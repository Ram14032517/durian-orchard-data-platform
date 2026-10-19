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
function annualRecords(a,b,year){
  const find=point=>point?DATA.annual.find(r=>r.province_code===point.code&&r.year_ce===year)||null:null;
  return {a:find(a),b:find(b)};
}
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
  $('view-summary').textContent=`ช่วงอากาศ: ${$('start').value} ถึง ${$('end').value} ผลผลิตใช้ปีตามระเบียนที่แสดง`;
  renderAreaStrip();
  updateMapTarget(activeArea);
  const totals=annualRecords(A,B,reportYear);
  $('yield-comparison').innerHTML='<h3>ปีข้อมูลผลผลิต '+(reportYear+543)+' · ระดับจังหวัด ทุกพันธุ์</h3>'+table(['ค่า','A: '+esc(name),B?'B: '+esc(DATA.provinces.find(p=>p.province_code===B.code).province_name):'ยังไม่เลือก B'],[['ผลผลิตรวม ตัน','production_tonnes'],['พื้นที่ให้ผล ไร่','bearing_rai'],['ผลผลิตต่อไร่ กก./ไร่','yield_kg_per_rai_calculated'],['เปลี่ยนต่อไร่จากปีก่อน %','yield_yoy_pct']].map(([label,key])=>[label,fmt(totals.a?.[key]),fmt(totals.b?.[key])]))+'<p class="scope-note">— คือไม่มีระเบียนปีนี้ ไม่ยกปีอื่นมาแทน ผลผลิตจังหวัดเดียวกันจะแสดงเท่ากัน แม้เลือกคนละอำเภอ/ชุดดิน ไม่ใช่ target ผลผลิตจุด A/B</p>';
  const region=regionFor(code),source=DATA.phenology.calendar_source;
  $('report-stage').innerHTML=stageChips(code,reportMonth)+`<p class="scope-note">กรอบฤดูทั่วไป: ${esc(region.label)} · หมอนทองในฤดู ไม่ใช่ระยะยืนยันของจุด A หรือของปี ${reportYear+543}</p>`+
    stagesFor(code,reportMonth).map(p=>`<p><b>${esc(DATA.phenology.stages[p.stage].label)} (${esc(p.range)})</b><br>${esc(DATA.phenology.stages[p.stage].description)}</p>`).join('')+
    (region.note?`<p class="warn">${esc(region.note)}</p>`:'')+
    `<p class="scope-note"><a href="${esc(source.url)}" target="_blank" rel="noopener">${esc(source.title)}</a> · ${esc(source.locator)}</p>`;
  const w=monthWeather(code),h=monthHarvest(code),point=DATA.provinces.find(p=>p.province_code===code);
  const stats=[['ผลผลิตรายเดือน '+(reportYear+543),h?fmt(h.tonnes,0)+' ตัน':'ไม่มีระเบียน','สศก. XLSX · ทั้งจังหวัดทุกพันธุ์ · ยังไม่ยืนยันยอดปิด'],
    ['อุณหภูมิเฉลี่ย',w?fmt(w.temperature_c)+' °C':'—',w?`มีค่า ${w.days_temperature}/${w.expected_days} วัน`:'ไม่มีข้อมูลเดือนนี้'],
    ['ฝนรวม',w?fmt(w.rain_mm,2)+' มม.':'—',w?`มีค่า ${w.days_rain}/${w.expected_days} วัน`:'ไม่มีข้อมูลเดือนนี้'],
    ['ความชื้นอากาศ',w?fmt(w.humidity_pct)+' %':'—','เฉลี่ยวันที่มีค่า'],
    ['รังสีดวงอาทิตย์',w?fmt(w.solar_mj_m2_day,2):'—','MJ/m²/วัน; เฉลี่ยวันที่มีค่า'],
    ['ต่างจากเดือนเดียวกัน 1991–2020',w?fmt(w.temperature_anomaly_c)+' °C':'—','อุณหภูมิเฉลี่ย ไม่ใช่ผลต่อผลผลิต']];
  $('report-metrics').innerHTML=stats.map(([label,value,note])=>`<div class="report-stat">${esc(label)}<strong>${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
  $('report-weather-note').innerHTML=`อากาศ <a href="https://power.larc.nasa.gov/docs/services/api/temporal/daily/" target="_blank" rel="noopener">NASA POWER</a> ณ จุดอ้างอิงจังหวัด ${point.weather_latitude}, ${point.weather_longitude} ไม่ใช่อากาศจุด A/B; วัน LST ใช้เฉพาะวันที่มีค่า ผลผลิตจาก <a href="https://catalog.oae.go.th/dataset/durian_product_month/resource/93c0421b-ebc5-443b-b763-2be1b4a86c5b" target="_blank" rel="noopener">สศก. durian_monthly_province.xlsx</a> ปีตามแถว ${reportYear+543} • วันที่ข้อมูลในไฟล์ 22 ก.ค. 2569 ไม่ใช่ปีผลผลิต • หน้าแคตตาล็อกระบุถึง 2567 แต่ไฟล์ที่ตรวจมีถึง 2568 จึงยังไม่ระบุว่าเป็นยอดปิดจริง • ไม่ใช่ PDF สุราษฎร์ฯ กรกฎาคม 2567`;
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
context=()=>{
  const end=$('end').value;if(end){reportYear=Number(end.slice(0,4));reportMonth=Number(end.slice(5,7));$('report-year').value=String(reportYear);}
  contextBeforeMonthlyReport();renderMonthlyReport();renderSoilExploration();
};
// Keep core controls and summaries visible; collapse only supporting tools.
document.querySelectorAll('aside > section:not(.monthly-report)').forEach(section=>{
  const heading=section.querySelector('h2');if(!heading)return;
  if(section.querySelector('#district'))section.id='area-section';
  if(section.querySelector('#load'))section.id='weather-section';
  if(section.querySelector('#yield'))section.id='yield-section';
  if(['area-section','weather-section','yield-section','soil-analysis','current-section'].includes(section.id))return;
  const details=document.createElement('details'),summary=document.createElement('summary');
  summary.textContent=section.querySelector('#events')?'คลังลิงก์ประกอบเดิม (ไม่กรองเดือน/ปี)':heading.textContent;details.append(summary);heading.remove();
  if(section.id==='area-section')summary.textContent='พื้นที่และชุดดิน';
  if(section.id==='weather-section')summary.textContent='กราฟเปรียบเทียบอากาศ A/B';
  if(section.id==='yield-section')summary.textContent='ผลผลิตและผลทดลองโมเดล';
  if(section.id==='training-section')summary.textContent='ดาวน์โหลดข้อมูลสำหรับวิเคราะห์ / เทรน';
  while(section.firstChild)details.append(section.firstChild);
  section.append(details);
});
document.querySelector('.monthly-report').id='report-section';
const monthlySection=$('report-section');
monthlySection.querySelector('h2').textContent='2. เลือกเดือน ดูฤดูและรายงาน';
$('weather-section').querySelector('h2').textContent='อากาศตามพิกัดอ้างอิง A/B';
$('soil-analysis-title').textContent='คุณสมบัติดินตามแผนที่';
$('yield-section').querySelector('h2').textContent='ผลผลิตจังหวัด A/B และผลทดลองโมเดล';
$('yield-section').before($('soil-analysis'));
DATA.provinces.forEach(p=>{
  const button=document.createElement('button');button.type='button';button.dataset.province=p.province_code;button.textContent=p.province_name;button.setAttribute('aria-pressed','false');
  button.onclick=()=>{areaControl('province').value=p.province_code;provinceChange(activeArea);};$('province-shortcuts').append(button);
});
function showWorkspaceView(id,reveal=true){
  if(id==='map-section'||id==='area-section'){showWorkspaceView('soil-analysis',false);setAreaEditor(true);$('soil-picker').scrollIntoView({behavior:'auto',block:'start'});return;}
  const tab=document.querySelector(`.quick-nav [role="tab"][data-value="${id}"]`);
  if(tab&&tab.getAttribute('aria-selected')!=='true'){tab.click();return;}
  document.body.classList.toggle('orchard-home',id==='current-section');
  document.body.dataset.workspace=id;
  $('toggle-area-editor').textContent=id==='soil-analysis'&&$('soil-picker')?.open?'ย่อพื้นที่':'แก้ไขพื้นที่';
  if(id!=='current-section')requestAnimationFrame(()=>map.invalidateSize());
  const core=['area-section','map-section','report-section','weather-section','soil-analysis','yield-section','training-section','current-section'];
  document.querySelectorAll('aside > section, #workspace-tabs > section').forEach(section=>{if(section.id==='area-section')return;section.hidden=section.id!==id&&!(id==='training-section'&&!core.includes(section.id));});
  document.querySelectorAll('.quick-nav a').forEach(link=>{if(link.getAttribute('href')==='#'+id)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
  if(id==='current-section')$('view-summary').textContent='ข้อมูลจังหวัดเป็นบริบท · ระยะสวนใช้สิ่งที่สังเกตจริง · เวลาของเซนเซอร์กำกับแยกกัน';
  if(id==='training-section'){const detail=$(id).querySelector(':scope > details');if(detail)detail.open=true;}
  if(reveal)$(id).scrollIntoView({behavior:'auto',block:'start'});else document.querySelector('aside').scrollTop=0;
}
const workspaceTop=document.createElement('div');workspaceTop.className='workspace-top';document.querySelector('aside').prepend(workspaceTop);workspaceTop.append(document.querySelector('.quick-nav'),$('area-strip'));
const appHeader=document.querySelector('.orchard-header'),logoutLink=appHeader.querySelector('.logout-link');
workspaceTop.prepend(appHeader);if(logoutLink)workspaceTop.insertBefore(logoutLink,$('area-strip'));
const mapPanel=document.querySelector('.map-pane');mapPanel.id='map-section';
const soilPicker=document.createElement('details');soilPicker.id='soil-picker';soilPicker.open=true;
const soilPickerSummary=document.createElement('summary');soilPickerSummary.textContent='เลือกพื้นที่และชุดดิน · กดย่อเพื่ออ่านรายละเอียด';
soilPicker.append(soilPickerSummary,mapPanel,$('area-section'));$('soil-analysis-title').after(soilPicker);
soilPicker.addEventListener('toggle',()=>setAreaEditor(soilPicker.open));
$('toggle-area-editor').onclick=()=>{const expanded=document.body.dataset.workspace!=='soil-analysis'||!soilPicker.open;showWorkspaceView('soil-analysis',false);setAreaEditor(expanded);};
$('apply-areas').textContent='ดูรายละเอียดดิน';$('apply-areas').onclick=()=>{setAreaEditor(false);$('soil-analysis-scope').scrollIntoView({block:'start'});};
const viewLabels={'current-section':'สวนของฉัน','weather-section':'อากาศ','soil-analysis':'ดิน','yield-section':'ผลผลิต','report-section':'ฤดูกาล','training-section':'ดาวน์โหลด','map-section':'แผนที่'};
document.querySelectorAll('.quick-nav a').forEach(link=>{const id=link.getAttribute('href').slice(1);link.textContent=viewLabels[id];link.onclick=event=>{event.preventDefault();showWorkspaceView(id);};});
showWorkspaceView('current-section',false);
for(const id of ['focus-a','focus-b'])$(id).addEventListener('click',()=>showWorkspaceView('map-section'));
const soilLegend=document.createElement('details');soilLegend.id='soil-legend';soilLegend.className='soil-legend';soilLegend.hidden=true;soilLegend.open=true;document.querySelector('.map-pane').append(soilLegend);
$('soil-analysis-properties').previousElementSibling.remove();
$('district-yield-bars').previousElementSibling.after($('soil-analysis').querySelector('.warn'));
const soilSelectionActions=document.createElement('div');soilSelectionActions.className='soil-selection-actions';
for(const which of ['A','B']){
  const button=document.createElement('button');button.type='button';button.id='edit-soil-'+which.toLowerCase();button.textContent='เลือกดิน '+which;
  button.onclick=async()=>{showWorkspaceView('area-section');if(which==='B')$('comparison-controls').open=true;await focusArea(which);const control=!areaControl('province',which).value?'province':!areaControl('district',which).value?'district':'soil';areaControl(control,which).focus();};
  soilSelectionActions.append(button);
}
$('soil-analysis-scope').after(soilSelectionActions);
// Hide supporting records until needed; headline values remain visible.
for(const [id,title] of [['report-events','รายงานเหตุการณ์ตรงเดือน–ปี'],['report-compare','เทียบทั้ง 5 จังหวัดในเดือนเดียวกัน']]){
  const node=$(id),heading=node.previousElementSibling;
  const detail=document.createElement('details'),summary=document.createElement('summary');summary.textContent=title;
  node.before(detail);detail.append(summary,node);if(heading?.tagName==='H3')heading.remove();
}
const graphButton=document.createElement('button');graphButton.type='button';graphButton.textContent='ดูกราฟอากาศเดือนนี้';
graphButton.onclick=()=>{selectReportMonth(reportMonth);showWorkspaceView('weather-section');loadWeather();};
$('report-section').querySelector('.report-controls').append(graphButton);
const downloadWeather=document.createElement('button');downloadWeather.id='download-weather';downloadWeather.type='button';downloadWeather.disabled=true;downloadWeather.textContent='ดาวน์โหลดอากาศ A/B เป็น CSV';
$('chart').after(downloadWeather);
$('weather').before($('chart-metric').closest('label'),$('chart-note'),$('chart'),downloadWeather);
const exportMessage=document.createElement('p');exportMessage.id='export-message';exportMessage.className='scope-note';exportMessage.setAttribute('role','status');downloadWeather.after(exportMessage);
const weatherFilters=document.createElement('div');weatherFilters.className='weather-filters';
$('load').before(weatherFilters);
for(const id of ['month','start','end'])weatherFilters.append($(id).closest('label'));
weatherFilters.append($('load'));
const customDates=document.createElement('details');customDates.className='custom-dates';
const dateSummary=document.createElement('summary');dateSummary.textContent='กำหนดช่วงวันที่เอง';customDates.append(dateSummary,$('start').closest('label'),$('end').closest('label'));weatherFilters.insertBefore(customDates,$('load'));
$('weather-section').querySelectorAll(':scope > br').forEach(node=>node.remove());
const weatherInfo=$('weather-section').querySelector(':scope > p.muted');
const sourceDetails=document.createElement('details');sourceDetails.className='weather-source';const sourceSummary=document.createElement('summary');sourceSummary.textContent='แหล่งข้อมูลและข้อจำกัดของอากาศกริด';weatherInfo.before(sourceDetails);sourceDetails.append(sourceSummary,weatherInfo);
const weatherPlot=document.createElement('div');weatherPlot.className='weather-plot';
const plotToolbar=document.createElement('div');plotToolbar.className='plot-toolbar';
const expandWeather=document.createElement('button');expandWeather.type='button';expandWeather.dataset.expandPlot='';expandWeather.textContent='ขยายกราฟ';expandWeather.setAttribute('aria-label','ขยายกราฟอากาศ A/B');
$('chart-metric').closest('label').before(weatherPlot);plotToolbar.append($('chart-metric').closest('label'),expandWeather);weatherPlot.append(plotToolbar,$('chart-note'),$('chart'));
document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-expand-plot]');if(!button)return;
  const panel=button.closest('.weather-plot,.telemetry-panel');
  try{if(document.fullscreenElement===panel)await document.exitFullscreen();else if(panel.requestFullscreen)await panel.requestFullscreen();else throw new Error('เบราว์เซอร์นี้ไม่รองรับการขยายเต็มจอ');}
  catch(error){const note=panel.querySelector('.plot-message')||$('chart-note');note.textContent='ขยายกราฟไม่ได้: '+error.message;}
});
document.addEventListener('fullscreenchange',()=>document.querySelectorAll('[data-expand-plot]').forEach(button=>{button.textContent=document.fullscreenElement===button.closest('.weather-plot,.telemetry-panel')?'กลับหน้าปกติ':'ขยายกราฟ';}));
function weatherCsv(snapshot){
  const metrics=Object.keys(chartMetrics),headers=['area','province_code','location_label','selected_latitude','selected_longitude','data_latitude','data_longitude','date',...metrics,'time_standard','source_basis','source_label','source_url','retrieved_utc','warning'];
  const quote=value=>'"'+String(value??'').replace(/"/g,'""')+'"';
  const records=[[snapshot.resultA,snapshot.a,'A'],[snapshot.resultB,snapshot.b,'B']].flatMap(([result,point,area])=>!result||!point?[]:result.rows.map(row=>[area,point.code,point.label,point.lat,point.lon,result.dataLat,result.dataLon,row.date,...metrics.map(key=>row[key]),result.timeStandard,result.basis,result.source,result.sourceUrl,result.retrievedUtc,result.warning]));
  return '\ufeff'+[headers,...records].map(row=>row.map(quote).join(',')).join('\r\n');
}
downloadWeather.onclick=async()=>{
  if(!weatherExportState)return;
  const snapshot=weatherExportState,content=weatherCsv(snapshot);downloadWeather.disabled=true;exportMessage.textContent='กำลังบันทึก CSV ในเครื่อง…';
  try{
    const response=await fetch('/api/weather-export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({start:snapshot.start,end:snapshot.end,csv:content})});
    if(!(response.headers.get('content-type')||'').includes('application/json'))throw Error('ต้องเปิดผ่านเซิร์ฟเวอร์โครงการรุ่นล่าสุด');
    const result=await response.json();if(!response.ok)throw Error(result.error||`HTTP ${response.status}`);
    if(weatherExportState!==snapshot)return;
    exportMessage.textContent=`บันทึก ${result.rows} แถว (${snapshot.start} ถึง ${snapshot.end}) ใน ${result.folder}/ แล้ว • `;
    const link=document.createElement('a');link.href=result.url;link.download=result.filename;link.textContent='เปิด / ดาวน์โหลด CSV';exportMessage.append(link);
  }catch(error){
    exportMessage.textContent='บันทึกในเครื่องไม่ได้: '+error.message+' • ';
    const url=URL.createObjectURL(new Blob([content],{type:'text/csv;charset=utf-8'})),link=document.createElement('a');link.href=url;link.download=`weather_AB_${snapshot.start}_${snapshot.end}.csv`;link.textContent='ลองดาวน์โหลดผ่านเบราว์เซอร์';exportMessage.append(link);
    setTimeout(()=>URL.revokeObjectURL(url),60000);
  }finally{downloadWeather.disabled=!weatherExportState;}
};
const weatherLoaderBeforeUx=loadWeather;
loadWeather=async()=>{downloadWeather.disabled=true;weatherExportState=null;await weatherLoaderBeforeUx();downloadWeather.disabled=!weatherExportState||!chartRowsA.length;};
$('load').onclick=loadWeather;
const invalidatorBeforeUx=invalidateWeather;
invalidateWeather=message=>{invalidatorBeforeUx(message);weatherExportState=null;downloadWeather.disabled=true;exportMessage.textContent='';};
const selectorBeforeUx=selectA;
selectA=point=>{weatherExportState=null;downloadWeather.disabled=true;exportMessage.textContent='';selectorBeforeUx(point);};
fetch('training/manifest.json').then(response=>{if(!response.ok)throw Error(response.status);return response.json();}).then(meta=>{
  const note=document.createElement('p');note.className='view-summary';note.textContent=`ชุดรายเดือน ${fmt(meta.rows,0)} แถว • ผ่านเงื่อนไข baseline ${fmt(meta.eligible_rows,0)} แถว • train ${meta.eligible_by_split.train} / validation ${meta.eligible_by_split.validation} / test ${meta.eligible_by_split.test}`;
  $('training-section').querySelector('.training-links').before(note);
}).catch(()=>{});
// Keep the province → district → soil sequence together in section 1.
$('report-section').querySelector('.report-controls').append($('overview'));
const areaButton=document.createElement('button');
areaButton.type='button';areaButton.textContent='เลือกอำเภอ / ชุดดิน';
areaButton.onclick=()=>{showWorkspaceView('area-section');$('district').focus();};
$('report-section').querySelector('.report-controls').append(areaButton);
const scope=document.createElement('p');scope.className='scope-note';
scope.className='warn';
scope.textContent='รายงานรายเดือน = อากาศจุดอ้างอิงจังหวัด + ผลผลิตทั้งจังหวัด • เลือกอำเภอ/ชุดดินในส่วน 1 เพื่อเปลี่ยนพื้นที่ดินและจุด A; หากต้องการอากาศจุด A ใช้ส่วน 3 “วันที่และกราฟอากาศ A/B” ไม่ใช้ตัวเลขจังหวัดแทนค่าของสวน';
$('report-section').querySelector('.report-controls').after(scope);
const productionProvenance=document.createElement('p');productionProvenance.className='scope-note';
productionProvenance.innerHTML='แหล่งผลผลิตรายปี: <a href="https://catalog.oae.go.th/dataset/durian_product/resource/3f9531b0-dc97-415a-a8d5-aa7c89f0c7b3" target="_blank" rel="noopener">สศก. durian_province.xlsx</a> • ปีตามแถว 2540–2568 • วันที่ข้อมูลในไฟล์ 14 ก.ค. 2569 ไม่ใช่ปีผลผลิต • สถานะยอดจริง/ประมาณการยังไม่ยืนยัน หน้าแคตตาล็อกระบุถึง 2567 ต่างจากไฟล์ที่ตรวจ ไม่ใช้ปีจัดพิมพ์ PDF เปลี่ยนปีของตัวเลขเหล่านี้';
$('yield-note').after(productionProvenance);
const yieldComparison=document.createElement('div');yieldComparison.id='yield-comparison';productionProvenance.after(yieldComparison);
const historyHeading=document.createElement('h3');historyHeading.textContent='ประวัติผลผลิตจังหวัดของ A';$('yield').before(historyHeading);

// Keep orchard observations independent from A/B reference-point selection.
const currentYear=new Date().getFullYear();
[currentYear,currentYear+1].forEach(y=>$('current-year').add(new Option(String(y+543),String(y))));
DATA.provinces.forEach(p=>$('orchard-province').add(new Option(p.province_name,p.province_code)));
const orchardStateKey='durian.orchard.observations.v1';
function orchardCalendar(){
  const code=$('orchard-province').value;
  $('orchard-calendar').textContent=code?'กรอบปฏิทินเดือนปัจจุบันของจังหวัดสวน: '+stagesFor(code,new Date().getMonth()+1).map(p=>DATA.phenology.stages[p.stage].label).join(' / ')+' · ไม่ใช่ระยะยืนยันของสวน':'เลือกจังหวัดสวนเพื่อดูบริบทฤดู โดยไม่เปลี่ยนพื้นที่ A/B';
}
try{
  const entries=JSON.parse(localStorage.getItem(orchardStateKey)||'[]');
  const last=Array.isArray(entries)?entries.at(-1):null;
  if(last){for(const field of ['province','stage','water','situation']){const control=$('orchard-'+field);if([...control.options].some(o=>o.value===last[field]))control.value=last[field];}
    $('orchard-state-note').textContent='สถานะบันทึกในเบราว์เซอร์นี้เมื่อ '+last.observed_at+' ไม่ใช่ข้อมูลระยะที่เซนเซอร์ตรวจได้';}
}catch{$('orchard-state-note').textContent='อ่านสถานะเดิมไม่ได้ กรุณาบันทึกใหม่';}
orchardCalendar();$('orchard-province').onchange=orchardCalendar;
$('save-orchard-state').onclick=()=>{
  if(!$('orchard-province').value){$('orchard-state-note').textContent='เลือกจังหวัดสวนจริงก่อนบันทึก';return;}
  try{
    const previous=JSON.parse(localStorage.getItem(orchardStateKey)||'[]');
    const entry={observed_at:new Date().toISOString()};
    for(const field of ['province','stage','water','situation'])entry[field]=$('orchard-'+field).value;
    localStorage.setItem(orchardStateKey,JSON.stringify([...(Array.isArray(previous)?previous:[]),entry].slice(-200)));
    $('orchard-state-note').textContent='บันทึกเมื่อ '+new Date(entry.observed_at).toLocaleString('th-TH')+' · เก็บเฉพาะเบราว์เซอร์นี้ ยังไม่ส่งชีตหรือใช้เทรน';
  }catch{$('orchard-state-note').textContent='บันทึกไม่ได้: ตรวจการอนุญาตพื้นที่เก็บข้อมูลของเบราว์เซอร์';}
};
async function currentJson(url){
  const response=await fetch(url,{cache:'no-store'});
  if(!response.headers.get('content-type')?.includes('application/json'))throw Error('HTTP '+response.status+' · เซิร์ฟเวอร์ไม่ส่งข้อมูล JSON');
  const data=await response.json();if(data.error)throw Error(data.error);return data;
}
let currentRequest=0;
async function refreshCurrent(){
  if(!A)return;
  const request=++currentRequest,code=A.code,year=$('current-year').value;
  const name=DATA.provinces.find(p=>p.province_code===code).province_name;
  if(!$('current-section').hidden)$('view-summary').textContent='จังหวัด '+name+' ปี '+(+year+543)+' · สวนส่วนตัวแยกจากตำแหน่งอ้างอิง A/B';
  $('current-province').textContent='กำลังคำนวณ '+name+' '+(+year+543)+' จากโมเดลเดิมและอากาศล่าสุด…';
  await Promise.all([
    currentJson('/api/orchard-status').then(data=>{
      if(request!==currentRequest)return;
      if(data.status==='missing'){$('current-orchard').textContent=data.message;return;}
      const liveSource=data.mode==='supabase_live',stale=data.status.startsWith('stale');
      $('current-orchard').nextElementSibling.textContent=liveSource?'อ่านข้อมูลล่าสุดจาก Supabase ทุก 5 นาทีเมื่อเปิดแท็บนี้ ค่าวัดมีเวลาจริงและเตือนเมื่อเก่า':'ตรวจไฟล์ snapshot ทุก 5 นาที ไม่ใช่การเชื่อมชีตโดยตรง แสดงเวลาวัดเสมอและเตือนเมื่อเก่าเกิน 1 ชั่วโมง';
      const sourceLabel=liveSource?'Supabase สด':'snapshot ในเครื่อง';
      const prediction=data.prediction;
      const projection=!stale&&prediction?.status==='available'?`<div class="report-stat"><span>ความชื้นคาดการณ์ 6 ชั่วโมง</span><strong>${fmt(prediction.predicted_hour_mean_soil_percent,2)}%</strong><small>สิ้นสุด ${esc(prediction.target_th)} · ${esc(prediction.group||'persistence')} · ไม่ใช่ผลผลิต</small></div>`:'';
      $('current-orchard').innerHTML=`<div class="report-stat"><span>ความชื้นจุดเซนเซอร์</span><strong>${fmt(data.soil_percent,1)}%</strong><small>ยังไม่สอบเทียบ ไม่ใช่ค่าเฉลี่ยทั้งสวน</small></div><div class="report-stat"><span>VPD อากาศภายนอก</span><strong>${fmt(data.vpd_kpa,2)} kPa</strong><small>ไม่ได้ใช้ค่าอากาศในบ้าน</small></div>${projection}<p class="scope-note">${sourceLabel} · วัด ${esc(data.sensor_time)} · ${stale?'ข้อมูลเก่า ตรวจการส่งจากอุปกรณ์':'ข้อมูลภายใน 1 ชั่วโมง'} · อายุ ${fmt(data.age_minutes,0)} นาที</p>`;
    }).catch(e=>{if(request===currentRequest)$('current-orchard').textContent='อ่านข้อมูลสวนไม่ได้: '+e.message;}),
    currentJson('/api/province-estimate?province='+encodeURIComponent(code)+'&year='+year).then(data=>{
      if(request!==currentRequest)return;
      $('current-province').innerHTML=`<div class="report-stat"><span>${esc(name)} · ปี ${+year+543} · ระดับจังหวัด ทุกพันธุ์</span><strong>${data.predicted_kg_rai===null?'ยังคำนวณไม่ได้':fmt(data.predicted_kg_rai,1)+' กก./ไร่'}</strong><p>${esc(data.message)}</p><small>ตัดข้อมูล ${esc(data.as_of)} · หน้าต่างอากาศ ${esc(data.weather_start)} ถึง ${esc(data.weather_end)} · อายุผลสมมุติ ${data.age_days} วัน</small>${data.stale_cache?'<p class="warn">ใช้ cache เก่า เพราะดึงข้อมูลใหม่ไม่สำเร็จ</p>':''}</div>`;
    }).catch(e=>{if(request===currentRequest)$('current-province').textContent='คำนวณจังหวัดไม่ได้: '+e.message;})
  ]);
}
$('current-year').onchange=refreshCurrent;$('refresh-current').onclick=refreshCurrent;
const selectBeforeCurrent=selectA;
selectA=point=>{selectBeforeCurrent(point);refreshCurrent();};
setInterval(()=>{if(!document.hidden&&!$('current-section').hidden)refreshCurrent();},300000);

// Orchard telemetry is independent of the research map's A/B coordinates.
document.querySelector('header h1').textContent='สวนทุเรียนของฉัน';
document.querySelector('.header-description').textContent='ติดตามดินและอากาศจากเซนเซอร์ พร้อมดูแนวโน้มย้อนหลังและวิเคราะห์ 5 จังหวัด';
$('current-section').querySelector('h2').textContent='ภาพรวมสวน';
$('current-section').querySelector('.scope-note').textContent='ข้อมูลจุดเซนเซอร์ในสวน แยกจากจุดอ้างอิงจังหวัดและแผนที่ A/B';
const orchardDashboard=document.createElement('div');
orchardDashboard.className='orchard-telemetry';
orchardDashboard.innerHTML=`<div class="telemetry-toolbar"><div><h3>ดินและอากาศย้อนหลัง</h3><p>ข้อมูลสวนจาก Supabase · เวลาไทย</p></div><div class="telemetry-actions"><label>ช่วงเวลา <select id="orchard-period"><option value="day">รายวัน · 24 ชั่วโมง</option><option value="week">รายสัปดาห์ · 7 วัน</option><option value="month">รายเดือน · 30 วัน</option></select></label><button id="refresh-history" type="button">โหลดข้อมูลใหม่</button></div></div><p id="orchard-history-note" role="status">กำลังโหลดประวัติสวน…</p><div id="orchard-timeseries" class="telemetry-grid"></div><details class="telemetry-table"><summary>ดูค่าตารางและจำนวนตัวอย่าง</summary><div id="orchard-history-table"></div></details>`;
$('current-orchard').nextElementSibling.after(orchardDashboard);
const provinceDetails=document.createElement('details');provinceDetails.className='province-context';
const provinceSummary=document.createElement('summary');provinceSummary.textContent='ประมาณการผลผลิตจังหวัด · ไม่ใช่ผลผลิตสวน';provinceDetails.append(provinceSummary);
provinceDetails.append($('current-year').closest('.report-controls'),$('current-province').previousElementSibling,$('current-province'));
$('current-section').append(provinceDetails);
const telemetryFields=[['soil_moisture_percent','ความชื้นดิน','%','#087f8c'],['soil_temperature_c','อุณหภูมิดิน','°C','#b45309'],['outdoor_temperature_c','อุณหภูมิอากาศภายนอก','°C','#2563eb'],['outdoor_humidity_percent','ความชื้นอากาศภายนอก','%','#087f8c']];
function telemetryChart(rows,field,label,unit,color){
  const valid=rows.map(r=>r[field]).filter(v=>Number.isFinite(v));
  if(!valid.length)return `<article class="telemetry-panel"><h3>${label} <small>${unit}</small></h3><p class="empty-series">ไม่มีค่าที่ใช้ได้ในช่วงนี้</p></article>`;
  const W=640,H=205,L=54,R=16,T=18,B=36;
  let low=Math.min(...valid),high=Math.max(...valid),pad=Math.max((high-low)*.15,unit==='%'?1:.5);low-=pad;high+=pad;
  if(unit==='%'){low=Math.max(0,low);high=Math.min(100,high);}
  const x=i=>L+i*(W-L-R)/Math.max(rows.length-1,1),y=v=>T+(high-v)*(H-T-B)/(high-low||1);
  let path='',connected=false;
  const dots=rows.map((r,i)=>{const v=r[field];if(!Number.isFinite(v)){connected=false;return '';}
    path+=`${connected?'L':'M'}${x(i).toFixed(1)},${y(v).toFixed(1)} `;connected=true;
    return `<circle cx="${x(i)}" cy="${y(v)}" r="3" fill="${color}"><title>${esc(new Date(r.time).toLocaleString('th-TH'))}: ${fmt(v,2)} ${unit} · ${r.valid_counts[field]} ตัวอย่าง</title></circle>`;
  }).join('');
  const grid=[0,1,2,3].map(i=>{const v=low+(high-low)*i/3;return `<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" stroke="#dce5f0"/><text x="${L-8}" y="${y(v)+4}" text-anchor="end">${fmt(v,1)}</text>`;}).join('');
  const ticks=[0,Math.floor((rows.length-1)/2),rows.length-1].map(i=>`<text x="${x(i)}" y="${H-10}" text-anchor="${i===0?'start':i===rows.length-1?'end':'middle'}">${esc(new Date(rows[i].time).toLocaleString('th-TH',{month:'short',day:'numeric',...(rows.length<=25?{hour:'2-digit',minute:'2-digit'}:{})}))}</text>`).join('');
  return `<article class="telemetry-panel"><div class="telemetry-panel-heading"><h3>${label} <small>${unit}</small></h3><span style="color:${color}">เฉลี่ย ${fmt(valid.reduce((a,b)=>a+b,0)/valid.length,1)}</span><button type="button" data-expand-plot aria-label="ขยายกราฟ${label}">ขยายกราฟ</button></div><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${label} ตามเวลา หน่วย ${unit}">${grid}<path d="${path}" stroke="${color}" stroke-width="2" fill="none"/>${dots}${ticks}</svg><p class="plot-message" role="status">ต่ำสุด ${fmt(Math.min(...valid),1)} · สูงสุด ${fmt(Math.max(...valid),1)} · มีค่า ${valid.length}/${rows.length} ช่วง</p></article>`;
}
let historyRequest=0;
async function refreshOrchardHistory(){
  const request=++historyRequest;
  $('orchard-history-note').textContent='กำลังอ่านข้อมูลสวนจาก Supabase…';
  $('orchard-timeseries').innerHTML=telemetryFields.map(f=>telemetryChart([],...f)).join('');$('orchard-history-table').replaceChildren();
  try{
    const data=await currentJson('/api/orchard-history?period='+$('orchard-period').value+'&end='+$('orchard-history-end').value);
    if(request!==historyRequest)return;
    $('orchard-history-note').textContent=`${data.source} · ${data.raw_count} ระเบียน · ${data.aggregation||''} · ${data.message}${data.truncated?' · ข้อมูลบางส่วน: ถึงขีดจำกัด 30,000 ระเบียน':''}`;
    $('orchard-timeseries').innerHTML=telemetryFields.map(f=>telemetryChart(data.rows,...f)).join('');
    $('orchard-history-table').innerHTML=table(['เวลาไทย',...telemetryFields.map(f=>f[1]+' ('+f[2]+')'),'ตัวอย่างดิน / อากาศ'],data.rows.map(r=>[esc(new Date(r.time).toLocaleString('th-TH')),...telemetryFields.map(f=>fmt(r[f[0]],2)),`${r.valid_counts.soil_moisture_percent} / ${r.valid_counts.outdoor_temperature_c}`]));
  }catch(error){if(request===historyRequest)$('orchard-history-note').textContent='โหลดประวัติสวนไม่ได้: '+error.message+' · ตรวจการเชื่อม Supabase ฝั่งเซิร์ฟเวอร์';}
}
const historyEndLabel=document.createElement('label');historyEndLabel.textContent='ถึงวันที่';
const historyEnd=document.createElement('input');historyEnd.type='date';historyEnd.id='orchard-history-end';
historyEnd.value=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Bangkok'}).format(new Date());historyEnd.max=historyEnd.value;
historyEndLabel.append(historyEnd);document.querySelector('.telemetry-actions').prepend(historyEndLabel);
$('orchard-period').onchange=refreshOrchardHistory;historyEnd.onchange=refreshOrchardHistory;
const periodButtons=document.createElement('div');periodButtons.className='period-switch';periodButtons.setAttribute('role','group');periodButtons.setAttribute('aria-label','ช่วงเวลาข้อมูลสวน');
for(const [value,label] of [['day','วัน'],['week','สัปดาห์'],['month','เดือน']]){
  const button=document.createElement('button');button.type='button';button.textContent=label;button.dataset.period=value;button.setAttribute('aria-pressed',String(value===$('orchard-period').value));
  button.onclick=()=>{$('orchard-period').value=value;periodButtons.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));refreshOrchardHistory();};periodButtons.append(button);
}
$('orchard-period').closest('label').hidden=true;document.querySelector('.telemetry-actions').append(periodButtons);
$('current-orchard').nextElementSibling.textContent='แสดงแหล่งข้อมูลและเวลาวัดจริง ตรวจอัปเดตทุก 5 นาที และแจ้งเมื่อข้อมูลเก่าเกิน 1 ชั่วโมง';
$('refresh-history').onclick=()=>{refreshOrchardHistory();refreshCurrent();};
refreshOrchardHistory();
setInterval(()=>{if(!document.hidden&&!$('current-section').hidden)refreshOrchardHistory();},300000);
