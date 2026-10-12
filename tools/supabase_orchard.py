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
from orchard_live_model import prepare_readings, prepare_forecasts, forecast_at, estimate, HOURS
from clean_stale_weather import WEATHER


def read_table(table,params):
    url=os.environ.get('SUPABASE_URL','').rstrip('/')
    key=os.environ.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not re.fullmatch(r'https://[a-z0-9-]+\.supabase\.co',url) or not key:
        raise RuntimeError('ยังไม่ได้ตั้งค่า Supabase ฝั่งเซิร์ฟเวอร์')
    headers={'apikey':key,'Accept':'application/json'}
    if not key.startswith('sb_secret_'):headers['Authorization']='Bearer '+key
    response=requests.get(url+'/rest/v1/'+table,params=params,headers=headers,timeout=15,allow_redirects=False)
    if response.status_code!=200:
        raise RuntimeError('อ่าน Supabase ไม่สำเร็จ ตรวจคีย์ สิทธิ์ และตาราง โดยไม่เปิด RLS เป็นสาธารณะ')
    rows=response.json()
    if not isinstance(rows,list):raise RuntimeError('รูปแบบข้อมูล Supabase ไม่ถูกต้อง')
    return rows


def orchard_history(period='day', now=None, reader=read_table, end=None):
    """Hourly means first, then daily means; never sum rolling rain readings."""
    if period not in ('day', 'week', 'month'):
        raise ValueError('ช่วงข้อมูลต้องเป็น day, week หรือ month')
    now=pd.Timestamp(now or datetime.now(timezone.utc))
    if end:
        from datetime import date
        selected=date.fromisoformat(end)
        if selected>now.tz_convert('Asia/Bangkok').date():raise ValueError('ไม่เลือกวันอนาคต')
        now=min(now,pd.Timestamp(selected,tz='Asia/Bangkok')+pd.Timedelta(days=1)-pd.Timedelta(microseconds=1))
    device=os.environ.get('ORCHARD_DEVICE_ID','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',device):
        raise RuntimeError('ต้องตั้ง ORCHARD_DEVICE_ID เพื่อเลือกสวน')
    days={'day':1,'week':7,'month':30}[period]
    start=now-pd.Timedelta(days=days)
    values=['soil_moisture_percent','soil_temperature_c','outdoor_temperature_c','outdoor_humidity_percent']
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
        frame[col]=pd.to_numeric(frame[col],errors='coerce').replace([np.inf,-np.inf],np.nan)
    for prefix,cols in [('soil',values[:2]),('weather',values[2:])]:
        bad=frame[prefix+'_valid'].eq(False) | pd.to_numeric(frame[prefix+'_age_sec'],errors='coerce').gt(3600)
        frame.loc[bad,cols]=np.nan
    frame.loc[~frame.soil_moisture_percent.between(0,100),'soil_moisture_percent']=np.nan
    frame.loc[~frame.outdoor_humidity_percent.between(0,100),'outdoor_humidity_percent']=np.nan
    frame=frame.set_index('time').sort_index().tz_convert('Asia/Bangkok')
    hourly=frame[values].resample('h').mean()
    frequency='h' if period=='day' else 'D'
    means=hourly if period=='day' else hourly.resample('D').mean()
    counts=frame[values].resample(frequency).count()
    full=pd.date_range(start.tz_convert('Asia/Bangkok').floor(frequency),now.tz_convert('Asia/Bangkok').floor(frequency),freq=frequency)
    means=means.reindex(full)
    records=[]
    for stamp,row in means.iterrows():
        records.append(dict(time=stamp.isoformat(),**{col:float(row[col]) if pd.notna(row[col]) else None for col in values},
            valid_counts={col:int(counts.loc[stamp,col]) if stamp in counts.index else 0 for col in values}))
    return dict(period=period,source='Supabase',rows=records,raw_count=len(frame),truncated=truncated,
        start=start.isoformat(),end=now.isoformat(),aggregation='ค่าเฉลี่ยรายชั่วโมง' if period=='day' else 'ค่าเฉลี่ยรายวันจากค่าเฉลี่ยรายชั่วโมง',
        message='ข้อมูลจุดเซนเซอร์ ไม่ใช่ค่าเฉลี่ยทั้งสวน; ช่องว่างไม่ใช่ศูนย์')


def live_status(now=None,reader=read_table):
    now=pd.Timestamp(now or datetime.now(timezone.utc))
    device=os.environ.get('ORCHARD_DEVICE_ID','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',device):
        raise RuntimeError('ต้องตั้ง ORCHARD_DEVICE_ID เพื่อไม่ปะปนข้อมูลหลายสวน')
    fields=['event_id','recorded_at','device_id','soil_moisture_percent','soil_temperature_c',*WEATHER,
            'soil_valid','weather_valid','soil_age_sec','weather_age_sec']
    rows=reader('sensor_readings',dict(select=','.join(dict.fromkeys(fields)),device_id='eq.'+device,
                order='recorded_at.desc',limit='200'))
    if not rows:return dict(status='missing',message='ไม่มีข้อมูลเซนเซอร์ของสวนที่ตั้งไว้')
    frame=pd.DataFrame(rows)
    times=pd.to_datetime(frame.recorded_at,utc=True,format='mixed',errors='raise')
    if (times>now+pd.Timedelta(minutes=5)).any():raise RuntimeError('เวลาเซนเซอร์อยู่ในอนาคต ตรวจนาฬิกาอุปกรณ์')
    for field in WEATHER+['soil_moisture_percent','soil_temperature_c']:
        if field not in frame:frame[field]=np.nan
    bad_soil=frame.get('soil_valid',pd.Series(index=frame.index,dtype=object)).eq(False)
    bad_weather=frame.get('weather_valid',pd.Series(index=frame.index,dtype=object)).eq(False)
    bad_soil|=pd.to_numeric(frame.get('soil_age_sec'),errors='coerce').gt(3600) if 'soil_age_sec' in frame else False
    bad_weather|=pd.to_numeric(frame.get('weather_age_sec'),errors='coerce').gt(3600) if 'weather_age_sec' in frame else False
    frame.loc[bad_soil,['soil_moisture_percent','soil_temperature_c']]=np.nan
    frame.loc[bad_weather,WEATHER]=np.nan
    readings,hourly=prepare_readings(frame)
    latest=readings.iloc[-1]
    age=(now-latest.time).total_seconds()/60
    finite=lambda v:float(v) if pd.notna(v) and np.isfinite(v) else None
    result=dict(status='fresh_live' if 0<=age<=60 else 'stale_live',mode='supabase_live',
                sensor_time=latest.time.isoformat(),age_minutes=float(age),soil_percent=finite(latest.soil_moisture_percent),
                vpd_kpa=finite(latest.vpd_kpa),prediction=None)
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
