"""Read-only Supabase orchard summaries. Credentials never leave the server."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ml'))
from orchard_live_model import prepare_readings, prepare_forecasts, forecast_at, estimate, vpd, HOURS
from clean_stale_weather import WEATHER

SOIL_FIELDS=['soil_moisture_percent','soil_temperature_c','soil_ec','soil_ph','soil_n','soil_p','soil_k']
TELEMETRY_FIELDS=SOIL_FIELDS+WEATHER
# Rain totals in the source are rolling windows, so report the last reading, never their sum.
LAST_FIELDS=['rain_1h_mm','rain_24h_mm']
MAX_FIELDS=['wind_gust']


def read_table(table,params):
    url=os.environ.get('SUPABASE_URL','').rstrip('/')
    key=os.environ.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',url) or not key:
        raise RuntimeError('ยังไม่ได้ตั้งค่า Supabase ฝั่งเซิร์ฟเวอร์')
    headers={'apikey':key,'Accept':'application/json'}
    if not key.startswith('sb_secret_'):headers['Authorization']='Bearer '+key
    response=requests.get(url+'/rest/v1/'+table,params=params,headers=headers,timeout=15,allow_redirects=False)
    legacy=False
    optional={'soil_valid','soil_age_sec','weather_valid','weather_age_sec','weather_source'}
    selected=params.get('select','').split(',')
    if table=='sensor_readings' and response.status_code==400 and optional.intersection(selected):
        try:code=response.json().get('code')
        except (ValueError,AttributeError):code=None
        if code in ('42703','PGRST204'):
            # Old databases retain the original payload. Recover explicit quality facts only.
            fallback=dict(params,select=','.join(dict.fromkeys([c for c in selected if c not in optional]+['source_payload'])))
            response=requests.get(url+'/rest/v1/'+table,params=fallback,headers=headers,timeout=15,allow_redirects=False)
            legacy=True
    if response.status_code!=200:
        raise RuntimeError('อ่าน Supabase ไม่สำเร็จ ตรวจคีย์ สิทธิ์ และตาราง โดยไม่เปิด RLS เป็นสาธารณะ')
    rows=response.json()
    if not isinstance(rows,list):raise RuntimeError('รูปแบบข้อมูล Supabase ไม่ถูกต้อง')
    if legacy:
        for row in rows:
            payload=row.get('source_payload') or {}
            if not isinstance(payload,dict):payload={}
            known=True
            for prefix in ['soil','weather']:
                data=payload.get(prefix) or {}
                if not isinstance(data,dict):data={}
                valid=data.get('valid');age=data.get('age_sec')
                valid=valid if isinstance(valid,bool) else None
                age=float(age) if isinstance(age,(int,float)) and not isinstance(age,bool) and np.isfinite(age) and age>=0 else None
                row[prefix+'_valid']=valid;row[prefix+'_age_sec']=age
                known=known and valid is not None and age is not None
            row['weather_source']=payload.get('weather',{}).get('source') if isinstance(payload.get('weather'),dict) else None
            row['_quality_metadata_available']=known
            if 'source_payload' not in selected:row.pop('source_payload',None)
    return rows


def orchard_history(period='day', now=None, reader=read_table, end=None, start_date=None):
    """Hourly means first, then daily means; never sum rolling rain readings."""
    if period not in ('day', 'week', 'month', 'custom'):
        raise ValueError('ช่วงข้อมูลไม่ถูกต้อง')
    now=pd.Timestamp(now or datetime.now(timezone.utc))
    if end:
        from datetime import date
        selected=date.fromisoformat(end)
        if selected>now.tz_convert('Asia/Bangkok').date():raise ValueError('ไม่เลือกวันอนาคต')
        now=min(now,pd.Timestamp(selected,tz='Asia/Bangkok')+pd.Timedelta(days=1)-pd.Timedelta(microseconds=1))
    device=os.environ.get('ORCHARD_DEVICE_ID','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',device):
        raise RuntimeError('ต้องตั้ง ORCHARD_DEVICE_ID เพื่อเลือกสวน')
    if period=='custom':
        if not start_date or not end:raise ValueError('ระบุวันเริ่มและวันสิ้นสุด')
        from datetime import date
        first=date.fromisoformat(start_date)
        last=date.fromisoformat(end)
        if first>last or (last-first).days>=90:raise ValueError('ช่วงวันที่ต้องเรียงกันและไม่เกิน 90 วัน')
        start=pd.Timestamp(first,tz='Asia/Bangkok')
        if start>now:raise ValueError('ไม่เลือกวันอนาคต')
    else:
        days={'day':1,'week':7,'month':30}[period]
        start=now-pd.Timedelta(days=days)
    values=TELEMETRY_FIELDS
    fields=['event_id','recorded_at',*values,'soil_valid','weather_valid','soil_age_sec','weather_age_sec']
    rows=[]
    truncated=False
    for offset in range(0,30000,1000):
        page=reader('sensor_readings',dict(select=','.join(fields),device_id='eq.'+device,
            recorded_at='gte.'+start.isoformat(),order='recorded_at.desc,event_id.desc',limit='1000',offset=str(offset),
            **{'and':'(recorded_at.lte.'+now.isoformat()+')'}))
        rows.extend(page)
        if len(page)<1000:break
    else:truncated=True
    if not rows:
        return dict(period=period,source='Supabase',rows=[],raw_count=0,truncated=False,
                    start=start.isoformat(),end=now.isoformat(),message='ไม่มีข้อมูลสวนในช่วงที่เลือก')
    frame=pd.DataFrame(rows).drop_duplicates('event_id')
    frame['time']=pd.to_datetime(frame.recorded_at,utc=True,format='mixed',errors='coerce')
    frame=frame.loc[frame.time.between(start,now)].copy()
    for col in values:
        if col not in frame:frame[col]=np.nan
        frame[col]=pd.to_numeric(frame[col],errors='coerce').replace([np.inf,-np.inf],np.nan)
    for prefix,cols in [('soil',SOIL_FIELDS),('weather',WEATHER)]:
        for suffix in ('_valid','_age_sec'):
            if prefix+suffix not in frame:frame[prefix+suffix]=None
        bad=frame[prefix+'_valid'].eq(False) | pd.to_numeric(frame[prefix+'_age_sec'],errors='coerce').gt(3600)
        frame.loc[bad,cols]=np.nan
    frame.loc[~frame.soil_moisture_percent.between(0,100),'soil_moisture_percent']=np.nan
    frame.loc[~frame.outdoor_humidity_percent.between(0,100),'outdoor_humidity_percent']=np.nan
    frame['vpd_kpa']=vpd(frame.outdoor_temperature_c,frame.outdoor_humidity_percent)
    values=values+['vpd_kpa']
    frame=frame.set_index('time').sort_index().tz_convert('Asia/Bangkok')
    hourly=frame[values].resample('h').mean()
    frequency='h' if period=='day' or (period=='custom' and now-start<=pd.Timedelta(days=2)) else 'D'
    means=hourly if frequency=='h' else hourly.resample('D').mean()
    # Values in a rolling rain window are snapshots; wind gust is a peak, not an average.
    for col in LAST_FIELDS:means[col]=frame[col].resample(frequency).last()
    for col in MAX_FIELDS:means[col]=frame[col].resample(frequency).max()
    counts=frame[values].resample(frequency).count()
    full=pd.date_range(start.tz_convert('Asia/Bangkok').floor(frequency),now.tz_convert('Asia/Bangkok').floor(frequency),freq=frequency)
    means=means.reindex(full)
    records=[]
    for stamp,row in means.iterrows():
        records.append(dict(time=stamp.isoformat(),**{col:float(row[col]) if pd.notna(row[col]) else None for col in values},
            valid_counts={col:int(counts.loc[stamp,col]) if stamp in counts.index else 0 for col in values}))
    quality_unknown=any(r.get('_quality_metadata_available') is False for r in rows)
    return dict(period=period,source='Supabase',rows=records,raw_count=len(frame),truncated=truncated,
        start=start.isoformat(),end=now.isoformat(),aggregation='ค่าเฉลี่ยรายชั่วโมง' if frequency=='h' else 'ค่าเฉลี่ยรายวันจากค่าเฉลี่ยรายชั่วโมง',
        message='ข้อมูลจุดเซนเซอร์ ไม่ใช่ค่าเฉลี่ยทั้งสวน; ฝน 1/24 ชั่วโมงเป็นค่าล่าสุดของช่วง ไม่ใช่ผลรวม; ลมกระโชกใช้ค่าสูงสุด; ช่องว่างไม่ใช่ศูนย์'+
            ('; ข้อมูลเดิมบางรายการไม่มีธงคุณภาพยืนยัน จึงไม่ถือว่าผ่านการตรวจอัตโนมัติ' if quality_unknown else ''))


def live_status(now=None,reader=read_table):
    now=pd.Timestamp(now or datetime.now(timezone.utc))
    device=os.environ.get('ORCHARD_DEVICE_ID','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',device):
        raise RuntimeError('ต้องตั้ง ORCHARD_DEVICE_ID เพื่อไม่ปะปนข้อมูลหลายสวน')
    fields=['event_id','recorded_at','device_id',*TELEMETRY_FIELDS,
            'soil_valid','weather_valid','soil_age_sec','weather_age_sec']
    rows=reader('sensor_readings',dict(select=','.join(dict.fromkeys(fields)),device_id='eq.'+device,
                order='recorded_at.desc',limit='200'))
    if not rows:return dict(status='missing',message='ไม่มีข้อมูลเซนเซอร์ของสวนที่ตั้งไว้')
    frame=pd.DataFrame(rows)
    times=pd.to_datetime(frame.recorded_at,utc=True,format='mixed',errors='raise')
    if (times>now+pd.Timedelta(minutes=5)).any():raise RuntimeError('เวลาเซนเซอร์อยู่ในอนาคต ตรวจนาฬิกาอุปกรณ์')
    for field in TELEMETRY_FIELDS:
        if field not in frame:frame[field]=np.nan
        frame[field]=pd.to_numeric(frame[field],errors='coerce').replace([np.inf,-np.inf],np.nan)
    bad_soil=frame.get('soil_valid',pd.Series(index=frame.index,dtype=object)).eq(False)
    bad_weather=frame.get('weather_valid',pd.Series(index=frame.index,dtype=object)).eq(False)
    bad_soil|=pd.to_numeric(frame.get('soil_age_sec'),errors='coerce').gt(3600) if 'soil_age_sec' in frame else False
    bad_weather|=pd.to_numeric(frame.get('weather_age_sec'),errors='coerce').gt(3600) if 'weather_age_sec' in frame else False
    frame.loc[bad_soil,SOIL_FIELDS]=np.nan
    frame.loc[bad_weather,WEATHER]=np.nan
    readings,hourly=prepare_readings(frame)
    latest=readings.iloc[-1]
    age=(now-latest.time).total_seconds()/60
    finite=lambda v:float(v) if pd.notna(v) and np.isfinite(v) else None
    def quality(prefix):
        valid=latest.get(prefix+'_valid');age=latest.get(prefix+'_age_sec')
        if valid is False or isinstance(valid,np.bool_) and not valid:return 'invalid'
        if prefix=='weather' and latest.get('weather_stale_online',False):return 'stale'
        if pd.notna(age) and float(age)>3600:return 'stale'
        return 'valid' if (valid is True or isinstance(valid,np.bool_) and valid) and pd.notna(age) else 'unverified'
    result=dict(status='fresh_live' if 0<=age<=60 else 'stale_live',mode='supabase_live',
                sensor_time=latest.time.isoformat(),age_minutes=float(age),soil_percent=finite(latest.soil_moisture_percent),
                vpd_kpa=finite(latest.vpd_kpa),prediction=None,
                readings={**{field:finite(latest[field]) for field in TELEMETRY_FIELDS},'vpd_kpa':finite(latest.vpd_kpa)},
                sensor_quality={prefix:quality(prefix) for prefix in ('soil','weather')})
    if result['sensor_quality']['soil'] in ('invalid','stale'):
        # Old readings remain historical; never treat an invalid or undated reading as current.
        def usable_soil(page):
            for row in page:
                valid=row.get('soil_valid');age=row.get('soil_age_sec')
                if valid is not True or isinstance(age,bool) or not isinstance(age,(int,float)) or not np.isfinite(age) or not 0<=age<=3600:
                    continue
                stamp=pd.to_datetime(row.get('recorded_at'),utc=True,errors='coerce')
                if pd.isna(stamp) or stamp>now:continue
                values={}
                for field in SOIL_FIELDS:
                    number=pd.to_numeric(row.get(field),errors='coerce')
                    values[field]=finite(number)
                if values['soil_moisture_percent'] is not None and not 0<=values['soil_moisture_percent']<=100:
                    values['soil_moisture_percent']=None
                if values['soil_temperature_c'] is not None and not -10<=values['soil_temperature_c']<=60:
                    values['soil_temperature_c']=None
                if any(value is not None for value in values.values()):
                    return dict(sensor_time=stamp.isoformat(),readings=values)
            return None
        previous=usable_soil(rows)
        try:
            for offset in range(200,3200,1000):
                if previous:break
                page=reader('sensor_readings',dict(select=','.join(['event_id','recorded_at','device_id',*SOIL_FIELDS,'soil_valid','soil_age_sec']),
                    device_id='eq.'+device,order='recorded_at.desc',limit='1000',offset=str(offset)))
                previous=usable_soil(page)
                if len(page)<1000:break
        except (requests.RequestException,RuntimeError,ValueError):
            result['last_valid_soil_note']='ค้นหาค่าดินย้อนหลังไม่สำเร็จ ลองโหลดใหม่'
        result['last_valid_soil']=previous
    if any(r.get('_quality_metadata_available') is False for r in rows):
        result['quality_status']='legacy_unverified'
        result['prediction_note']='ข้อมูลเดิมไม่มีธงคุณภาพครบ จึงไม่แสดง AI คาดการณ์จากข้อมูลชุดนี้'
        return result
    model_path=ROOT/'models/orchard_soil_6h.json'
    if not model_path.exists():return result
    bundle=json.loads(model_path.read_text(encoding='utf-8'))
    config=bundle['config'];origin=hourly.index[hourly.index<=latest.time].max()
    live=hourly.loc[[origin]].copy()
    forecast=None
    if config['group']=='soil_weather_forecast':
        location=os.environ.get('ORCHARD_LOCATION_ID','')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',location):
            result['prediction_note']='ยังไม่ตั้ง ORCHARD_LOCATION_ID สำหรับพยากรณ์สวน';return result
        raw=reader('weather_forecasts_hourly',dict(select='issued_at,received_at,forecast_time,temperature_c,humidity_percent,rain_mm,source',
                   location_id='eq.'+location,issued_at='gte.'+(origin-pd.Timedelta(hours=24)).isoformat(),
                   order='issued_at.desc',limit='1000'))
        if raw:forecast=forecast_at(prepare_forecasts(pd.DataFrame(raw)),origin)
        if forecast:
            for field,value in forecast.items():live[field]=value
    columns=config['columns'] or ['soil']
    complete=all(c in live and pd.notna(live[c].iloc[0]) for c in columns)
    valid=complete and 0<=age<=60 and pd.Timestamp(bundle['trained_through'])<origin
    value=finite(estimate(bundle['parameters'],live,columns)[0] if bundle['parameters'] else live.soil.iloc[0]) if valid else None
    result['prediction']=dict(status='available' if valid else 'unavailable',group=config['group'],
                              origin_th=origin.tz_convert('Asia/Bangkok').isoformat(),
                              target_th=(origin+pd.Timedelta(hours=HOURS)).tz_convert('Asia/Bangkok').isoformat(),
                              predicted_hour_mean_soil_percent=value)
    return result
