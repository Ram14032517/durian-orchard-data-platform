// Monthly regional context and dated evidence stay separate from live point weather.
const reportMonths=['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน','กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม'];
const reportShort=['ม.ค.','ก.พ.','มี.ค.','เม.ย.','พ.ค.','มิ.ย.','ก.ค.','ส.ค.','ก.ย.','ต.ค.','พ.ย.','ธ.ค.'];
let reportYear=2025,reportMonth=7;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function regionFor(code){return Object.values(DATA.phenology.regions).find(r=>r.provinces.includes(code));}
function stagesFor(code,month){return regionFor(code).periods.filter(p=>p.months.includes(month));}
function stageChips(code,month){return stagesFor(code,month).map(p=>`<span class="stage-chip stage-${p.stage}">${esc(DATA.phenology.stages[p.stage].short)}</span>`).join('');}
function monthWeather(code){return DATA.monthly_weather.find(r=>r.province_code===code&&r.year_ce===reportYear&&r.month===reportMonth);}
function monthHarvest(code){return DATA.harvest.find(r=>r.province_code===code&&r.year_ce===reportYear&&r.month_number===reportMonth);}
function selectReportMonth(month){
  reportMonth=month;
  const ym=`${reportYear}-${String(month).padStart(2,'0')}`;
  $('month').value=ym;$('start').value=ym+'-01';$('end').value=new Date(Date.UTC(reportYear,month,0)).toISOString().slice(0,10);
  invalidateWeather('เลือกเดือนรายงานแล้ว: ตารางด้านบนใช้จุดอ้างอิงจังหวัด หากต้องการอากาศจุด A/B ให้กดดูอากาศด้านล่าง');
  context();
}
function renderMonthlyReport(){
  if(!A)return;
  const code=A.code,name=DATA.provinces.find(p=>p.province_code===code).province_name;
  $('report-province').value=code;
  $('month-buttons').innerHTML=reportShort.map((m,i)=>`<button class="month-card" data-month="${i+1}" aria-pressed="${reportMonth===i+1}" aria-label="รายงาน${reportMonths[i]} ${reportYear+543}"><strong>${m}</strong><small>${stagesFor(code,i+1).map(p=>esc(DATA.phenology.stages[p.stage].short)).join(' · ')}</small></button>`).join('');
  $('month-buttons').querySelectorAll('[data-month]').forEach(b=>b.onclick=()=>selectReportMonth(+b.dataset.month));
  $('report-title').textContent=`${name} · ${reportMonths[reportMonth-1]} ${reportYear+543}`;
  const region=regionFor(code),source=DATA.phenology.calendar_source;
  $('report-stage').innerHTML=stageChips(code,reportMonth)+`<p class="scope-note">กรอบฤดูทั่วไป: ${esc(region.label)} · หมอนทองในฤดู ไม่ใช่ระยะยืนยันของจุด A หรือของปี ${reportYear+543}</p>`+
    stagesFor(code,reportMonth).map(p=>`<p><b>${esc(DATA.phenology.stages[p.stage].label)} (${esc(p.range)})</b><br>${esc(DATA.phenology.stages[p.stage].description)}</p>`).join('')+
    (region.note?`<p class="warn">${esc(region.note)}</p>`:'')+
    `<p class="scope-note"><a href="${esc(source.url)}" target="_blank" rel="noopener">${esc(source.title)}</a> · ${esc(source.locator)}</p>`;
  const w=monthWeather(code),h=monthHarvest(code),point=DATA.provinces.find(p=>p.province_code===code);
  const stats=[['ผลผลิตที่รายงาน',h?fmt(h.tonnes,0)+' ตัน':'ไม่มีระเบียน','สศก. ทั้งจังหวัด ทุกพันธุ์'],
    ['อุณหภูมิเฉลี่ย',w?fmt(w.temperature_c)+' °C':'—',w?`มีค่า ${w.days_temperature}/${w.expected_days} วัน`:'ไม่มีข้อมูลเดือนนี้'],
    ['ฝนรวม',w?fmt(w.rain_mm,2)+' มม.':'—',w?`มีค่า ${w.days_rain}/${w.expected_days} วัน`:'ไม่มีข้อมูลเดือนนี้'],
    ['ความชื้นอากาศ',w?fmt(w.humidity_pct)+' %':'—','เฉลี่ยวันที่มีค่า'],
    ['รังสีดวงอาทิตย์',w?fmt(w.solar_mj_m2_day,2):'—','MJ/m²/วัน; เฉลี่ยวันที่มีค่า'],
    ['ต่างจากเดือนเดียวกัน 1991–2020',w?fmt(w.temperature_anomaly_c)+' °C':'—','อุณหภูมิเฉลี่ย ไม่ใช่ผลต่อผลผลิต']];
  $('report-metrics').innerHTML=stats.map(([label,value,note])=>`<div class="report-stat">${esc(label)}<strong>${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
  $('report-weather-note').innerHTML=`อากาศ <a href="https://power.larc.nasa.gov/docs/services/api/temporal/daily/" target="_blank" rel="noopener">NASA POWER</a> ณ จุดอ้างอิงจังหวัด ${point.weather_latitude}, ${point.weather_longitude} ไม่ใช่ค่าเฉลี่ยทั้งจังหวัดหรืออากาศที่ polygon ดิน/อำเภอที่เลือก วันแบบ LST; เดือนที่ข้อมูลไม่ครบใช้เฉพาะวันที่มีค่า ผลผลิตจาก <a href="https://catalog.oae.go.th/dataset/durian_product_month" target="_blank" rel="noopener">สศก.</a> ไม่ยืนยันเหตุและผลจากอากาศ`;
  const events=DATA.phenology.events.filter(e=>e.province_code===code&&e.year===reportYear&&e.months.includes(reportMonth));
  $('report-events').innerHTML=events.length?events.map(e=>`<article class="evidence-item"><small>${esc(e.kind)} · ${esc(e.district||'ระดับจังหวัด')}</small><p><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a></p><p>${esc(e.summary)}</p><small>วันเหตุ/วันกำหนด: ${esc(e.event_date||'ไม่ระบุ')} · เผยแพร่: ${esc(e.published_date||'ไม่ระบุวันแน่นอน')} · ตรวจแหล่ง ${DATA.phenology.reviewed_on}</small></article>`).join(''):'<p class="scope-note">ยังไม่มีรายงานที่ตรวจยืนยันสำหรับจังหวัดและเดือน–ปีนี้ในฐาน ไม่ได้หมายความว่าไม่มีเหตุการณ์เกิดขึ้น และไม่ดึงข่าวปีอื่นมาแทน</p>';
  $('report-questions').innerHTML=stagesFor(code,reportMonth).map(p=>`<li>${esc(DATA.phenology.stages[p.stage].check)}</li>`).join('');
  $('report-compare').innerHTML=table(['จังหวัด','กรอบระยะทั่วไป','เฉลี่ย °C','ฝนรวม มม.','ตัน/เดือน'],DATA.provinces.map(p=>{const v=monthWeather(p.province_code),o=monthHarvest(p.province_code);return [`<button data-compare-province="${p.province_code}">${esc(p.province_name)}</button>`,stageChips(p.province_code,reportMonth),v?fmt(v.temperature_c):'—',v?fmt(v.rain_mm,2):'—',o?fmt(o.tonnes,0):'—'];}));
  $('report-compare').querySelectorAll('[data-compare-province]').forEach(b=>b.onclick=()=>{$('province').value=b.dataset.compareProvince;provinceChange();});
}
DATA.provinces.forEach(p=>$('report-province').add(new Option(p.province_name,p.province_code)));
for(let y=2026;y>=1981;y--)$('report-year').add(new Option(y+543,y));
$('report-year').value=reportYear;
$('report-year').onchange=()=>{reportYear=+$('report-year').value;selectReportMonth(reportMonth);};
$('report-province').onchange=()=>{$('province').value=$('report-province').value;provinceChange();};
// Existing area selection remains the single source of province state.
const contextBeforeMonthlyReport=context;
context=()=>{contextBeforeMonthlyReport();renderMonthlyReport();};
// Keep the monthly report readable; preserve existing tools as expandable detail.
document.querySelectorAll('aside > section:not(.monthly-report)').forEach(section=>{
  const heading=section.querySelector('h2');if(!heading)return;
  const details=document.createElement('details'),summary=document.createElement('summary');
  summary.textContent=section.querySelector('#events')?'คลังลิงก์ประกอบเดิม (ไม่กรองเดือน/ปี)':heading.textContent;details.append(summary);heading.remove();
  while(section.firstChild)details.append(section.firstChild);
  section.append(details);
});
// Keep the province → district → soil sequence together in section 1.
document.querySelector('.report-controls').append($('overview'));
const areaButton=document.createElement('button');
areaButton.type='button';areaButton.textContent='เลือกอำเภอ / ชุดดิน';
areaButton.onclick=()=>{const details=$('district').closest('details');details.open=true;details.scrollIntoView({behavior:'smooth',block:'start'});$('district').focus();};
document.querySelector('.report-controls').append(areaButton);
const scope=document.createElement('p');scope.className='scope-note';
scope.className='warn';
scope.textContent='รายงานรายเดือน = อากาศจุดอ้างอิงจังหวัด + ผลผลิตทั้งจังหวัด • เลือกอำเภอ/ชุดดินในส่วน 1 เพื่อเปลี่ยนพื้นที่ดินและจุด A; อากาศรายเดือนไม่เปลี่ยน หากต้องการอากาศจุด A ให้เปิด “2. วันที่และอากาศ”';
document.querySelector('.report-controls').after(scope);
