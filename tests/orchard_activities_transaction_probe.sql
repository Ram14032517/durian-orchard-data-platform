-- Run as a one-off diagnostic in Supabase SQL Editor. Nothing is committed.
begin;
set local role service_role;
do $$
declare testid uuid:=gen_random_uuid();
begin
  insert into public.orchard_activities(id,owner_id,orchard_code,activity_date,kind,status,title)
    values(testid,repeat('0',64),'transaction-only-qa',(now() at time zone 'Asia/Bangkok')::date,'water','done','QA rollback only');
  update public.orchard_activities set notes='QA edited' where id=testid;
  if (select version from public.orchard_activities where id=testid)<>2 then raise exception 'version check failed';end if;
  if (select count(*) from public.orchard_activity_revisions where record_id=testid)<>1 then raise exception 'revision check failed';end if;
  begin
    insert into public.orchard_activities(id,owner_id,orchard_code,activity_date,kind,status,title)
      values(gen_random_uuid(),repeat('0',64),'transaction-only-qa',(now() at time zone 'Asia/Bangkok')::date+1,'water','done','Must reject future completed');
    raise exception 'future done incorrectly accepted';
  exception when check_violation then null;end;
end $$;
select 'insert_update_audit_future_date_checks_passed_rollback_follows' as result;
rollback;
