-- HackXplore 2026 — Supabase Schema
-- Run in order: sensors → trees (FK dependency)

create extension if not exists "uuid-ossp";

-- ── Sensors ────────────────────────────────────────────────────────────────
create table sensors (
  id               uuid primary key default uuid_generate_v4(),
  name             text not null,
  model_type       text not null,
  status           text not null check (status in ('active', 'inactive')),
  installed_at     timestamptz not null,
  last_activity    timestamptz not null,
  lat              double precision not null,
  lng              double precision not null,
  covered_tree_ids uuid[] not null default '{}',
  battery_level    int check (battery_level between 0 and 100),
  created_at       timestamptz not null default now()
);

-- ── Trees ──────────────────────────────────────────────────────────────────
create table trees (
  id               uuid primary key default uuid_generate_v4(),
  name             text not null,
  tree_type        text not null,
  common_name      text not null,
  age_years        int not null check (age_years > 0),
  owner_username   text,
  current_humidity numeric(5, 2) not null default 0 check (current_humidity between 0 and 100),
  humidity_status  text not null check (humidity_status in ('dry', 'low', 'normal', 'moist')),
  sensor_id        uuid references sensors (id) on delete set null,
  lat              double precision not null,
  lng              double precision not null,
  district         text not null,
  created_at       timestamptz not null default now()
);

-- ── Sensor Readings ────────────────────────────────────────────────────────
create table sensor_readings (
  id        uuid primary key default uuid_generate_v4(),
  sensor_id uuid not null references sensors (id) on delete cascade,
  tree_id   uuid not null references trees (id) on delete cascade,
  value     numeric(5, 2) not null check (value between 0 and 100),
  timestamp timestamptz not null default now()
);

create index on sensor_readings (sensor_id, timestamp desc);
create index on sensor_readings (tree_id, timestamp desc);

-- ── User Profiles ──────────────────────────────────────────────────────────
create table user_profiles (
  id                   uuid primary key,
  username             text unique not null,
  assigned_trees_count int not null default 0,
  avatar_url           text,
  joined_at            timestamptz not null default now()
);

-- ── Row Level Security (public read for dashboard) ─────────────────────────
alter table trees enable row level security;
alter table sensors enable row level security;
alter table sensor_readings enable row level security;
alter table user_profiles enable row level security;

create policy "Public read trees"    on trees           for select using (true);
create policy "Public read sensors"  on sensors         for select using (true);
create policy "Public read readings" on sensor_readings for select using (true);
create policy "Public read profiles" on user_profiles   for select using (true);
