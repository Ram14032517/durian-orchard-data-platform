/* Private seasonal harvests: server persistence only; never derive orchard yield from GAP/OAE. */
(function(root){
  'use strict';
  const numeric=value=>value===null||value===undefined||String(value).trim()===''?null:Number(value);
  function payload(values,yearNow){
    const data={};
    for(const key of ['orchard_code','season_key','cultivar','province_code','harvest_start','harvest_end','source_type','source_reference','status'])data[key]=String(values[key]||'').trim();
    data.harvest_year=numeric(values.harvest_year);
    if(!Number.isInteger(data.harvest_year)||data.harvest_year<1981||data.harvest_year>yearNow)throw Error('ระบุปี ค.ศ. ที่เก็บเกี่ยวแล้ว');
    for(const key of ['bearing_area_rai','harvested_kg']){
      data[key]=numeric(values[key]);
      if(data[key]!==null&&(!Number.isFinite(data[key])||data[key]<0||(key==='bearing_area_rai'&&data[key]===0)))throw Error('พื้นที่ให้ผลต้องมากกว่า 0 น้ำหนักไม่ติดลบ ไม่ทราบให้เว้นว่าง');
    }
    data.actual_harvest_confirmed=values.actual_harvest_confirmed===true||values.actual_harvest_confirmed==='on';
    return data;
  }
  function historyGroups(records){
    const groups=new Map();
    for(const r of records){
      const yieldValue=numeric(r.yield_kg_per_rai),year=numeric(r.harvest_year);
      if(r.status!=='complete'||yieldValue===null||!Number.isFinite(yieldValue)||yieldValue<0||!Number.isInteger(year))continue;
      const key=JSON.stringify([r.orchard_code,r.season_key]);
      if(!groups.has(key))groups.set(key,{orchard:r.orchard_code,season:r.season_key,points:[]});
      groups.get(key).points.push({year,value:yieldValue});
    }
    return [...groups.values()].map(g=>({...g,points:g.points.sort((a,b)=>a.year-b.year)}));
  }
  root.OrchardHarvestHelpers=Object.freeze({numeric,payload,historyGroups});
  if(!root.document)return;
  function init(){
    const doc=root.document,home=doc.getElementById('current-section');
    if(!home||doc.getElementById('orchard-harvest-section'))return;
    const panel=doc.createElement('section');panel.id='orchard-harvest-section';panel.className='private-harvest';
    panel.innerHTML=`<h3>ประวัติผลผลิตจริง — สวนของฉัน</h3>
      <p class="scope-note">ข้อมูลส่วนตัวตามบัญชีที่เข้าสู่ระบบ เก็บในฐานข้อมูล Supabase ไม่ใช้เบราว์เซอร์เป็นฐานข้อมูล และไม่ย้ายตามหมุด GAP หรือพื้นที่ A/B</p>
      <p id="harvest-status" role="status" aria-live="polite">กำลังตรวจสิทธิ์…</p>
      <div class="report-controls"><a id="harvest-login" href="/login" target="_blank" rel="noopener">เข้าสู่ระบบบันทึกสวน</a><button id="harvest-reload" type="button">โหลดประวัติใหม่</button><button id="harvest-export" type="button" disabled>ดาวน์โหลดข้อมูลเฉพาะบัญชีฉัน</button></div>
      <form id="harvest-form"><fieldset disabled><legend>บันทึกหนึ่งสวน–ปี–ฤดู ไม่รวมหลายสวนเป็นรายการเดียว</legend><div class="harvest-fields">
      <label>รหัสสวนของคุณ (ใช้รหัสเดิมข้ามปี)<input name="orchard_code" maxlength="64" required placeholder="เช่น สวน-001 ไม่ต้องใส่ชื่อเจ้าของ"></label>
      <label>ฤดู (ใช้ชื่อเดิมข้ามปี)<input name="season_key" maxlength="64" value="main" required></label>
      <label>ปีเก็บเกี่ยว ค.ศ.<input name="harvest_year" type="number" min="1981" required></label>
      <label>พันธุ์ / หลายพันธุ์<input name="cultivar" maxlength="120" placeholder="ระบุพันธุ์ที่รวมในพื้นที่และน้ำหนักนี้"></label>
      <label>รหัสจังหวัด (ถ้าทราบ)<input name="province_code" inputmode="numeric" pattern="[1-9][0-9]" maxlength="2" placeholder="เช่น 22"></label>
      <label>พื้นที่ให้ผลจริงในฤดูนี้ (ไร่)<input name="bearing_area_rai" type="number" min="0.000001" step="0.000001" placeholder="ไม่ใช้พื้นที่ปลูกตาม GAP แทน"></label>
      <label>น้ำหนักเก็บเกี่ยวจริงครบฤดู (กก.)<input name="harvested_kg" type="number" min="0" step="0.000001" placeholder="ศูนย์ได้เมื่อผลจริงเป็นศูนย์"></label>
      <label>วันที่เริ่มเก็บเกี่ยว<input name="harvest_start" type="date"></label><label>วันที่สิ้นสุดเก็บเกี่ยว<input name="harvest_end" type="date"></label>
      <label>แหล่งข้อมูล<select name="source_type"><option value="farm_log">สมุดบันทึกสวน</option><option value="weighbridge">ใบชั่ง</option><option value="sales_receipts">ใบรับซื้อที่รวบรวมครบ</option><option value="self_report">เจ้าของรายงานเอง</option></select></label>
      <label>สถานะ<select name="status"><option value="draft">ร่าง — ข้อมูลยังไม่ครบ</option><option value="complete">ปิดฤดู — เก็บเกี่ยวและบันทึกครบแล้ว</option></select></label>
      <label class="harvest-wide">รายละเอียดหลักฐาน / วิธีรวบรวมน้ำหนัก<textarea name="source_reference" maxlength="1000" placeholder="เช่น เลขอ้างอิงสมุดหรือใบชั่ง ไม่ต้องใส่ชื่อ เบอร์โทร หรือพิกัด"></textarea></label>
      </div><label class="harvest-confirm"><input name="actual_harvest_confirmed" type="checkbox"> ยืนยันว่าน้ำหนักนี้เป็นผลเก็บเกี่ยวจริงทั้งฤดูของพื้นที่ให้ผลที่ระบุ ไม่ใช่ปริมาณ GAP หรือเฉพาะส่วนส่งออก</label>
      <div class="report-controls"><button type="submit" id="harvest-save">บันทึกถาวรในบัญชีฉัน</button><button type="button" id="harvest-cancel">ยกเลิกการแก้ไข / เริ่มรายการใหม่</button></div></fieldset></form>
      <h4>ค่าฐานจากผลฤดูก่อน — Baseline ไม่ใช่ AI Forecast</h4><div id="harvest-baselines" class="report-grid">ยังไม่มีข้อมูล</div>
      <h4>แนวโน้มผลผลิตสวนที่บันทึกจริง</h4><div id="harvest-charts" class="harvest-charts">กำลังอ่านข้อมูล…</div>
      <h4>ประวัติที่บันทึกและแก้ไขได้</h4><div class="harvest-table" tabindex="0" aria-label="ตารางประวัติสวน เลื่อนแนวนอนได้"><table><thead><tr><th>สวน / ฤดู</th><th>ปี พ.ศ. (ค.ศ.)</th><th>พันธุ์</th><th>พื้นที่ให้ผล ไร่</th><th>เก็บเกี่ยว กก.</th><th>กก./ไร่</th><th>วันที่เก็บเกี่ยว</th><th>แหล่ง / สถานะ</th><th>รุ่น / แก้ไข</th></tr></thead><tbody id="harvest-rows"></tbody></table></div>
      <p class="scope-note">ตัวเลขยังเป็นข้อมูลที่ผู้ใช้รายงาน ไม่ได้ตรวจหลักฐานอิสระ การบันทึกย้อนหลังไม่พิสูจน์ว่าเคยทราบข้อมูล ณ วันพยากรณ์ ระบบเก็บรุ่นก่อนแก้ไขและไม่ Auto-train</p>
      <h4>ความพร้อมประมาณการทดลองระดับจังหวัด</h4><p id="harvest-forecast-readiness" class="warn" role="status">กำลังตรวจสถานะโมเดล…</p>`;
    home.append(panel);
    const el=id=>doc.getElementById(id),form=el('harvest-form'),fieldset=form.querySelector('fieldset');
    const yearNow=Number(new Intl.DateTimeFormat('en',{year:'numeric',timeZone:'Asia/Bangkok'}).format(new Date()));
    form.elements.harvest_year.max=String(yearNow);form.elements.harvest_year.value=String(yearNow);
    const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Bangkok',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
    for(const name of ['harvest_start','harvest_end'])form.elements[name].max=today;
    let csrf=null,editing=null,loading=0,busy=false,account=null;
    const status=text=>{el('harvest-status').textContent=text;};
    const fmt=value=>value===null||value===undefined?'ยังไม่ครบ':Number(value).toLocaleString('th-TH',{maximumFractionDigits:3});
    async function api(path,method='GET',data){
      const response=await root.fetch(path,{method,credentials:'same-origin',cache:'no-store',headers:{...(data?{'Content-Type':'application/json'}:{}),...(csrf?{'X-CSRF-Token':csrf}:{})},...(data?{body:JSON.stringify(data)}:{})});
      if(response.status===401){csrf=null;account=null;reset();fieldset.disabled=true;el('harvest-export').disabled=true;el('harvest-rows').replaceChildren();el('harvest-charts').textContent='กรุณาเข้าสู่ระบบ';el('harvest-baselines').textContent='กรุณาเข้าสู่ระบบ';throw Error('กรุณาเข้าสู่ระบบบันทึกสวน แล้วกดโหลดประวัติใหม่');}
      if(!response.headers.get('content-type')?.includes('application/json'))throw Error('เซิร์ฟเวอร์ไม่ตอบข้อมูล JSON (HTTP '+response.status+')');
      const value=await response.json();if(!response.ok||value.error)throw Error(value.error||'HTTP '+response.status);return value;
    }
    function reset(){editing=null;form.reset();form.elements.harvest_year.value=String(yearNow);el('harvest-save').textContent='บันทึกถาวรในบัญชีฉัน';}
    function show(records,baselines){
      const charts=el('harvest-charts');charts.replaceChildren();
      for(const group of historyGroups(records)){
        const card=doc.createElement('article'),heading=doc.createElement('strong'),svg=doc.createElementNS('http://www.w3.org/2000/svg','svg');
        card.className='harvest-chart';heading.textContent=group.orchard+' / '+group.season+' · กก./ไร่';svg.setAttribute('viewBox','0 0 500 145');svg.setAttribute('role','img');svg.setAttribute('aria-label','ประวัติผลผลิตต่อไร่ของสวนที่บันทึก');
        const max=Math.max(...group.points.map(p=>p.value),1);let lastYear=null,path='';
        group.points.forEach((p,i)=>{const x=45+i*410/Math.max(group.points.length-1,1),y=110-90*p.value/max;
          path+=(lastYear===p.year-1?'L':'M')+x+','+y+' ';lastYear=p.year;
          const dot=doc.createElementNS('http://www.w3.org/2000/svg','circle');dot.setAttribute('cx',x);dot.setAttribute('cy',y);dot.setAttribute('r','4');const title=doc.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=(p.year+543)+' · '+fmt(p.value)+' กก./ไร่';dot.append(title);svg.append(dot);
          const text=doc.createElementNS('http://www.w3.org/2000/svg','text');text.setAttribute('x',x);text.setAttribute('y','132');text.setAttribute('text-anchor','middle');text.textContent=String(p.year+543);svg.append(text);
        });
        const line=doc.createElementNS('http://www.w3.org/2000/svg','path');line.setAttribute('d',path);line.setAttribute('fill','none');line.setAttribute('stroke','#16835a');line.setAttribute('stroke-width','2');svg.prepend(line);card.append(heading,svg);charts.append(card);
      }
      if(!charts.childNodes.length)charts.textContent='ยังไม่มีผลเก็บเกี่ยวจริงที่ปิดฤดูและมีพื้นที่ให้ผลครบ';
      const body=el('harvest-rows');body.replaceChildren();
      for(const r of records){
        const tr=doc.createElement('tr');
        for(const text of [r.orchard_code+' / '+r.season_key,(r.harvest_year+543)+' ('+r.harvest_year+')',r.cultivar||'ยังไม่ระบุ',fmt(r.bearing_area_rai),fmt(r.harvested_kg),fmt(r.yield_kg_per_rai),(r.harvest_start||'—')+' ถึง '+(r.harvest_end||'—'),r.source_type+' · '+(r.status==='complete'?'ปิดฤดู':'ร่าง')+' · '+r.source_reference]){
          const td=doc.createElement('td');td.textContent=text;tr.append(td);
        }
        const td=doc.createElement('td'),button=doc.createElement('button');button.type='button';button.textContent='แก้ไขรุ่น '+r.version;
        button.onclick=()=>{if(busy)return;editing=r;for(const [name,value] of Object.entries(r)){const field=form.elements.namedItem(name);if(!field)continue;if(field.type==='checkbox')field.checked=value===true;else field.value=value??'';}el('harvest-save').textContent='บันทึกการแก้ไขรุ่น '+r.version;form.scrollIntoView({block:'center',behavior:'auto'});form.elements.orchard_code.focus();};
        td.append(button);tr.append(td);body.append(tr);
      }
      if(!records.length){const tr=doc.createElement('tr'),td=doc.createElement('td');td.colSpan=9;td.textContent='ยังไม่มีประวัติของบัญชีนี้ เริ่มบันทึกโดยไม่ต้องเลือกหมุด GAP';tr.append(td);body.append(tr);}
      const bases=el('harvest-baselines');bases.replaceChildren();
      for(const b of baselines){const box=doc.createElement('article');box.className='report-stat';const label=doc.createElement('span'),value=doc.createElement('strong'),note=doc.createElement('p');label.textContent=b.orchard_code+' / '+b.season_key+' · ค่าฐานสำหรับปี '+(b.target_year+543);value.textContent=fmt(b.kg_per_rai)+' กก./ไร่';note.textContent='อ้างผลจริงที่บันทึกปี '+(b.source_harvest_year+543)+' รุ่น '+b.source_version+' · Baseline ไม่ใช่ AI Forecast';box.append(label,value,note);bases.append(box);}
      if(!baselines.length)bases.textContent='ยังไม่มีรายการปิดฤดูครบถ้วน จึงยังไม่คำนวณค่าฐาน';
    }
    async function load(){
      const request=++loading;status('กำลังตรวจสิทธิ์และโหลดจากฐานข้อมูล…');fieldset.disabled=true;el('harvest-export').disabled=true;
      try{const session=await api('/api/orchard-session');if(request!==loading)return;if(account!==session.account)reset();account=session.account;csrf=session.csrf;const data=await api('/api/orchard-harvest');if(request!==loading)return;show(data.records,data.baselines);fieldset.disabled=false;el('harvest-export').disabled=false;status('บัญชี '+session.account+' · อ่านประวัติจาก Supabase '+data.records.length+' รายการ · ไม่ใช่ข้อมูล GAP และไม่ฝึกโมเดลอัตโนมัติ');return true;}
      catch(error){if(request===loading){csrf=null;fieldset.disabled=true;el('harvest-rows').replaceChildren();el('harvest-charts').textContent='ยังอ่านข้อมูลไม่ได้';el('harvest-baselines').textContent='ยังอ่านข้อมูลไม่ได้';status(error.message);}}
    }
    form.addEventListener('submit',async event=>{
      event.preventDefault();if(!csrf||busy)return;busy=true;el('harvest-save').disabled=true;
      try{const values=Object.fromEntries(new FormData(form));const data=payload(values,yearNow);if(editing)data.expected_version=editing.version;
        await api('/api/orchard-harvest'+(editing?'/'+encodeURIComponent(editing.id):''),editing?'PATCH':'POST',data);reset();if(await load())status('บันทึกในฐานข้อมูลแล้ว · เก็บรุ่นก่อนแก้ไข · ไม่ได้ฝึกโมเดล');}
      catch(error){status(error.message);}finally{busy=false;el('harvest-save').disabled=false;}
    });
    el('harvest-cancel').onclick=()=>{if(!busy)reset();};el('harvest-reload').onclick=()=>{if(!busy)load();};
    el('harvest-export').onclick=async()=>{try{const data=await api('/api/orchard-harvest/export');const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=doc.createElement('a');a.href=url;a.download='my_orchard_harvest_private.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('ดาวน์โหลดข้อมูลเฉพาะบัญชีแล้ว โปรดเก็บเป็นส่วนตัว; ยังไม่รับรองพร้อมฝึก ML');}catch(error){status(error.message);}};
    api('/api/province-forecast-readiness').then(data=>{el('harvest-forecast-readiness').textContent=data.message+' · ผลผลิตจังหวัดไม่ใช่ผลผลิตสวน';}).catch(error=>{el('harvest-forecast-readiness').textContent='ยังตรวจความพร้อมโมเดลไม่ได้ จึงไม่แสดง Forecast ปีหน้า: '+error.message;});
    load();
  }
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})(typeof window!=='undefined'?window:globalThis);
