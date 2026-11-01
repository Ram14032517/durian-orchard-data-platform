-- Apply to the existing Supabase project; no anonymous/browser access.
begin;
create table public.orchard_harvest_seasons (
  id uuid primary key default gen_random_uuid(),
  owner_id text not null check (owner_id ~ '^[0-9a-f]{64}$'),
  orchard_code text not null check (length(orchard_code) between 1 and 64),
  season_key text not null check (length(season_key) between 1 and 64),
  harvest_year integer not null check (harvest_year between 1981 and 2200),
  cultivar text not null default '' check (length(cultivar) <= 120),
  province_code text check (province_code ~ '^[1-9][0-9]$'),
  bearing_area_rai numeric check (bearing_area_rai > 0 and bearing_area_rai <= 1000000000000),
  harvested_kg numeric check (harvested_kg >= 0 and harvested_kg <= 1000000000000),
  harvest_start date,
  harvest_end date,
  source_type text not null check (source_type in ('farm_log','weighbridge','sales_receipts','self_report')),
  source_reference text not null default '' check (length(source_reference) <= 1000),
  status text not null default 'draft' check (status in ('draft','complete')),
  actual_harvest_confirmed boolean not null default false,
  yield_kg_per_rai numeric generated always as
    (case when status='complete' then harvested_kg / bearing_area_rai else null end) stored,
  version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id,orchard_code,season_key,harvest_year),
  check (harvest_start is null or extract(year from harvest_start)=harvest_year),
  check (harvest_end is null or extract(year from harvest_end)=harvest_year),
  check (harvest_start is null or harvest_end is null or harvest_start <= harvest_end),
  check (status <> 'complete' or (actual_harvest_confirmed and bearing_area_rai is not null
    and harvested_kg is not null and harvest_start is not null and harvest_end is not null
    and length(trim(cultivar))>0 and length(trim(source_reference))>0))
);
create index orchard_harvest_owner_year_idx on public.orchard_harvest_seasons(owner_id,harvest_year desc);

create table public.orchard_harvest_revisions (
  record_id uuid not null references public.orchard_harvest_seasons(id),
  owner_id text not null,
  version integer not null,
  row_data jsonb not null,
  archived_at timestamptz not null default now(),
  primary key(record_id,version)
);
create function public.audit_orchard_harvest() returns trigger language plpgsql security definer
set search_path = public, pg_temp as $$
begin
  if new.owner_id <> old.owner_id or new.id <> old.id then
    raise exception 'Cannot change record owner or identity';
  end if;
  insert into public.orchard_harvest_revisions(record_id,owner_id,version,row_data)
    values(old.id,old.owner_id,old.version,to_jsonb(old));
  new.version := old.version+1;
  new.created_at := old.created_at;
  new.updated_at := now();
  return new;
end $$;
revoke all on function public.audit_orchard_harvest() from public,anon,authenticated;
create trigger orchard_harvest_revision before update on public.orchard_harvest_seasons
  for each row execute function public.audit_orchard_harvest();
alter table public.orchard_harvest_seasons enable row level security;
alter table public.orchard_harvest_revisions enable row level security;
revoke all on public.orchard_harvest_seasons,public.orchard_harvest_revisions from public,anon,authenticated;
revoke all on public.orchard_harvest_seasons,public.orchard_harvest_revisions from service_role;
grant select,insert,update on public.orchard_harvest_seasons to service_role;
grant select on public.orchard_harvest_revisions to service_role;
-- No DELETE grant and no public RLS policy. The authenticated backend must filter owner_id.
commit;
