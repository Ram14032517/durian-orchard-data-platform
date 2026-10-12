// District evidence and mapped soil descriptions are deliberately not soil-level targets.
function soilComparisonValues(point){
  if(!point)return ['ยังไม่เลือก','—','—','—','—','—'];
  const province=DATA.provinces.find(p=>p.province_code===point.code)?.province_name||point.code;
  const rows=point.district&&point.soil_code?(point.soil_properties?[point.soil_properties]:DATA.soil_properties.filter(s=>s.province_code===point.code&&s.district===point.district&&s.soil_code===point.soil_code)):[];
  const value=key=>!point.soil_code?'เลือกหน่วยดินก่อน':[...new Set(rows.map(s=>s[key]).filter(v=>v&&v!=='-'))].join(' / ')||'ไม่ระบุ';
  return [province,point.district||'ยังไม่เลือกอำเภอ',point.soil_code?point.soil_code+' '+value('soil_name'):'ยังไม่เลือกหน่วยดิน',value('topsoil_texture'),value('topsoil_ph'),value('fertility')];
}
function renderSoilExploration(){
  if(!A)return;
  const escape=value=>String(value??'ไม่ระบุ').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const district=A.district||'';
  $('soil-analysis-scope').textContent='ระดับหน่วยดินตามแผนที่ LDD ปี 2561 รหัส เช่น Bu เป็นรหัสหน่วยดิน ไม่ใช่ค่าจากเซนเซอร์';
  const a=soilComparisonValues(A),b=soilComparisonValues(B),labels=['จังหวัด','อำเภอ','รหัสและชื่อหน่วยดิน','เนื้อดินบน','ปฏิกิริยาดิน (คำบรรยาย)','ความอุดมสมบูรณ์'];
  $('soil-analysis-properties').innerHTML=table(['ข้อมูล','A','B'],labels.map((label,i)=>[label,escape(a[i]),escape(b[i])]))+'<p class="scope-note">คุณสมบัติมาจากแผนที่ ไม่ใช่ผลตรวจสวนหรือค่า pH ตัวเลข ไม่รวมดินทั้งอำเภอเป็นค่าของจุดอ้างอิง</p>';
  for(const [side,point] of [['A',A],['B',B]]){
    if(!point?.district||point.soil_code)continue;
    const units=DATA.soil_properties.filter(s=>s.province_code===point.code&&s.district===point.district);
    $('soil-analysis-properties').innerHTML+='<details><summary>ดูหน่วยดินทั้งหมดในอำเภอ '+side+'</summary>'+table(['รหัสและชื่อ','เนื้อดินบน','ปฏิกิริยาดิน','ความอุดมสมบูรณ์'],units.map(s=>[s.soil_code+' '+s.soil_name,s.topsoil_texture,s.topsoil_ph,s.fertility].map(escape)))+'</details>';
  }
  const rows=DATA.district_exploration.filter(r=>r.province_code===A.code&&(!district||r.district===district));
  $('district-evidence-table').innerHTML=rows.length?table(['อำเภอ / ปี','ไร่ให้ผล','ตัน','กก./ไร่ รายงาน','กก./ไร่ คำนวณ','ตรวจความละเอียด'],rows.map(r=>[escape(r.district)+' / '+(r.year_ce+543),fmt(r.bearing_rai,0),fmt(r.production_tonnes,0),fmt(r.reported_yield_kg_rai,0),fmt(r.calculated_yield_kg_rai,2),r.yield_precision_warning?'ค่ารายงานไม่ตรงกับยอดปัดเศษ':'—'])):'ยังไม่มีหลักฐานผลผลิตรายอำเภอของพื้นที่นี้ในทะเบียนที่ตรวจแล้ว ไม่แจกยอดจังหวัดลงอำเภอ';
  const numeric=rows.filter(r=>r.reported_yield_kg_rai!==null);
  const max=Math.max(1,...numeric.map(r=>r.reported_yield_kg_rai));
  $('district-yield-bars').replaceChildren();
  for(const r of numeric){
    const line=document.createElement('div');line.className='soil-yield-bar';
    const label=document.createElement('span');label.textContent=`${r.district} ${r.year_ce+543}`;
    const bar=document.createElement('span');bar.className='soil-yield-fill';bar.style.width=`${r.reported_yield_kg_rai/max*100}%`;
    const value=document.createElement('span');value.textContent=`${fmt(r.reported_yield_kg_rai,0)} กก./ไร่`;
    line.append(label,bar,value);$('district-yield-bars').append(line);
  }
  const paired=rows.filter(r=>r.year_ce===2021&&r.reported_yield_kg_rai!==null).map(r=>{
    const old=rows.find(p=>p.district===r.district&&p.year_ce===2020);
    return old&&old.reported_yield_kg_rai>0?`${r.district}: ต่อไร่ ${fmt((r.reported_yield_kg_rai/old.reported_yield_kg_rai-1)*100)}% จากค่ารายงาน; ตัน ${fmt((r.production_tonnes/old.production_tonnes-1)*100)}%; พื้นที่ให้ผล ${fmt((r.bearing_rai/old.bearing_rai-1)*100)}%`:null;
  }).filter(Boolean);
  $('district-analysis-note').textContent=paired.length?paired.join(' • ')+' • เป็นการเปลี่ยนแปลงที่รายงาน ไม่ใช่ผลกระทบของชุดดินหรืออากาศที่พิสูจน์แล้ว':'เลือกอุตรดิตถ์และอำเภอเพื่อดูหลักฐานปี 2563–2564';
  $('district-evidence-link').hidden=!rows.length;
  $('soil-analysis-gap').textContent='ยังไม่มีค่า pH ตัวเลข, N/P/K, อินทรียวัตถุ, ความสามารถอุ้มน้ำ และการจัดการรายแปลงที่ตรวจยืนยัน จึงไม่ให้คะแนนความพร้อมต้น ไม่คำนวณปริมาณปุ๋ย และไม่ฝึกโมเดลผลผลิตรายชุดดินจากข้อมูลนี้';
  $('district-weather-2020').disabled=!numeric.length||!district;
  $('district-weather-2021').disabled=!numeric.length||!district;
}
const selectionBeforeSoilAnalysis=selectA;
selectA=point=>{selectionBeforeSoilAnalysis(point);renderSoilExploration();};
for(const year of [2020,2021])$('district-weather-'+year).onclick=()=>{
  invalidateWeather('กำลังโหลดอากาศทั้งปีสำหรับตรวจข้อมูลทดลอง');
  $('start').value=year+'-01-01';$('end').value=year+'-12-31';$('month').value='';
  context();loadWeather();
  showWorkspaceView('weather-section');
};
