"""Private date-based journal using the existing Supabase transport and owner identity."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import math
import uuid

from orchard_harvest import HarvestStore, HarvestConflict
from supabase_orchard import read_table

TABLE='orchard_activities'
FIELDS='id,owner_id,orchard_code,activity_date,kind,production_stage,stage_context,status,title,notes,amount,unit,version,created_at,updated_at'
INPUTS={'orchard_code','activity_date','kind','production_stage','stage_context','status','title','notes','amount','unit'}
STAGES=('recovery','flower','bloom','young','growth','harvest')


def validate(payload, today=None):
    today=today or datetime.now(ZoneInfo('Asia/Bangkok')).date()
    if not isinstance(payload,dict) or set(payload)-INPUTS:raise ValueError('มีช่องข้อมูลที่ไม่อนุญาต')
    result={}
    for key,limit in [('orchard_code',64),('title',120),('notes',2000)]:
        value=payload.get(key,'')
        if not isinstance(value,str) or len(value.strip())>limit or any(ord(c)<32 and c not in '\n\r\t' for c in value):raise ValueError('ข้อความไม่ถูกต้องหรือยาวเกินกำหนด')
        result[key]=value.strip()
    if not result['orchard_code'] or not result['title']:raise ValueError('ระบุสวนและหัวข้อกิจกรรม')
    try:stamp=date.fromisoformat(payload.get('activity_date',''))
    except (ValueError,TypeError):raise ValueError('วันที่ต้องเป็น YYYY-MM-DD') from None
    if stamp.isoformat()!=payload.get('activity_date') or not date(1981,1,1)<=stamp<=date(2100,12,31):raise ValueError('วันที่อยู่นอกช่วงที่รองรับหรือรูปแบบไม่ถูกต้อง')
    result.update(activity_date=stamp.isoformat(),kind=payload.get('kind'),status=payload.get('status'))
    if result['kind'] not in ('water','fertilizer','observation','harvest','stage') or result['status'] not in ('planned','done'):raise ValueError('ประเภทหรือสถานะกิจกรรมไม่ถูกต้อง')
    result['production_stage']=payload.get('production_stage') or None
    if (result['kind']=='stage' and result['production_stage'] not in STAGES) or (result['kind']!='stage' and result['production_stage'] is not None):raise ValueError('เลือกระยะการผลิตให้ตรงกับประเภทบันทึก')
    context=payload.get('stage_context',{})
    if not isinstance(context,dict) or set(context)-{'province','water','situation'}:raise ValueError('บริบทระยะไม่ถูกต้อง')
    choices={'province':{'','22','33','53','84','86'},'water':{'unknown','yes','no'},'situation':{'unknown','normal','dry','wet','drop','flush','storm'}}
    if any(not isinstance(v,str) or v not in choices[k] for k,v in context.items()) or (result['kind']!='stage' and context):raise ValueError('บริบทระยะไม่ตรงกับข้อมูลที่รองรับ')
    result['stage_context']=context
    if result['status']=='done' and stamp>today:raise ValueError('กิจกรรมที่ทำแล้วต้องไม่เป็นวันที่ในอนาคต')
    raw=payload.get('amount')
    if raw is None or raw=='':
        if payload.get('unit') not in (None,''):raise ValueError('ถ้าระบุหน่วย ต้องระบุปริมาณด้วย')
        result.update(amount=None,unit=None)
    else:
        try:value=float(raw)
        except (TypeError,ValueError):raise ValueError('ปริมาณต้องเป็นตัวเลข') from None
        if isinstance(raw,bool) or not math.isfinite(value) or not 0<=value<=1e9 or payload.get('unit') not in ('litre','kg','minute','tree'):raise ValueError('ตรวจปริมาณและหน่วย')
        result.update(amount=value,unit=payload['unit'])
    return result


def public_record(row):return {k:v for k,v in row.items() if k!='owner_id'}


class ActivityStore(HarvestStore):
    table=TABLE

    def latest_stage(self,owner):
        today=datetime.now(ZoneInfo('Asia/Bangkok')).date().isoformat()
        rows=read_table(TABLE,dict(select=FIELDS,owner_id='eq.'+owner,orchard_code='eq.sensor-orchard-v1',kind='eq.stage',
            status='eq.done',activity_date='lte.'+today,order='activity_date.desc,updated_at.desc,id.desc',limit='1'))
        if rows and rows[0].get('owner_id')!=owner:raise RuntimeError('เจ้าของระยะสวนไม่ตรง')
        return public_record(rows[0]) if rows else None

    def list(self,owner,month):
        try:
            first=date.fromisoformat(month+'-01')
            if first.strftime('%Y-%m')!=month or not 1981<=first.year<=2100:raise ValueError()
        except (TypeError,ValueError):raise ValueError('เดือนต้องเป็น YYYY-MM') from None
        end=(first.replace(day=28)+timedelta(days=4)).replace(day=1)
        rows=read_table(TABLE,dict(select=FIELDS,owner_id='eq.'+owner,activity_date='gte.'+first.isoformat(),
            **{'and':'(activity_date.lt.'+end.isoformat()+')'},order='activity_date.asc,id.asc',limit='1000'))
        if len(rows)>=1000:raise RuntimeError('มีกิจกรรมมากเกินขอบเขตเดือน กรุณาติดต่อผู้ดูแลเพื่อแบ่งหน้า')
        if any(r.get('owner_id')!=owner for r in rows):raise RuntimeError('เจ้าของข้อมูลไม่ตรง')
        return [public_record(r) for r in rows]

    def create(self,owner,payload):
        if not isinstance(payload,dict):raise ValueError('ต้องส่ง JSON object')
        try:identity=str(uuid.UUID(payload.get('id','')))
        except (ValueError,TypeError,AttributeError):raise ValueError('รหัสคำขอบันทึกไม่ถูกต้อง') from None
        values=validate({k:v for k,v in payload.items() if k!='id'})
        try:rows=self._write('POST',{'select':FIELDS},dict(values,id=identity,owner_id=owner))
        except HarvestConflict:
            # Retry of the same form is idempotent; another owner's UUID never returns their row.
            rows=read_table(TABLE,dict(select=FIELDS,owner_id='eq.'+owner,id='eq.'+identity,limit='1'))
            if len(rows)!=1 or any(rows[0].get(k)!=v for k,v in values.items()):raise HarvestConflict('คำขอนี้ถูกบันทึกแล้ว ให้โหลดปฏิทินก่อนแก้ไข') from None
        if len(rows)!=1 or rows[0].get('owner_id')!=owner:raise RuntimeError('ยืนยันเจ้าของกิจกรรมไม่ได้')
        return public_record(rows[0])

    def update(self,owner,record_id,payload):
        if not isinstance(payload,dict) or set(payload)-INPUTS-{'expected_version'}:raise ValueError('ช่องข้อมูลแก้ไขไม่ถูกต้อง')
        expected=payload.get('expected_version')
        if type(expected) is not int or expected<1:raise ValueError('ต้องระบุรุ่นรายการก่อนแก้ไข')
        filters=dict(select=FIELDS,owner_id='eq.'+owner,id='eq.'+str(uuid.UUID(record_id)),limit='1')
        rows=read_table(TABLE,filters)
        if not rows:raise LookupError('ไม่พบกิจกรรมของบัญชีนี้')
        old=rows[0]
        if old.get('owner_id')!=owner:raise RuntimeError('เจ้าของกิจกรรมไม่ตรง')
        if old['version']!=expected:raise HarvestConflict('รายการถูกแก้ไขแล้ว โหลดใหม่ก่อนบันทึก')
        values=validate({**{k:old.get(k) for k in INPUTS},**{k:v for k,v in payload.items() if k!='expected_version'}})
        filters.pop('limit');filters['version']='eq.'+str(expected)
        rows=self._write('PATCH',filters,values)
        if not rows:raise HarvestConflict('รายการเปลี่ยนระหว่างบันทึก กรุณาโหลดใหม่')
        if len(rows)!=1 or rows[0].get('owner_id')!=owner:raise RuntimeError('ยืนยันเจ้าของกิจกรรมไม่ได้')
        return public_record(rows[0])
