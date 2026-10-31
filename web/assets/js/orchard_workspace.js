/* Presentation only: retain the existing map, data, tabs, APIs and exports. */
(function(root){
  'use strict';
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const paths={
    home:'M3 10 12 3l9 7v11h-6v-7H9v7H3Z',
    leaf:'M20 3C9 2 3 8 5 15c2 7 14 5 15-12ZM5 21 16 9',
    map:'m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Zm6-2v16m6-14v16',
    weather:'M6 17a4 4 0 0 1 0-8 6 6 0 0 1 11-1 4.5 4.5 0 0 1 1 9ZM12 2v2M3 5l2 2',
    chart:'M4 20V10h3v10Zm7 0V4h3v16Zm7 0v-7h3v7Z',
    calendar:'M4 5h16v16H4ZM8 2v6m8-6v6M4 10h16',
    data:'M20 6c0 2-16 2-16 0s16-2 16 0ZM4 6v12c0 3 16 3 16 0V6M4 12c0 3 16 3 16 0',
    search:'M20 20l-5-5M17 10A7 7 0 1 1 3 10a7 7 0 0 1 14 0Z',
    soil:'m3 8 9-5 9 5-9 5ZM3 12l9 5 9-5M3 16l9 5 9-5',
    info:'M12 11v6m0-11v1M22 12A10 10 0 1 1 2 12a10 10 0 0 1 20 0Z',
    menu:'M3 6h18M3 12h18M3 18h18',
    arrow:'M5 12h14m-6-6 6 6-6 6',
    pin:'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z'
  };
  const icon=name=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.info}"/></svg>`;
  function number(value){return value===null||value===undefined||String(value).trim()===''?null:Number.isFinite(Number(value))?Number(value):null;}
  function gardenRecord(values,selectionId,yearNow){
    if(!selectionId)throw Error('เลือกหมุด GAP ก่อนบันทึก');
    const record={selection_id:selectionId,source:'user_entered_unverified'};
    for(const key of ['bearing_area_rai','bearing_trees','last_harvest_kg']){
      record[key]=number(values[key]);
      if(values[key]!==''&&values[key]!==null&&values[key]!==undefined&&(record[key]===null||record[key]<0))throw Error('ตรวจค่าตัวเลขให้เป็นศูนย์หรือมากกว่า');
    }
    if(record.bearing_area_rai===0)throw Error('พื้นที่ให้ผลต้องมากกว่า 0 หรือเว้นว่างหากยังไม่ทราบ');
    if(record.bearing_trees!==null&&!Number.isInteger(record.bearing_trees))throw Error('จำนวนต้นต้องเป็นจำนวนเต็ม');
    record.harvest_year=number(values.harvest_year);
    if(record.harvest_year!==null&&(!Number.isInteger(record.harvest_year)||record.harvest_year<1981||record.harvest_year>yearNow))throw Error('เลือกปีที่เก็บเกี่ยวแล้ว ไม่ใช้ปีอนาคต');
    if(record.last_harvest_kg!==null&&record.harvest_year===null)throw Error('ระบุปีของผลผลิตที่กรอกด้วย');
    record.cultivar=String(values.cultivar||'');record.stage=String(values.stage||'');record.note=String(values.note||'').slice(0,2000);
    if(Object.entries(record).filter(([k])=>!['selection_id','source'].includes(k)).every(([,v])=>v===null||v===''))throw Error('กรอกข้อมูลอย่างน้อยหนึ่งรายการก่อนบันทึก');
    return record;
  }
  root.OrchardWorkspaceHelpers=Object.freeze({number,gardenRecord});
  if(typeof document==='undefined')return;
  function init(){
    const $=id=>document.getElementById(id),tabs=$('workspace-tabs')||document.querySelector('aside');
    if(!tabs||$('advisor-sidebar'))return;
    document.body.classList.add('advisor-ui');
    const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
    const button=(text,handler,kind='')=>{const e=make('button','advisor-button '+kind,text);e.type='button';e.onclick=handler;return e;};
    const heading=(text,name)=>`<h3>${icon(name)}<span>${escape(text)}</span></h3>`;
    const card=(title,name,cls='')=>{const e=make('section','advisor-card '+cls);e.innerHTML=heading(title,name);return e;};
    const go=id=>{showWorkspaceView(id,false);window.scrollTo({top:0,behavior:'auto'});};
    const nav=document.querySelector('.quick-nav'),top=document.querySelector('.workspace-top'),header=document.querySelector('.orchard-header');
    const sidebar=make('div','advisor-sidebar');sidebar.id='advisor-sidebar';
    const brand=make('div','advisor-sidebar-brand');brand.append(document.querySelector('.orchard-mark').cloneNode(true),make('span',null,'Durian\nOrchard'));
    sidebar.append(brand,nav,$('area-strip'));
    const sidebarFoot=make('div','advisor-sidebar-foot');sidebarFoot.append(document.querySelector('.usage-guide'),make('p',null,'ข้อมูลวิจัยภายในโครงการ'));sidebar.append(sidebarFoot);tabs.prepend(sidebar);
    const menu=[['current-section','สวนของฉัน','leaf'],['soil-analysis','แผนที่ / GAP','map'],['weather-section','สภาพอากาศ','weather'],['yield-section','ผลผลิต','chart'],['report-section','ฤดูกาล','calendar']];
    for(const [id,label,name] of menu){const a=nav.querySelector(`a[href="#${id}"]`);if(a){a.innerHTML=icon(name)+`<span>${label}</span>`;a.title=label;}}
    const mobileMenu=button('',()=>{const open=document.body.classList.toggle('advisor-menu-open');mobileMenu.setAttribute('aria-expanded',String(open));},'advisor-mobile-menu');
    mobileMenu.innerHTML=icon('menu');mobileMenu.setAttribute('aria-label','เปิดหรือปิดเมนู');mobileMenu.setAttribute('aria-expanded','false');mobileMenu.setAttribute('aria-controls',sidebar.id);
    header.querySelector('h1').textContent='ระบบข้อมูลทุเรียน 5 จังหวัด';
    header.querySelector('.header-description').textContent='ข้อมูลพื้นที่ อากาศ และผลผลิต เพื่อการศึกษาและการจัดการสวน';
    top.prepend(mobileMenu);
    const topActions=make('div','advisor-top-actions');
    const searchButton=button('',()=>{go('soil-analysis');document.querySelector('.gap-search-field input').focus();});searchButton.innerHTML=icon('search')+'<span>ค้นหาหมุด GAP</span>';
    const snapshot=make('div','advisor-snapshot');snapshot.innerHTML='<small>ทะเบียน GAP ณ Snapshot</small><strong>กำลังอ่านแหล่งข้อมูล</strong>';
    topActions.append(searchButton,snapshot);top.append(topActions);
    const navScrim=button('',()=>{document.body.classList.remove('advisor-menu-open');mobileMenu.setAttribute('aria-expanded','false');},'advisor-menu-scrim');navScrim.setAttribute('aria-label','ปิดเมนู');sidebar.after(navScrim);
    nav.addEventListener('click',()=>{document.body.classList.remove('advisor-menu-open');mobileMenu.setAttribute('aria-expanded','false');});
    document.addEventListener('keydown',event=>{if(event.key==='Escape'){document.body.classList.remove('advisor-menu-open');mobileMenu.setAttribute('aria-expanded','false');}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();searchButton.click();}});
    let manifest=null;
    fetch('gap_orchards/manifest.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(data=>{manifest=data;snapshot.querySelector('strong').textContent=data.snapshot_date||'ไม่ระบุวันที่';render();}).catch(()=>{snapshot.querySelector('strong').textContent='ยังอ่านวันที่ไม่ได้';});

    // Move existing controls, not copies: all original filters and actions remain wired.
    const atlas=$('soil-analysis'),stage=document.querySelector('.atlas-map-stage'),right=document.querySelector('.atlas-side-panel');
    atlas.querySelector('.atlas-eyebrow').remove();$('soil-analysis-title').textContent='แผนที่สวนและทะเบียน GAP';
    atlas.querySelector('.atlas-subtitle').textContent='เลือกหมุดเป็นพื้นที่ A หรือ B เพื่อดูดิน อากาศ และข้อมูลอ้างอิงที่ตรงระดับพื้นที่';
    const subnav=make('nav','advisor-subnav');subnav.setAttribute('aria-label','ข้อมูลพื้นที่ที่เลือก');
    atlas.querySelector('.atlas-topbar').after(subnav);
    const filterbar=make('div','advisor-map-filters'),gap=$('gap-orchard-controls');
    filterbar.append(gap.querySelector('.gap-search-field'),gap.querySelector('.gap-filters'),gap.querySelector('.atlas-extra-filters'),gap.querySelector('.gap-visibility'));
    const existingRetry=gap.querySelector(':scope > button');
    filterbar.append(gap.querySelector('.gap-status'));if(existingRetry)filterbar.append(existingRetry);
    subnav.after(filterbar);
    const registry=card('ข้อมูลพื้นที่ที่เลือก','pin','advisor-registry');registry.id='advisor-registry';
    const registryBody=make('div','advisor-registry-body');registry.append(registryBody);
    const originalRegistry=make('details','advisor-original-registry');originalRegistry.append(make('summary',null,'รายละเอียดทะเบียน แหล่งอ้างอิง และรายการหมุด'),gap);registry.append(originalRegistry);
    gap.querySelector('.gap-list-details').addEventListener('toggle',()=>{if(gap.querySelector('.gap-list-details').open)originalRegistry.open=true;});
    right.prepend(registry);
    const garden=card('บันทึกข้อมูลประกอบสวน','leaf','advisor-garden');garden.id='advisor-garden';
    garden.innerHTML+=`<p class="advisor-muted">ร่างประกอบหมุด เก็บเฉพาะเบราว์เซอร์นี้ ไม่ใช่ประวัติผลผลิตถาวรหรือหลักฐานยืนยันจากทะเบียน หากต้องการบันทึกผลจริงรายฤดูในฐานข้อมูล ให้ใช้ “ประวัติผลผลิตจริง” ในแท็บสวนของฉัน</p>
      <form id="advisor-garden-form"><fieldset disabled><div class="advisor-form-grid">
      <label>พื้นที่ให้ผลที่บันทึก (ไร่)<input name="bearing_area_rai" type="number" min="0.01" step="any" placeholder="ยังไม่ทราบให้เว้นว่าง"></label>
      <label>จำนวนต้นให้ผล (ต้น)<input name="bearing_trees" type="number" min="0" step="1" placeholder="เช่น 120"></label>
      <label>พันธุ์หลัก<select name="cultivar"><option value="">ยังไม่ระบุ</option>${['หมอนทอง','ชะนี','กระดุม','ก้านยาว','หลงลับแล','หลินลับแล','หลายพันธุ์','อื่น ๆ'].map(v=>`<option>${v}</option>`).join('')}</select></label>
      <label>ผลผลิตที่เก็บเกี่ยวแล้ว (กก.)<input name="last_harvest_kg" type="number" min="0" step="any" placeholder="น้ำหนักจริงที่คุณบันทึก"></label>
      <label>ปีของผลผลิตที่กรอก<select name="harvest_year"><option value="">เลือกปีที่เก็บเกี่ยว</option></select></label>
      <label>ระยะที่สังเกตจริง<select name="stage"><option value="">ยังไม่ทราบ</option>${['ทำใบ / ฟื้นต้น','เตรียมดอก','ดอกบาน','ติดผล','พัฒนาผล','เก็บเกี่ยว'].map(v=>`<option>${v}</option>`).join('')}</select></label>
      </div><details><summary>หมายเหตุเพิ่มเติม</summary><label>การจัดการหรือสิ่งที่พบ<textarea name="note" maxlength="2000" placeholder="ไม่ต้องใส่ชื่อเจ้าของ เบอร์โทร หรือข้อมูลส่วนบุคคล"></textarea></label></details>
      <button type="submit" class="advisor-button primary">บันทึกในเบราว์เซอร์นี้</button></fieldset></form><p id="advisor-garden-status" class="advisor-muted" role="status">เลือกหมุด GAP ก่อนกรอกข้อมูลสวน</p>`;
    right.insertBefore(garden,$('soil-picker'));
    const form=$('advisor-garden-form'),yearNow=Number(new Intl.DateTimeFormat('en',{year:'numeric',timeZone:'Asia/Bangkok'}).format(new Date()));
    for(let y=yearNow;y>=2006;y--)form.elements.harvest_year.add(new Option(String(y+543),String(y)));
    const readiness=card('สถานะการประเมินผลผลิตสวน','chart','advisor-readiness');readiness.id='advisor-readiness';
    readiness.innerHTML+='<div class="advisor-not-ready"><strong>ยังไม่มีคำพยากรณ์ผลผลิตรายสวน</strong><p>ต้องมีผลผลิตจริงของสวนหลายฤดู และโมเดลที่ผ่านการทดสอบรายสวนก่อน</p></div><p class="advisor-callout">ผลผลิตจังหวัดและปริมาณในทะเบียน GAP ไม่ใช่ผลผลิตจริงของสวนที่เลือก การกรอกแบบฟอร์มยังไม่ทำให้โมเดลจังหวัดกลายเป็นโมเดลสวน</p>';
    right.insertBefore(readiness,$('soil-picker'));
    const localKey='durian.orchard.reference-notes.v1';let formSelection=null;const drafts=new Map();
    const values=()=>Object.fromEntries(new FormData(form));
    function records(){const v=JSON.parse(localStorage.getItem(localKey)||'[]');if(!Array.isArray(v))throw Error('รูปแบบประวัติเดิมไม่ถูกต้อง จึงไม่เขียนทับ');return v;}
    form.addEventListener('input',()=>{if(formSelection)drafts.set(formSelection,values());});
    form.addEventListener('submit',event=>{
      event.preventDefault();const point=activeArea==='B'?B:A;
      if(!point||point.point_kind!=='gap_registry'||point.gap_id!==formSelection){$('advisor-garden-status').textContent='พื้นที่เปลี่ยนแล้ว กรุณาตรวจหมุดที่เลือกก่อนบันทึก';return;}
      try{const record=gardenRecord(values(),formSelection,yearNow);record.recorded_at=new Date().toISOString();localStorage.setItem(localKey,JSON.stringify([...records(),record]));$('advisor-garden-status').textContent='บันทึกแล้วในเบราว์เซอร์นี้ · ข้อมูลกรอกเอง ยังไม่ใช่ผลผลิตที่ตรวจยืนยัน และไม่ได้ส่งไปเซิร์ฟเวอร์';}
      catch(error){$('advisor-garden-status').textContent=error.message;}
    });

    const under=make('div','advisor-map-cards');stage.after(under);
    const weather=card('อากาศ ณ พื้นที่ A','weather','advisor-weather-preview');
    const weatherBody=make('div');weather.append(weatherBody,button('ดูอากาศและกราฟ A/B',()=>go('weather-section')));
    const soil=card('หน่วยดิน ณ พื้นที่ที่เลือก','soil');const soilBody=make('div');soil.append(soilBody,button('ดูข้อมูลดินและหลักฐาน',()=>{document.querySelector('.atlas-soil-details').open=true;document.querySelector('.atlas-soil-details').scrollIntoView({block:'start'});}));
    const yieldCard=card('ผลผลิตอ้างอิงจังหวัด','chart');yieldCard.innerHTML+='<p class="advisor-scope-badge">ไม่ใช่ผลผลิตของสวนนี้</p>';
    const yieldYear=make('select');yieldYear.setAttribute('aria-label','ปีผลผลิตอ้างอิงจังหวัด');
    [...new Set(DATA.annual.map(r=>r.year_ce))].sort((a,b)=>b-a).forEach(y=>yieldYear.add(new Option(String(y+543),String(y))));yieldYear.value=String(reportYear);
    yieldYear.onchange=()=>{reportYear=Number(yieldYear.value);selectReportMonth(reportMonth);};
    const yieldBody=make('div');yieldCard.append(yieldYear,yieldBody,button('ดูข้อมูลย้อนหลัง',()=>go('yield-section')));under.append(weather,soil,yieldCard);
    const comparison=card('เปรียบเทียบพื้นที่ A / B','map','advisor-comparison');comparison.id='advisor-comparison';
    const compareActions=make('div','advisor-comparison-actions');compareActions.append(button('สลับ A ↔ B',()=>$('swap-areas').click()),button('ดูพร้อมกัน',()=>$('fit-areas').click()),button('ล้าง B',()=>$('clear-b').click()));
    const compareBody=make('div','advisor-compare-grid');comparison.append(compareActions,compareBody);atlas.append(comparison);
    for(const [label,action] of [
      ['แผนที่',()=>stage.scrollIntoView({block:'start'})],
      ['รายการทะเบียน',()=>{originalRegistry.open=true;gap.querySelector('.gap-list-details').open=true;registry.scrollIntoView({block:'start'});}],
      ['เปรียบเทียบ A/B',()=>comparison.scrollIntoView({block:'start'})],
      ['ข้อมูลดิน',()=>soil.querySelector('button').click()],
      ['สภาพอากาศ',()=>go('weather-section')],
      ['ข้อมูลผลผลิตสวน',()=>readiness.scrollIntoView({block:'start'})]
    ])subnav.append(button(label,action));
    const legend=make('details','advisor-map-legend');legend.open=true;legend.innerHTML='<summary>สัญลักษณ์บนแผนที่</summary><p><span class="advisor-mini-pin"></span>หมุดทะเบียน GAP — ยังไม่ยืนยันภาคสนาม</p><p><span class="advisor-mini-cluster">12</span>กลุ่มหมุดใกล้กัน คลิกเพื่อซูมหรือเลือกรายการ</p><p><b class="advisor-a">A</b> พื้นที่หลัก <b class="advisor-b">B</b> พื้นที่เปรียบเทียบ</p><small>สีและรูปหมุดไม่ใช่ระดับความเสี่ยงโรค</small>';stage.append(legend);
    legend.querySelector('.advisor-mini-cluster').textContent='';
    legend.querySelector('.advisor-mini-cluster').classList.add('advisor-mini-group');
    legend.querySelector('.advisor-mini-cluster').parentElement.lastChild.textContent=' กลุ่มหมุดใกล้กัน คลิกจึงแสดงจำนวนและรายการ';
    const home=$('current-section'),homeIntro=make('div','advisor-home-intro');
    homeIntro.innerHTML='<div><p class="advisor-kicker">SMART ORCHARD · สวนของฉัน</p><h2>ข้อมูลสวนของคุณ</h2><p>ติดตามค่าจากจุดเซนเซอร์และบันทึกสิ่งที่พบในสวน เพื่อประกอบการดูแลอย่างรอบคอบ</p></div>';
    homeIntro.append(button('สำรวจแผนที่และหมุด GAP',()=>go('soil-analysis'),'primary'));home.prepend(homeIntro);
    const overview=make('div','advisor-overview-stats');
    const provinceCards=make('div','advisor-province-cards');
    const provinceOverview=make('details','advisor-province-overview');provinceOverview.innerHTML='<summary>ข้อมูลอ้างอิง 5 จังหวัด</summary>';provinceOverview.append(overview,provinceCards);home.append(provinceOverview);
    const referenceContext=make('section','orchard-reference-context');referenceContext.innerHTML='<p class="orchard-eyebrow">ข้อมูลอ้างอิงจากพื้นที่ A</p><h3>แผนที่ดินและอากาศกริด</h3><div class="orchard-reference-grid"><div id="home-soil-reference"></div><div id="home-weather-reference"></div></div><p class="advisor-muted">ข้อมูลนี้อ้างอิงพื้นที่ A ที่เลือกบนแผนที่ อาจไม่ตรงกับตำแหน่งเซนเซอร์หรือสวนของคุณ</p>';
    const referenceActions=make('div','report-controls');referenceActions.append(button('เลือกพื้นที่และดูแผนที่ดิน',()=>go('soil-analysis')),button('ดูอากาศย้อนหลัง A/B',()=>go('weather-section')));referenceContext.append(referenceActions);
    home.querySelector('.orchard-telemetry').after(referenceContext);
    home.querySelector(':scope > h2')?.classList.add('advisor-existing-title');
    function rowStats(point){return point?DATA.annual.find(r=>r.province_code===point.code&&r.year_ce===Number(yieldYear.value)):null;}
    function render(){
      const point=activeArea==='B'?B:A,reg=point?.gap_registry_data||{},isGap=point?.point_kind==='gap_registry';
      const province=point?DATA.provinces.find(p=>p.province_code===point.code):null;
      const name=province?.province_name||'ยังไม่เลือกพื้นที่';
      const snapshotDate=point?.gap_snapshot_date||manifest?.snapshot_date||'ยังอ่านวันที่ไม่ได้';
      registryBody.innerHTML=isGap?`<div class="advisor-selected-heading"><span class="advisor-area-badge ${activeArea==='B'?'is-b':''}">${activeArea}</span><div><strong>${escape(name)} · ${escape(point.registry_district||point.district||'ไม่ระบุอำเภอ')}</strong><small>รหัสแสดงผล ${escape(point.gap_id)} · ไม่ใช่เลขใบรับรอง</small></div></div><p class="advisor-scope-badge">พิกัดตามทะเบียน ยังไม่ยืนยันภาคสนาม</p><dl class="advisor-definition"><div><dt>ตำบล</dt><dd>${escape(reg.tambon||'ไม่ระบุ')}</dd></div><div><dt>ทะเบียน ณ Snapshot</dt><dd>${escape(snapshotDate)}</dd></div><div><dt>วันออกที่รายงาน</dt><dd>${escape(reg.issued||'ไม่ระบุ')}</dd></div><div><dt>วันสิ้นสุดที่รายงาน</dt><dd>${escape(reg.expired||'ไม่ระบุ')}</dd></div></dl><div class="advisor-registry-stats"><div><span>พื้นที่ปลูกตามทะเบียน</span><strong>${reg.area_rai===null||reg.area_rai===undefined?'ไม่ระบุ':escape(fmt(reg.area_rai,2))+' ไร่'}</strong></div><div><span>จำนวนต้นให้ผล</span><strong>ยังไม่มีข้อมูล</strong></div><div><span>ผลผลิตรายปีของสวน</span><strong>ยังไม่ยืนยัน</strong></div></div><p class="advisor-muted">พื้นที่ปลูกไม่ใช่พื้นที่ให้ผล · วันที่ทะเบียนไม่ใช่ปีเก็บเกี่ยว</p>`:
        `<div class="advisor-empty-selection">${icon('pin')}<strong>เลือกหมุด GAP เป็นพื้นที่ ${activeArea}</strong><p>ขณะนี้ ${escape(name)} เป็นข้อมูลอ้างอิง เลือกหมุดทรงปักบนแผนที่หรือเลือกรายการทะเบียนเพื่อดูรายละเอียด</p></div>`;
      const selected=isGap?point.gap_id:null;
      form.querySelector('fieldset').disabled=!selected;
      if(selected!==formSelection){
        formSelection=selected;form.reset();
        try{const saved=drafts.get(selected)||records().filter(r=>r.selection_id===selected).at(-1);if(saved)for(const [k,v] of Object.entries(saved))if(form.elements[k])form.elements[k].value=v??'';
          $('advisor-garden-status').textContent=selected?'ข้อมูลผูกกับรหัสแสดงผลที่เลือก ไม่ยืนยันสิทธิ์เจ้าของสวน และยังไม่ใช้เป็น Label ฝึกโมเดล':'เลือกหมุด GAP ก่อนกรอกข้อมูลสวน';
        }catch(error){$('advisor-garden-status').textContent='อ่านประวัติในเบราว์เซอร์ไม่ได้: '+error.message;}
      }
      const props=point?.soil_properties;
      soilBody.innerHTML=props?`<strong class="advisor-soil-name">${escape(props.soil_name||'ไม่ระบุชื่อ')} (${escape(props.soil_code||point.soil_code)})</strong><dl class="advisor-definition"><div><dt>เนื้อดินบน</dt><dd>${escape(props.topsoil_texture||'ไม่ระบุ')}</dd></div><div><dt>ความอุดมสมบูรณ์</dt><dd>${escape(props.fertility||'ไม่ระบุ')}</dd></div><div><dt>pH ดินบนตามแผนที่</dt><dd>${escape(props.topsoil_ph||'ไม่ระบุ')}</dd></div></dl><p class="advisor-muted">หน่วยแผนที่ดิน LDD 2561 ไม่ใช่ผลตรวจดินทั้งสวน</p>`:'<p class="advisor-empty">ยังไม่ได้หน่วยดินที่จับคู่ตำแหน่งได้อย่างไม่กำกวม เลือกหมุดหรือใช้ตัวเลือกหน่วยดินเดิมด้านล่าง</p>';
      const y=Number(yieldYear.value),annual=rowStats(A);
      yieldBody.innerHTML=`<h4>${escape(DATA.provinces.find(p=>p.province_code===A?.code)?.province_name||'ยังไม่เลือก A')}</h4><dl class="advisor-definition"><div><dt>ผลผลิตรวม</dt><dd>${annual?fmt(annual.production_tonnes,0)+' ตัน':'—'}</dd></div><div><dt>พื้นที่ให้ผล</dt><dd>${annual?fmt(annual.bearing_rai,0)+' ไร่':'—'}</dd></div><div><dt>ผลผลิตต่อไร่</dt><dd>${annual?fmt(annual.yield_kg_per_rai_calculated,1)+' กก./ไร่':'—'}</dd></div></dl><p class="advisor-muted">OAE ระดับจังหวัด ปี ${y+543} · สถานะยอดปิดยังไม่ยืนยัน</p>`;
      const weatherResult=weatherExportState?.resultA,exactWeather=weatherExportState&&samePoint(weatherExportState.a,A)&&weatherExportState.start===$('start').value&&weatherExportState.end===$('end').value;
      const sample=exactWeather?weatherResult?.rows:null;
      if(sample?.length){
        const valid=k=>sample.map(r=>r[k]).filter(Number.isFinite),temps=valid('T2M'),rain=valid('PRECTOTCORR'),rh=valid('RH2M');
        weatherBody.innerHTML=`<div class="advisor-small-stats"><div><span>อุณหภูมิเฉลี่ย</span><strong>${temps.length?fmt(temps.reduce((a,b)=>a+b,0)/temps.length,1)+' °C':'—'}</strong></div><div><span>ฝนสะสมวันที่มีค่า</span><strong>${rain.length?fmt(rain.reduce((a,b)=>a+b,0),1)+' มม.':'—'}</strong></div><div><span>ความชื้นเฉลี่ย</span><strong>${rh.length?fmt(rh.reduce((a,b)=>a+b,0)/rh.length,1)+'%':'—'}</strong></div></div><p class="advisor-muted">${escape($('start').value)} ถึง ${escape($('end').value)} · ${escape(weatherResult.source)} · ${rain.length}/${sample.length} วันมีค่าฝน · NASA POWER เป็นกริด</p>`;
        if($('chart').childNodes.length){const clone=$('chart').cloneNode(true);clone.removeAttribute('id');weatherBody.append(clone);}
        if(weatherResult.basis==='province_proxy')weatherBody.append(make('p','advisor-callout','ใช้จุดอ้างอิงจังหวัดแทนพิกัด A — ไม่ใช่อากาศของหมุดสวน'));
      }else weatherBody.innerHTML='<div class="advisor-weather-empty">'+icon('weather')+'<strong>ยังไม่ได้โหลดอากาศพิกัด A</strong><p>เลือกช่วงวันและโหลดจากหน้าอากาศ ระบบจะแสดงแหล่งข้อมูลและวันที่มีค่าจริง</p></div>';
      const refSoil=A?.soil_properties;
      $('home-soil-reference').innerHTML=refSoil?`<strong>หน่วยดินแผนที่ LDD: ${escape(refSoil.soil_name||refSoil.soil_code||'ไม่ระบุ')}</strong><p>แผนที่ปี 2561 · ระดับหน่วยแผนที่ ไม่ใช่ผลตรวจดินหรือการวัดในสวน</p>`:'<strong>หน่วยดินแผนที่ LDD</strong><p>ยังไม่มีหน่วยดินที่จับคู่พื้นที่ A ได้ เลือกพื้นที่บนแผนที่</p>';
      const weatherValues=field=>sample?.map(r=>r[field]).filter(Number.isFinite)||[];
      const weatherMean=field=>{const v=weatherValues(field);return v.length?fmt(v.reduce((a,b)=>a+b,0)/v.length,1):'—';};
      const rainValues=weatherValues('PRECTOTCORR');
      $('home-weather-reference').innerHTML=sample?.length?`<strong>อากาศจาก ${escape(weatherResult.source||'แหล่งข้อมูลอากาศ')}</strong><p>อุณหภูมิเฉลี่ย ${weatherMean('T2M')} °C · ความชื้นเฉลี่ย ${weatherMean('RH2M')}% · ฝนรวมวันที่มีค่า ${rainValues.length?fmt(rainValues.reduce((a,b)=>a+b,0),1):'—'} มม. (${rainValues.length}/${sample.length} วัน)</p><p>พื้นที่ A · ${escape($('start').value)} ถึง ${escape($('end').value)} · ${weatherResult.basis==='province_proxy'?'จุดอ้างอิงจังหวัด':'ข้อมูลกริดที่จุด A'} ไม่ใช่สถานีวัดในสวน</p>`:'<strong>อากาศกริด NASA POWER</strong><p>ยังไม่ได้โหลดช่วงวันที่ของพื้นที่ A · ข้อมูลกริดไม่ใช่ค่าจากเซนเซอร์สวน</p>';
      compareBody.innerHTML=[['A',A],['B',B]].map(([label,p])=>{const a=rowStats(p),n=DATA.provinces.find(v=>v.province_code===p?.code)?.province_name;return `<article class="advisor-compare-area ${label==='B'?'is-b':''}"><span class="advisor-area-badge ${label==='B'?'is-b':''}">${label}</span><div><strong>${escape(n||'ยังไม่เลือกพื้นที่ B')}</strong><p>${p?escape(p.point_kind==='gap_registry'?'หมุด GAP · '+(p.registry_district||p.district||'ไม่ระบุอำเภอ'):'จุดอ้างอิงจังหวัด / หน่วยดิน'):'เลือกพื้นที่ B จากแผนที่เพื่อเปรียบเทียบ'}</p><small>${a?'ผลผลิตอ้างอิงจังหวัด '+fmt(a.yield_kg_per_rai_calculated,1)+' กก./ไร่ · ปี '+(y+543):'ไม่มีข้อมูลอ้างอิงปีที่เลือก'} · ไม่ใช่ผลผลิตสวน</small></div></article>`;}).join('');
      compareActions.firstElementChild.disabled=!B;
      const latest=Math.max(...DATA.annual.map(r=>r.year_ce)),latestRows=DATA.provinces.map(p=>DATA.annual.find(r=>r.province_code===p.province_code&&r.year_ce===latest)),complete=latestRows.every(Boolean);
      const total=complete?latestRows.reduce((sum,r)=>sum+r.production_tonnes,0):null;
      overview.innerHTML=[['จังหวัดในระบบ',String(DATA.provinces.length),'จังหวัดที่มีข้อมูลอ้างอิง','map'],['ผลผลิตรวมที่รายงาน',total===null?'ยังไม่ครบ':fmt(total,0)+' ตัน','ทั้ง 5 จังหวัด ปี '+(latest+543)+' · ไม่ยืนยันยอดปิด','chart'],['หมุด GAP ผ่านเกณฑ์แสดงผล',manifest?fmt(manifest.totals.display_points,0):'กำลังอ่าน','พิกัดทะเบียน ไม่ยืนยันภาคสนาม','pin'],['ข้อมูลผลผลิตล่าสุด','ปี '+(latest+543),'ปีตามระเบียน OAE ไม่ใช่ปีเผยแพร่','data']].map(([label,value,note,name])=>`<article class="advisor-stat">${icon(name)}<div><span>${label}</span><strong>${value}</strong><small>${note}</small></div></article>`).join('');
      provinceCards.innerHTML=DATA.provinces.map(p=>{const r=latestRows.find(v=>v?.province_code===p.province_code);return `<button type="button" class="advisor-province-card" data-advisor-province="${p.province_code}"><strong>${escape(p.province_name)}</strong><span>${r?fmt(r.production_tonnes,0)+' ตัน':'—'}</span><small>${r?fmt(r.yield_kg_per_rai_calculated,1)+' กก./ไร่':'ไม่มีข้อมูลปีนี้'} · ระดับจังหวัด</small><span class="advisor-card-link">ดูบนแผนที่ ${icon('arrow')}</span></button>`;}).join('');
      provinceCards.querySelectorAll('button').forEach(b=>b.onclick=()=>{areaControl('province','A').value=b.dataset.advisorProvince;provinceChange('A');go('soil-analysis');});
    }
    const originalContext=context;context=()=>{originalContext();if(yieldYear.value!==String(reportYear)&&[...yieldYear.options].some(o=>o.value===String(reportYear)))yieldYear.value=String(reportYear);render();};
    const originalLoader=loadWeather;loadWeather=async()=>{await originalLoader();render();};$('load').onclick=loadWeather;
    const originalInvalidator=invalidateWeather;invalidateWeather=message=>{originalInvalidator(message);render();};
    const stripObserver=new MutationObserver(()=>render());stripObserver.observe($('area-strip'),{childList:true,subtree:true});
    document.querySelectorAll('input[name="map-area"]').forEach(input=>input.addEventListener('change',()=>requestAnimationFrame(render)));
    const navObserver=new MutationObserver(()=>{if(document.body.dataset.workspace!=='soil-analysis')return;requestAnimationFrame(()=>mapMotion.invalidate({pan:true}));});navObserver.observe(document.body,{attributes:true,attributeFilter:['data-workspace']});
    document.querySelector('.atlas-meta').textContent='ข้อมูลตามแหล่งอ้างอิง · ไม่ใช่คำพยากรณ์รายสวน';
    render();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})(typeof window!=='undefined'?window:globalThis);
