/* Physical calculations are scenarios, not fitted durian physiology or yield models. */
const OrchardPhysics = (() => {
  function finite(value, name, min, max) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max) throw Error('ตรวจค่า '+name);
    return value;
  }
  const es = t => 0.6108*Math.exp(17.27*t/(t+237.3));
  function atmosphere({tmin,tmax,rh,u2,rn,pressure}) {
    finite(tmin,'อุณหภูมิต่ำสุด',-50,60);finite(tmax,'อุณหภูมิสูงสุด',tmin,60);
    finite(rh,'RH',0,100);finite(u2,'ลมที่ 2 เมตร',0,60);
    finite(rn,'รังสีสุทธิ',-20,40);finite(pressure,'ความดันสถานี',50,110);
    const t=(tmin+tmax)/2, saturation=(es(tmin)+es(tmax))/2;
    // FAO56 Eq.19 RHmean approximation; not the preferred RHmin/RHmax method.
    const vpd=saturation*(1-rh/100), delta=4098*es(t)/(t+237.3)**2, gamma=.000665*pressure;
    const et0=(.408*delta*rn+gamma*900/(t+273)*u2*vpd)/(delta+gamma*(1+.34*u2));
    return {vpd_kpa:vpd,et0_mm_day:Math.max(0,et0)}; // G≈0 for daily time steps, FAO56.
  }
  function waterBalance({et0,kc,fc,wp,root,p,depletion,rain,irrigation,days}) {
    finite(et0,'ET0',0,30);finite(kc,'Kc',0,3);finite(wp,'จุดเหี่ยว',0,1);
    finite(fc,'ความจุสนาม',0,1);if(fc<=wp)throw Error('ความจุสนามต้องมากกว่าจุดเหี่ยว');
    finite(root,'ความลึกราก',.01,5);finite(p,'สัดส่วน RAW',.01,.99);
    finite(rain,'ฝนที่ซึมถึงราก',0,500);finite(irrigation,'น้ำที่ซึมถึงราก',0,500);
    finite(days,'จำนวนวัน',1,31);if(!Number.isInteger(days))throw Error('จำนวนวันต้องเป็นจำนวนเต็ม');
    const taw=1000*(fc-wp)*root,raw=p*taw;finite(depletion,'น้ำขาดเริ่มต้น',0,taw);
    const rows=[];
    for(let day=1;day<=days;day++){
      // Scenario: water arrives before ET; runoff already excluded, no capillary rise.
      const available=Math.max(0,depletion-rain-irrigation), drainage=Math.max(0,rain+irrigation-depletion);
      const ks=available<=raw?1:Math.max(0,(taw-available)/(taw-raw));
      const potential=et0*kc,actual=Math.min(ks*potential,taw-available);
      depletion=Math.min(taw,available+actual);
      rows.push({day,ks,etc_potential_mm:potential,etc_adjusted_mm:actual,depletion_mm:depletion,deep_drainage_mm:drainage});
    }
    return {taw_mm:taw,raw_mm:raw,rows};
  }
  function floweringRange(year,month,minDays,maxDays) {
    finite(year,'ปี ค.ศ.',1900,2200);finite(month,'เดือน',1,12);
    finite(minDays,'อายุผลต่ำสุด',1,365);finite(maxDays,'อายุผลสูงสุด',minDays,365);
    if(![year,month,minDays,maxDays].every(Number.isInteger))throw Error('ปี เดือน และอายุผลต้องเป็นจำนวนเต็ม');
    const first=new Date(Date.UTC(year,month-1,1)),last=new Date(Date.UTC(year,month,0));
    first.setUTCDate(first.getUTCDate()-maxDays);last.setUTCDate(last.getUTCDate()-minDays);
    return {start:first.toISOString().slice(0,10),end:last.toISOString().slice(0,10)};
  }
  return {atmosphere,waterBalance,floweringRange};
})();
if(typeof module!=='undefined')module.exports=OrchardPhysics;

