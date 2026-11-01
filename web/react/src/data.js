export const data=window.__ORCHARD_DATA__;
export const num=v=>v===null||v===undefined||v===''||!Number.isFinite(Number(v))?null:Number(v);
export const format=(v,d=1)=>num(v)===null?'—':Number(v).toLocaleString('th-TH',{maximumFractionDigits:d});
export const dateTime=v=>v&&!Number.isNaN(Date.parse(v))?new Date(v).toLocaleString('th-TH',{timeZone:'Asia/Bangkok',dateStyle:'medium',timeStyle:'short'}):'ไม่ระบุเวลา';
export const today=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Bangkok',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export const monthNames=['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];
export const metrics=[['soil_moisture_percent','ความชื้นดิน','%','drop','blue','soil'],['soil_temperature_c','อุณหภูมิดิน','°C','temp','amber','soil'],['outdoor_temperature_c','อุณหภูมิอากาศ','°C','sun','cyan','weather'],['outdoor_humidity_percent','ความชื้นอากาศ','%','drop','violet','weather'],['rain_1h_mm','ฝนย้อนหลัง 1 ชั่วโมง','มม.','rain','blue','weather'],['vpd_kpa','VPD อากาศภายนอก','kPa','wind','rose','weather'],['soil_ph','ความเป็นกรดด่างดิน','pH','soil','violet','soil'],['soil_ec','การนำไฟฟ้าดิน','µS/cm','soil','amber','soil'],['soil_n','ไนโตรเจน','mg/kg','leaf','green','soil'],['soil_p','ฟอสฟอรัส','mg/kg','leaf','green','soil'],['soil_k','โพแทสเซียม','mg/kg','leaf','green','soil'],['rain_24h_mm','ฝนย้อนหลัง 24 ชั่วโมง','มม.','rain','blue','weather'],['wind_avg','ลมเฉลี่ย','km/h','wind','cyan','weather'],['wind_gust','ลมกระโชก','km/h','wind','cyan','weather'],['pressure_hpa','ความกดอากาศ','hPa','sun','amber','weather'],['uv_index','ดัชนี UV','ดัชนี','sun','amber','weather'],['light_lux','ความเข้มแสง','lux','sun','amber','weather'],['rain_rate_mm_h','อัตราฝน','mm/h','rain','blue','weather'],['dew_point_c','จุดน้ำค้าง','°C','temp','cyan','weather'],['feels_like_c','อุณหภูมิที่รู้สึก','°C','temp','rose','weather'],['heat_index_c','ดัชนีความร้อน','°C','temp','rose','weather']];
export function sensorState(reading,group,key){
  if(!reading)return 'missing';
  const q=reading.sensor_quality?.[group];
  if(q==='invalid')return 'invalid';
  if(q==='stale'||reading.status?.startsWith('stale'))return 'stale';
  if(q!=='valid')return 'unverified';
  return num(reading.readings?.[key])===null?'missing':'fresh';
}
export function provincePoint(code){const p=data.provinces.find(p=>p.province_code===code);return {code,lat:p.weather_latitude,lon:p.weather_longitude,label:p.province_name,point_kind:'province_reference'};}
export function exportCsv(name,columns,rows){
  const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';
  const text='\uFEFF'+[columns,...rows].map(r=>r.map(quote).join(',')).join('\r\n');
  download(name,text,'text/csv;charset=utf-8');
}
export function download(name,content,type='application/json'){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
