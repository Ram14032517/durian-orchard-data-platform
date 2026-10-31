/* Metric card layout adapted from the supplied Smart Orchard Cards reference. */
function orchardReferenceCards(data){
  const icons={drop:'<path d="M12 22a8 8 0 0 0 8-8c0-5-8-13-8-13S4 9 4 14a8 8 0 0 0 8 8Z"/>',thermometer:'<path d="M14 14.76V5a3 3 0 0 0-6 0v9.76a5 5 0 1 0 6 0Z"/><path d="M11 10v7"/>',rain:'<path d="M20 15.5A4.5 4.5 0 0 0 17.5 8a6 6 0 0 0-11.3 2.2A4 4 0 0 0 6 17h12"/><path d="m8 20-1 2m6-2-1 2m6-2-1 2"/>',wind:'<path d="M3 8h11a3 3 0 1 0-3-3M2 12h17a3 3 0 1 1-3 3M4 16h6a3 3 0 1 1-3 3"/>'};
  const fields=[['soil_moisture_percent','ความชื้นดิน','drop','blue','%','soil'],['soil_temperature_c','อุณหภูมิดิน','thermometer','amber','°C','soil'],['outdoor_temperature_c','อุณหภูมิอากาศ','thermometer','cyan','°C','weather'],['outdoor_humidity_percent','ความชื้นอากาศ','drop','purple','%','weather'],['rain_1h_mm','ฝนสะสมย้อนหลัง 1 ชั่วโมง','rain','blue','มม.','weather'],['vpd_kpa','VPD อากาศภายนอก','wind','rose','kPa','weather']];
  const label={valid:['ข้อมูลล่าสุด','good'],invalid:['ตรวจสอบอุปกรณ์','bad'],stale:['สงสัยข้อมูลเก่า','warn'],unverified:['ยังไม่ยืนยัน','warn'],missing:['ไม่มีข้อมูล','']};
  const readings=data.readings||{};
  return `<div class="oc"><div class="oc-metrics">${fields.map(([key,name,icon,tone,unit,kind])=>{
    let quality=data.sensor_quality?.[kind]||'unverified';
    if(data.status==='stale_live'&&quality==='valid')quality='stale';
    const value=readings[key], present=Number.isFinite(value), status=quality==='valid'&&!present?'missing':quality;
    const [statusText,statusClass]=label[status]||label.missing;
    const time=data.sensor_time?esc(new Date(data.sensor_time).toLocaleString('th-TH',{timeZone:'Asia/Bangkok'})):'ไม่ระบุเวลา';
    return `<article class="oc-surface oc-metric tone-${tone}" aria-label="${name}"><div class="oc-metric-head"><span class="oc-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[icon]}</svg></span><span class="oc-pill ${statusClass}">${statusText}</span></div><div class="oc-metric-name">${name}</div><div class="oc-metric-value"><span>${present&&status==='valid'?fmt(value,2):'—'}</span><small>${unit}</small></div><div class="oc-metric-meta">จุดเซนเซอร์สวน · ${time}</div></article>`;
  }).join('')}</div></div>`;
}