if(typeof document!=='undefined'){
  function physicsNumber(id){const value=$(id).value;if(!value.trim())throw Error('กรอก '+$(id).labels[0].textContent);return Number(value);}
  let physicsWeatherContext=null;
  const physicsContextBefore=context;
  context=()=>{physicsContextBefore();$('phys-area').textContent=A?'พื้นที่อ้างอิง A: '+areaName(A)+' • แบบจำลองด้านล่างใช้ค่าที่กรอก ไม่ใช่ผลตรวจต้น':'ยังไม่เลือกพื้นที่';
    if(physicsWeatherContext){$('phys-provenance').textContent='พื้นที่หรือช่วงวันที่เปลี่ยนแล้ว ค่าที่คัดลอกไว้เป็นสถานการณ์เดิม กดคัดลอกใหม่หรือกรอกเอง';physicsWeatherContext=null;}
    renderHarvestBackdating();};
  function renderHarvestBackdating(){
    if(!A)return;
    const year=Number($('end').value.slice(0,4));
    const harvest=DATA.harvest.filter(r=>r.province_code===A.code&&r.year_ce===year);
    const total=harvest.reduce((sum,r)=>sum+r.tonnes,0);
    try{const lo=physicsNumber('phys-age-min'),hi=physicsNumber('phys-age-max');
      $('phys-harvest').innerHTML=harvest.length?table(['เดือนเก็บเกี่ยว','สัดส่วนตันในปี %','ช่วงดอกบานที่เป็นไปได้'],harvest.filter(r=>r.tonnes>0).map(r=>{const range=OrchardPhysics.floweringRange(year,r.month_number,lo,hi);return [r.month_number+'/'+(year+543),fmt(r.tonnes/total*100),range.start+' ถึง '+range.end];})):'ไม่มีผลผลิตรายเดือนปีนี้ ไม่ยกปีอื่นมาแทน';
    }catch(e){$('phys-harvest').textContent=e.message;}
  }
  $('phys-backdate').onclick=renderHarvestBackdating;
  $('phys-copy-weather').onclick=()=>{
    if(!weatherExportState||!chartRowsA.length){$('phys-provenance').textContent='เลือกพื้นที่/ช่วงวันที่ แล้วโหลดอากาศ A ก่อน';return;}
    const fields={'phys-tmin':'T2M_MIN','phys-tmax':'T2M_MAX','phys-rh':'RH2M','phys-u2':'WS2M'};
    for(const [id,key] of Object.entries(fields)){
      const values=chartRowsA.map(r=>r[key]).filter(v=>typeof v==='number'&&Number.isFinite(v));
      $(id).value=values.length===chartRowsA.length?(values.reduce((a,b)=>a+b,0)/values.length).toFixed(3):'';
    }
    // Never treat shortwave as net radiation, or sea-level pressure as station pressure.
    $('phys-rn').value='';$('phys-pressure').value='';
    physicsWeatherContext={...weatherExportState.a};
    $('phys-provenance').textContent=`คัดลอกค่าเฉลี่ย A จาก ${weatherExportState.resultA.source} ${weatherExportState.start} ถึง ${weatherExportState.end}; ถ้าหลายวันคือวันตัวแทน ไม่ใช่ผลรวม ET0 รายวัน กรอกรังสีสุทธิและความดันสถานีเอง`;
  };
  $('phys-atmosphere').onclick=()=>{try{
    const input={tmin:physicsNumber('phys-tmin'),tmax:physicsNumber('phys-tmax'),rh:physicsNumber('phys-rh'),u2:physicsNumber('phys-u2'),rn:physicsNumber('phys-rn'),pressure:physicsNumber('phys-pressure')};
    const result=OrchardPhysics.atmosphere(input);$('phys-et0').value=result.et0_mm_day.toFixed(4);
    $('phys-atmosphere-result').textContent=`VPD ≈ ${fmt(result.vpd_kpa,3)} kPa · ET0 ≈ ${fmt(result.et0_mm_day,3)} มม./วัน — หญ้าอ้างอิง ไม่ใช่น้ำทุเรียนหรือหลักฐานปากใบปิด`;
  }catch(e){$('phys-atmosphere-result').textContent=e.message;$('phys-et0').value='';}};
  $('phys-water').onclick=()=>{try{
    const input=Object.fromEntries(['et0','kc','fc','wp','root','p','depletion','rain','irrigation','days'].map(k=>[k,physicsNumber('phys-'+k)]));
    const result=OrchardPhysics.waterBalance(input);
    $('phys-water-result').innerHTML=`<p>ระยะที่ผู้ใช้ระบุ: ${esc($('phys-stage').value)} · TAW ${fmt(result.taw_mm)} มม. · RAW ${fmt(result.raw_mm)} มม.</p>`+table(['วัน','Ks','ETc ศักยภาพ มม.','ETc ปรับ มม.','น้ำขาดปลายวัน มม.'],result.rows.map(r=>[r.day,fmt(r.ks,3),fmt(r.etc_potential_mm,2),fmt(r.etc_adjusted_mm,2),fmt(r.depletion_mm,2)]))+'<p>Ks ลดลง = แบบจำลองลดการใช้น้ำ ไม่ใช่เปอร์เซ็นต์ผลผลิตลด ไม่มีการอนุมานดิน/ราก/Kc จากชื่อชุดดิน</p>';
  }catch(e){$('phys-water-result').textContent=e.message;}};
}
