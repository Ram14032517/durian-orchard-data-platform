"""Opt-in SQL integration against an isolated local cluster, never the user's existing DB."""
import os
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BIN=Path(r'C:/Program Files/PostgreSQL/17/bin')


@unittest.skipUnless(os.environ.get('RUN_PRIVATE_HARVEST_PG_TESTS')=='1' and (BIN/'initdb.exe').is_file(),
                     'Opt-in isolated PostgreSQL integration; no downloads')
class HarvestPostgresTests(unittest.TestCase):
    def test_private_schema_generated_yield_revisions_and_restart(self):
        parent=(ROOT/'.build/orchard-harvest-pg-tests').resolve();parent.mkdir(exist_ok=True)
        folder=Path(tempfile.mkdtemp(prefix='synthetic-',dir=parent)).resolve()
        self.assertTrue(folder.is_relative_to(parent))
        cluster=folder/'cluster';env={k:v for k,v in os.environ.items() if not k.startswith('PG')}
        env['PGCLIENTENCODING']='UTF8'
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        def call(name,args=(),sql=None,ok=True):
            r=subprocess.run([str(BIN/name),*args],input=sql,text=True,encoding='utf-8',errors='replace',
                capture_output=True,env=env,creationflags=flags,timeout=50)
            if ok:self.assertEqual(r.returncode,0,r.stderr[-1000:])
            else:self.assertNotEqual(r.returncode,0,'Expected database rejection')
            return r.stdout.strip()
        call('initdb.exe',['-D',str(cluster),'-U','postgres','-A','trust','--no-locale','-E','UTF8'])
        with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        log=(folder/'postgres.log').open('ab');process=None
        def start():
            nonlocal process
            process=subprocess.Popen([str(BIN/'postgres.exe'),'-D',str(cluster),'-h','127.0.0.1','-p',str(port)],
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env,creationflags=flags)
            deadline=time.monotonic()+25
            while time.monotonic()<deadline:
                with socket.socket() as probe:
                    if probe.connect_ex(('127.0.0.1',port))==0:return
                if process.poll() is not None:self.fail('Isolated PostgreSQL did not start')
                time.sleep(.1)
            self.fail('Isolated PostgreSQL startup timeout')
        def stop():
            if process and process.poll() is None:
                call('pg_ctl.exe',['-D',str(cluster),'-w','-m','fast','stop']);process.wait(timeout=10)
        def sql(text,ok=True):
            return call('psql.exe',['-X','-h','127.0.0.1','-p',str(port),'-U','postgres','-d','postgres','-qAt','-v','ON_ERROR_STOP=1'],text,ok)
        try:
            start()
            sql('create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;')
            sql('alter default privileges in schema public grant all on tables to service_role,anon,authenticated;')
            sql((ROOT/'api/supabase/migrations/004_private_orchard_harvest.sql').read_text(encoding='utf-8'))
            self.assertEqual(sql("select has_table_privilege('service_role','orchard_harvest_revisions','insert') or has_table_privilege('service_role','orchard_harvest_revisions','update') or has_table_privilege('service_role','orchard_harvest_revisions','delete');"),'f')
            owner='a'*64
            insert=f"""set role service_role; insert into public.orchard_harvest_seasons
            (id,owner_id,orchard_code,season_key,harvest_year,cultivar,bearing_area_rai,harvested_kg,
            harvest_start,harvest_end,source_type,source_reference,status,actual_harvest_confirmed)
            values('00000000-0000-4000-8000-000000000001','{owner}','SYNTHETIC-ONLY','main',2025,'TEST',10,15000,
            '2025-04-01','2025-05-01','farm_log','SYNTHETIC TEST ONLY','complete',true) returning yield_kg_per_rai=1500,version;"""
            self.assertEqual(sql(insert),'t|1')
            self.assertEqual(sql("set role service_role; update orchard_harvest_seasons set harvested_kg=18000 where version=1 returning yield_kg_per_rai=1800,version;"),'t|2')
            self.assertEqual(sql("select row_data->>'harvested_kg',version from orchard_harvest_revisions;"),'15000|1')
            sql(insert,ok=False)
            sql(f"set role service_role; update orchard_harvest_seasons set owner_id='{'b'*64}';",ok=False)
            sql('set role service_role; delete from orchard_harvest_seasons;',ok=False)
            for role in ['anon','authenticated']:
                for table in ['orchard_harvest_seasons','orchard_harvest_revisions']:
                    sql(f'set role {role}; select * from {table};',ok=False)
            sql(f"set role service_role; insert into orchard_harvest_seasons(owner_id,orchard_code,season_key,harvest_year,source_type) values('{owner}','SYNTHETIC-DRAFT','main',2025,'self_report');")
            self.assertEqual(sql("select yield_kg_per_rai is null from orchard_harvest_seasons where status='draft';"),'t')
            stop();start()
            self.assertEqual(sql("select count(*) from orchard_harvest_seasons;"),'2')
            self.assertEqual(sql("select count(*) from orchard_harvest_revisions;"),'1')
        finally:
            stop();log.close()
            # Retain synthetic-only cluster for inspection; no recursive removal of computed paths.


if __name__=='__main__':unittest.main()
