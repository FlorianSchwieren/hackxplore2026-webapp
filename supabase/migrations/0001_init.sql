create extension if not exists pgcrypto;
create extension if not exists postgis;

create table if not exists profiles (
    id uuid primary key,
    display_name text not null,
    email text,
    avatar_url text,
    score int not null default 0,
    notify_help_opt_in boolean not null default false,
    created_at timestamptz not null default now()
);

do $$
begin
    if exists (
        select 1
        from information_schema.tables
        where table_schema = 'auth' and table_name = 'users'
    ) and not exists (
        select 1
        from information_schema.table_constraints
        where constraint_schema = 'public'
          and table_name = 'profiles'
          and constraint_name = 'profiles_id_auth_users_fkey'
    ) then
        alter table profiles
            add constraint profiles_id_auth_users_fkey
            foreign key (id) references auth.users(id) on delete cascade;
    end if;
end $$;

create table if not exists species_water_profiles (
    id uuid primary key default gen_random_uuid(),
    match_kind text not null check (match_kind in ('category', 'species_lat')),
    match_value text not null unique,
    optimal_min_pct numeric not null,
    optimal_max_pct numeric not null,
    dry_critical_pct numeric not null,
    wet_critical_pct numeric not null,
    drought_tolerance text not null default 'medium',
    priority int not null default 0,
    notes text
);

create table if not exists trees (
    id uuid primary key default gen_random_uuid(),
    external_id bigint unique not null,
    lfdbnr int,
    artdeut text,
    artlat text,
    baumart_allgemein text not null,
    baumgruppe text,
    stadtteil text not null,
    geom geometry(Point, 4326) not null,
    name text,
    status text not null default 'available' check (status in ('available', 'adopted')),
    species_profile_id uuid references species_water_profiles(id),
    moisture_pct numeric(5,2),
    health_score int,
    health_state text check (
        health_state is null
        or health_state in ('thriving', 'healthy', 'thirsty', 'critical', 'overwatered')
    ),
    last_reading_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists idx_trees_geom on trees using gist (geom);
create index if not exists idx_trees_stadtteil on trees (stadtteil);
create index if not exists idx_trees_status on trees (status);
create index if not exists idx_trees_health_state on trees (health_state);

create table if not exists sensors (
    id uuid primary key default gen_random_uuid(),
    device_eui text unique not null,
    device_ref text unique not null,
    tree_id uuid unique not null references trees(id) on delete cascade,
    status text not null default 'working' check (status in ('working', 'inactive', 'defect')),
    is_real boolean not null default false,
    calibration_dry int not null,
    calibration_wet int not null,
    installed_at timestamptz not null default now(),
    last_seen_at timestamptz,
    created_at timestamptz not null default now()
);

create index if not exists idx_sensors_status on sensors (status);

create table if not exists sensor_readings (
    id bigserial primary key,
    sensor_id uuid not null references sensors(id) on delete cascade,
    tree_id uuid not null references trees(id) on delete cascade,
    raw int not null,
    moisture_pct numeric(5,2) not null,
    is_outlier boolean not null default false,
    measured_at timestamptz not null,
    received_at timestamptz not null default now(),
    fcnt int,
    rssi int,
    snr numeric,
    battery_mv int,
    device_status text,
    device_moisture_pct numeric,
    priority numeric,
    source text not null default 'lorawan' check (source in ('lorawan', 'mock', 'manual'))
);

create index if not exists idx_sensor_readings_sensor_time on sensor_readings (sensor_id, measured_at desc);
create index if not exists idx_sensor_readings_tree_time on sensor_readings (tree_id, measured_at desc);
create unique index if not exists uq_sensor_readings_sensor_fcnt
    on sensor_readings (sensor_id, fcnt)
    where fcnt is not null;
create unique index if not exists uq_sensor_readings_sensor_measured_at
    on sensor_readings (sensor_id, measured_at)
    where fcnt is null;

create table if not exists tree_partnerships (
    id uuid primary key default gen_random_uuid(),
    tree_id uuid not null references trees(id) on delete cascade,
    user_id uuid not null references profiles(id) on delete cascade,
    role text not null check (role in ('owner', 'member', 'caretaker')),
    active_from date not null default current_date,
    active_to date,
    streak int not null default 0,
    streak_frozen boolean not null default false,
    last_eval_date date,
    created_at timestamptz not null default now()
);

create unique index if not exists uq_tree_partnerships_active_user
    on tree_partnerships (tree_id, user_id)
    where active_to is null;
create unique index if not exists uq_tree_partnerships_active_owner
    on tree_partnerships (tree_id)
    where role = 'owner' and active_to is null;
create index if not exists idx_tree_partnerships_user on tree_partnerships (user_id);
create index if not exists idx_tree_partnerships_tree on tree_partnerships (tree_id);

create table if not exists absences (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references profiles(id) on delete cascade,
    tree_id uuid not null references trees(id) on delete cascade,
    partnership_id uuid not null references tree_partnerships(id) on delete cascade,
    from_date date not null,
    to_date date not null,
    status text not null default 'open' check (status in ('open', 'covered', 'expired')),
    covering_partnership_id uuid references tree_partnerships(id),
    created_at timestamptz not null default now(),
    check (to_date >= from_date)
);

create index if not exists idx_absences_status on absences (status);
create index if not exists idx_absences_user on absences (user_id);
create index if not exists idx_absences_tree on absences (tree_id);

create table if not exists weather_snapshots (
    id bigserial primary key,
    captured_at timestamptz not null default now(),
    lat numeric not null,
    lon numeric not null,
    temp_c numeric,
    precip_mm numeric,
    humidity_pct numeric,
    forecast_json jsonb
);

create index if not exists idx_weather_snapshots_captured_at on weather_snapshots (captured_at desc);

create table if not exists notifications (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references profiles(id) on delete cascade,
    kind text not null check (
        kind in ('thirsty', 'recovered', 'coverage_needed', 'streak_milestone')
    ),
    title text not null,
    body text not null,
    tree_id uuid references trees(id) on delete set null,
    payload jsonb,
    read boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists idx_notifications_user_created on notifications (user_id, created_at desc);

create or replace function prevent_append_only_history_changes()
returns trigger
language plpgsql
as $$
begin
    raise exception '% is append-only', tg_table_name;
end;
$$;

drop trigger if exists sensor_readings_append_only on sensor_readings;
create trigger sensor_readings_append_only
    before update or delete on sensor_readings
    for each row execute function prevent_append_only_history_changes();

drop trigger if exists weather_snapshots_append_only on weather_snapshots;
create trigger weather_snapshots_append_only
    before update or delete on weather_snapshots
    for each row execute function prevent_append_only_history_changes();

do $$
begin
    if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
        if not exists (
            select 1 from pg_publication_tables
            where pubname = 'supabase_realtime' and tablename = 'trees'
        ) then
            alter publication supabase_realtime add table trees;
        end if;
        if not exists (
            select 1 from pg_publication_tables
            where pubname = 'supabase_realtime' and tablename = 'tree_partnerships'
        ) then
            alter publication supabase_realtime add table tree_partnerships;
        end if;
        if not exists (
            select 1 from pg_publication_tables
            where pubname = 'supabase_realtime' and tablename = 'sensor_readings'
        ) then
            alter publication supabase_realtime add table sensor_readings;
        end if;
    end if;
end $$;
