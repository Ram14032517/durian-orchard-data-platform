-- Private activity journal; same backend owner identity as seasonal harvests.
begin;
create table public.orchard_activities (
  id uuid primary key,
  owner_id text not null check(owner_id ~ '^[0-9a-f]{64}$'),
  orchard_code text not null check(length(trim(orchard_code)) between 1 and 64),
  activity_date date not null check(activity_date between date '1981-01-01' and date '2100-12-31'),
  kind text not null check(kind in ('water','fertilizer','observation','harvest','stage')),
  production_stage text check(production_stage in ('recovery','flower','bloom','young','growth','harvest')),
  stage_context jsonb not null default '{}'::jsonb check(jsonb_typeof(stage_context)='object' and octet_length(stage_context::text)<=1000),
  status text not null check(status in ('planned','done')),
  title text not null check(length(trim(title)) between 1 and 120),
  notes text not null default '' check(length(notes)<=2000),
  amount numeric check(amount>=0 and amount<=1000000000),
  unit text check(unit in ('litre','kg','minute','tree')),
  version integer not null default 1 check(version>0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check((amount is null and unit is null) or (amount is not null and unit is not null)),
  check((kind='stage' and production_stage is not null) or (kind<>'stage' and production_stage is null)),
  check(kind='stage' or stage_context='{}'::jsonb),
  check(status<>'done' or activity_date <= (now() at time zone 'Asia/Bangkok')::date)
);
create index orchard_activities_owner_date_idx on public.orchard_activities(owner_id,activity_date,id);
create table public.orchard_activity_revisions (
  record_id uuid not null references public.orchard_activities(id),
  owner_id text not null,
  version integer not null,
  row_data jsonb not null,
  archived_at timestamptz not null default now(),
  primary key(record_id,version)
);
create function public.audit_orchard_activity() returns trigger language plpgsql security definer
set search_path = public, pg_temp as $$
begin
  if new.owner_id<>old.owner_id or new.id<>old.id then
    raise exception 'Cannot change activity owner or identity';
  end if;
  insert into public.orchard_activity_revisions(record_id,owner_id,version,row_data)
    values(old.id,old.owner_id,old.version,to_jsonb(old));
  new.version:=old.version+1;
  new.created_at:=old.created_at;
  new.updated_at:=now();
  return new;
end $$;
revoke all on function public.audit_orchard_activity() from public,anon,authenticated;
create trigger orchard_activity_revision before update on public.orchard_activities
  for each row execute function public.audit_orchard_activity();
alter table public.orchard_activities enable row level security;
alter table public.orchard_activity_revisions enable row level security;
revoke all on public.orchard_activities,public.orchard_activity_revisions from public,anon,authenticated,service_role;
grant select,insert,update on public.orchard_activities to service_role;
grant select on public.orchard_activity_revisions to service_role;
-- No direct browser grants, public policies, or DELETE. Backend always filters owner_id.
commit;
