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
