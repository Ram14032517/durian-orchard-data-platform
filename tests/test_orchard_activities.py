import copy
from datetime import date
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from orchard_activities import ActivityStore,validate,public_record
from orchard_harvest import HarvestConflict,owner_key
from serve_orchard_cloud import create_app

TODAY=date(2026,11,2)
OWNER=owner_key('qa-owner')


def values(**extra):
    return dict(orchard_code='sensor-orchard-v1',activity_date='2026-11-01',kind='water',production_stage=None,
        stage_context={},status='done',title='ให้น้ำตามบันทึก',notes='',amount=None,unit=None,**extra)


class ActivityTests(unittest.TestCase):
    def test_validate_actual_planned_missing_zero_and_units(self):
        self.assertIsNone(validate(values(),TODAY)['amount'])
        data=values();data.update(amount=0,unit='litre')
        self.assertEqual(validate(data,TODAY)['amount'],0)
        data.update(activity_date='2026-11-03',status='planned')
        self.assertEqual(validate(data,TODAY)['status'],'planned')
        data['status']='done'
        with self.assertRaises(ValueError):validate(data,TODAY)

    def test_reject_owner_bad_dates_nonfinite_and_stage_mismatch(self):
        for changes in [dict(owner_id='someone'),dict(activity_date='2026-02-30'),dict(amount=-1,unit='kg'),
            dict(amount=float('nan'),unit='kg'),dict(amount=True,unit='kg'),dict(unit='kg'),
            dict(kind='stage'),dict(production_stage='recovery'),dict(stage_context={'secret':'value'}),
            dict(stage_context=[]),dict(activity_date='20261101')]:
            data=values();data.update(changes)
            with self.assertRaises(ValueError,msg=str(changes)):validate(data,TODAY)
        data=values();data.update(kind='stage',production_stage='young',stage_context={'province':'84','water':'unknown'})
        self.assertEqual(validate(data,TODAY)['production_stage'],'young')

    def test_month_query_is_owner_scoped_and_complete(self):
        store=ActivityStore();row=dict(validate(values(),TODAY),id=str(uuid.uuid4()),owner_id=OWNER,version=1)
        with patch('orchard_activities.read_table',return_value=[row]) as read:
            result=store.list(OWNER,'2026-11')
            self.assertNotIn('owner_id',result[0])
            params=read.call_args.args[1]
            self.assertEqual(params['owner_id'],'eq.'+OWNER)
            self.assertEqual(params['activity_date'],'gte.2026-11-01')
            self.assertEqual(params['and'],'(activity_date.lt.2026-12-01)')
        for month in ('2026-13','2026-1','bad','9999-12'):
            with self.assertRaises(ValueError):store.list(OWNER,month)
        with patch('orchard_activities.read_table',return_value=[{**row,'owner_id':'other'}]):
            with self.assertRaises(RuntimeError):store.list(OWNER,'2026-11')

    def test_create_retries_do_not_duplicate_or_expose_another_owner(self):
        store=ActivityStore();data=dict(values(),id=str(uuid.uuid4()))
        row=dict(validate(values(),TODAY),id=data['id'],owner_id=OWNER,version=1)
        with patch.object(store,'_write',return_value=[row]) as write:
            result=store.create(OWNER,data)
            self.assertEqual(write.call_args.args[2]['owner_id'],OWNER)
            self.assertNotIn('owner_id',result)
        with patch.object(store,'_write',side_effect=HarvestConflict()),patch('orchard_activities.read_table',return_value=[row]) as read:
            self.assertEqual(store.create(OWNER,data)['id'],data['id'])
            self.assertEqual(read.call_args.args[1]['owner_id'],'eq.'+OWNER)
        with patch.object(store,'_write',side_effect=HarvestConflict()),patch('orchard_activities.read_table',return_value=[]):
            with self.assertRaises(HarvestConflict):store.create(OWNER,data)

    def test_update_filters_owner_and_version_and_rejects_conflicts(self):
        store=ActivityStore();identity=str(uuid.uuid4());row=dict(validate(values(),TODAY),id=identity,owner_id=OWNER,version=1)
        with patch('orchard_activities.read_table',return_value=[row]),patch.object(store,'_write',return_value=[{**row,'version':2}]) as write:
            self.assertEqual(store.update(OWNER,identity,{'notes':'ตรวจระบบน้ำ','expected_version':1})['version'],2)
            self.assertEqual(write.call_args.args[1]['owner_id'],'eq.'+OWNER)
            self.assertEqual(write.call_args.args[1]['version'],'eq.1')
        with patch('orchard_activities.read_table',return_value=[row]):
            with self.assertRaises(HarvestConflict):store.update(OWNER,identity,{'expected_version':2})
        with patch('orchard_activities.read_table',return_value=[]):
            with self.assertRaises(LookupError):store.update(OWNER,identity,{'expected_version':1})

    def test_latest_stage_ignores_planned_future_and_other_orchards(self):
        store=ActivityStore()
        with patch('orchard_activities.read_table',return_value=[]) as read:
            self.assertIsNone(store.latest_stage(OWNER))
            params=read.call_args.args[1]
            self.assertEqual(params['status'],'eq.done')
            self.assertEqual(params['orchard_code'],'eq.sensor-orchard-v1')
            self.assertEqual(params['kind'],'eq.stage')
            self.assertTrue(params['activity_date'].startswith('lte.'))


class ActivityApiTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'DASHBOARD_USER':'qa-owner','DASHBOARD_PASSWORD':'qa-activity-test-password'},clear=True)
        self.env.start();self.app=create_app();self.client=self.app.test_client()
        with self.client.session_transaction() as state:
            state.update(authenticated=True,principal='qa-owner',csrf='qa-csrf')
        self.store=Mock();self.store.list.return_value=[];self.store.latest_stage.return_value=None
        self.app.config['ACTIVITY_STORE']=self.store

    def tearDown(self):self.env.stop()

    def test_requires_login_csrf_and_owner_comes_from_session(self):
        identity=str(uuid.uuid4());data=dict(values(),id=identity)
        self.assertEqual(self.app.test_client().get('/api/orchard-activities').status_code,401)
        self.assertEqual(self.client.post('/api/orchard-activities',json=data).status_code,403)
        self.assertEqual(self.client.post('/api/orchard-activities',json=data,headers={'X-CSRF-Token':'qa-csrf','Origin':'https://evil.invalid'}).status_code,403)
        self.store.create.return_value={'id':identity}
        response=self.client.post('/api/orchard-activities',json=data,headers={'X-CSRF-Token':'qa-csrf'})
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.store.create.call_args.args[0],OWNER)
        listing=self.client.get('/api/orchard-activities?month=2026-11')
        self.assertEqual(listing.json['account'],'qa-owner')
        self.store.list.assert_called_with(OWNER,'2026-11')
        self.assertEqual(self.client.get('/api/orchard-activities/stage').json['record'],None)
        self.store.latest_stage.assert_called_with(OWNER)

    def test_update_conflict_and_not_found_are_visible(self):
        url='/api/orchard-activities/'+str(uuid.uuid4());headers={'X-CSRF-Token':'qa-csrf'}
        self.store.update.side_effect=HarvestConflict('reload')
        self.assertEqual(self.client.patch(url,json={'expected_version':1},headers=headers).status_code,409)
        self.store.update.side_effect=LookupError()
        self.assertEqual(self.client.patch(url,json={'expected_version':1},headers=headers).status_code,404)


if __name__=='__main__':unittest.main()
