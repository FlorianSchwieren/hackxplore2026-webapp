alter table profiles enable row level security;
alter table species_water_profiles enable row level security;
alter table trees enable row level security;
alter table sensors enable row level security;
alter table sensor_readings enable row level security;
alter table tree_partnerships enable row level security;
alter table absences enable row level security;
alter table weather_snapshots enable row level security;
alter table notifications enable row level security;

do $$
begin
    if not exists (select 1 from pg_policies where policyname = 'profiles_select_own') then
        create policy profiles_select_own on profiles
            for select to authenticated
            using (id = auth.uid());
    end if;
    if not exists (select 1 from pg_policies where policyname = 'profiles_update_own') then
        create policy profiles_update_own on profiles
            for update to authenticated
            using (id = auth.uid())
            with check (id = auth.uid());
    end if;
    if not exists (select 1 from pg_policies where policyname = 'species_public_read') then
        create policy species_public_read on species_water_profiles
            for select to authenticated
            using (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'trees_public_read') then
        create policy trees_public_read on trees
            for select to authenticated
            using (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'sensors_public_read') then
        create policy sensors_public_read on sensors
            for select to authenticated
            using (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'sensor_readings_public_read') then
        create policy sensor_readings_public_read on sensor_readings
            for select to authenticated
            using (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'tree_partnerships_read_relevant') then
        create policy tree_partnerships_read_relevant on tree_partnerships
            for select to authenticated
            using (user_id = auth.uid() or tree_id in (select id from trees));
    end if;
    if not exists (select 1 from pg_policies where policyname = 'absences_read_own_or_open') then
        create policy absences_read_own_or_open on absences
            for select to authenticated
            using (user_id = auth.uid() or status = 'open');
    end if;
    if not exists (select 1 from pg_policies where policyname = 'weather_public_read') then
        create policy weather_public_read on weather_snapshots
            for select to authenticated
            using (true);
    end if;
    if not exists (select 1 from pg_policies where policyname = 'notifications_select_own') then
        create policy notifications_select_own on notifications
            for select to authenticated
            using (user_id = auth.uid());
    end if;
    if not exists (select 1 from pg_policies where policyname = 'notifications_update_own') then
        create policy notifications_update_own on notifications
            for update to authenticated
            using (user_id = auth.uid())
            with check (user_id = auth.uid());
    end if;
end $$;
