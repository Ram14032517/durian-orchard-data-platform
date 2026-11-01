const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const {createRequire}=require('node:module');
const path=require('node:path');
const frontRequire=createRequire(path.resolve('web/react/package.json'));
const {buildSync}=frontRequire('esbuild');
const React=frontRequire('react');
const {renderToStaticMarkup}=frontRequire('react-dom/server');
const fixture={provinces:[{province_code:'22',weather_latitude:12,weather_longitude:102,province_name:'จังหวัดทดสอบ'}]};
function load(file,fetch){const compiled=buildSync({entryPoints:[file],bundle:true,write:false,format:'cjs',platform:'node',external:['react'],logLevel:'silent'}).outputFiles[0].text;const module={exports:{}};vm.runInNewContext(compiled,{module,exports:module.exports,require:frontRequire,window:{__ORCHARD_DATA__:fixture},fetch,URLSearchParams,AbortController,Date,Intl,console,setTimeout,clearTimeout,setInterval,clearInterval});return module.exports;}
test('React entry uses bundled React and compiled Tailwind, not a CDN transpiler',()=>{const html=fs.readFileSync('research_data/five_province_history/UNIFIED_MAP.html','utf8');assert.match(html,/orchard-react-root/);assert.match(html,/orchard_app\.js/);assert.match(html,/orchard_app\.css/);assert.doesNotMatch(html,/text\/babel|react\.development|orchard_lumen/);assert.ok(fs.statSync('research_data/five_province_history/orchard_app.css').size>1000);});
test('sensor cards reject invalid/stale data, preserve zero, and JSX escapes external text',()=>{const d=load('web/react/src/data.js');assert.equal(d.num(null),null);assert.equal(d.num(''),null);assert.equal(d.num(0),0);const r={status:'fresh_live',sensor_quality:{soil:'invalid',weather:'valid'},readings:{soil_moisture_percent:0,rain_1h_mm:0}};assert.equal(d.sensorState(r,'soil','soil_moisture_percent'),'invalid');assert.equal(d.sensorState(r,'weather','rain_1h_mm'),'fresh');r.status='stale_live';assert.equal(d.sensorState(r,'weather','rain_1h_mm'),'stale');const ui=load('web/react/src/ui.jsx');const html=renderToStaticMarkup(React.createElement(ui.Metric,{label:'<script>alert(1)</script>',value:0,unit:'%'}));assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);assert.match(html,/>0<\/span>/);});
test('React chart does not connect missing measurements or turn missing into zero',()=>{const ui=load('web/react/src/ui.jsx');const html=renderToStaticMarkup(React.createElement(ui.LineChart,{rows:[{time:'1',x:0},{time:'2',x:null},{time:'3',x:25}],series:[{key:'x',label:'test',color:'#123456'}],unit:'%'}));const d=html.match(/<path d="([^"]+)"/)[1];assert.equal((d.match(/M/g)||[]).length,2);assert.equal((d.match(/L/g)||[]).length,0);assert.equal((html.match(/<circle/g)||[]).length,2);});
test('weather fallback labels province proxy; missing days and duplicates fail closed',async()=>{const response=rows=>({ok:true,status:200,headers:{get:()=> 'application/json'},json:async()=>rows});let rows=[{date:'2024-01-01',T2M:0},{date:'2024-01-02',T2M:null}];const fetch=async url=>String(url).startsWith('/api/')?{ok:false,status:403,headers:{get:()=> 'application/json'},json:async()=>({error:'unavailable'})}:response(rows);const w=load('web/react/src/Weather.jsx',fetch);const p={code:'22',lat:12.5,lon:102.2};const result=await w.weatherAtPoint(p,'2024-01-01','2024-01-02');assert.equal(result.basis,'province_proxy');assert.match(result.warning,/ไม่ใช่อากาศสวน/);assert.equal(result.rows[0].T2M,0);rows=[{date:'2024-01-01'},{date:'2024-01-01'}];await assert.rejects(w.weatherAtPoint(p,'2024-01-01','2024-01-02'),/ไม่ครอบคลุม/);});
test('weather sign-in failure is not silently replaced with public province data',async()=>{let calls=0;const w=load('web/react/src/Weather.jsx',async()=>{calls++;return {ok:false,status:401,headers:{get:()=> 'application/json'},json:async()=>({error:'sign in'})};});await assert.rejects(w.weatherAtPoint({code:'22',lat:12,lon:102},'2024-01-01','2024-01-01'),e=>e.status===401);assert.equal(calls,1);});
test('soil codes use deterministic categorical colors; SC and W remain distinct',()=>{
  const {soilPalette,soilLegend}=load('web/react/src/soil.js');
  const a=soilPalette(['W','Ca','SC','Ac','Ca',' Ac ']),b=soilPalette(['Ac','SC','Ca','W']);
  for(const code of ['Ca','Ac','SC','W'])assert.equal(a(code),b(code));
  assert.equal(a('SC'),'#a4a29a');assert.equal(a('W'),'#398ac2');assert.equal(a('unknown'),'#cbd5e1');
  assert.notEqual(a('Ca'),a('Ac'));assert.equal(a(' Ca '),a('Ca'));
  const legend=soilLegend([{properties:{soil_code:'Ca',soil_name:'source name'}},{properties:{soil_code:'Ca'}},{properties:{soil_code:'W'}},{properties:{}}],a);
  assert.equal(legend.length,2);assert.equal(legend[0].name,'source name');assert.equal(legend[0].count,2);assert.equal(legend[0].color,a('Ca'));
});
test('all five existing soil layers have mapped colors and preserve their source codes',()=>{
  const html=fs.readFileSync('research_data/five_province_history/UNIFIED_MAP.html','utf8');
  const payload=JSON.parse(html.match(/const DATA=(.*?);window\.__ORCHARD_DATA__/s)[1]);
  const codes=new Set(payload.soil_properties.map(p=>p.soil_code));
  const color=load('web/react/src/soil.js').soilPalette([...codes]);
  for(const province of ['22','33','53','84','86']){
    const geo=JSON.parse(fs.readFileSync(`research_data/priority_provinces/soil_layers/${province}.geojson`,'utf8'));
    for(const f of geo.features){assert.ok(codes.has(f.properties.soil_code),`${province}: unmapped code`);assert.notEqual(color(f.properties.soil_code),'#cbd5e1');}
  }
});
test('durian logo and fruit-set stages use an internal SVG; A/B badges cannot intercept GAP clicks',()=>{
  const ui=load('web/react/src/ui.jsx'),svg=renderToStaticMarkup(React.createElement(ui.Icon,{name:'durian'}));
  assert.match(svg,/<svg/);assert.match(svg,/viewBox="0 0 64 64"/);assert.doesNotMatch(svg,/<image|https?:/);
  assert.match(fs.readFileSync('web/react/src/Home.jsx','utf8'),/\['young','ติดผล','durian'\]/);
  assert.match(fs.readFileSync('web/react/src/MapPage.jsx','utf8'),/interactive:false,keyboard:false/);
  const css=fs.readFileSync('research_data/five_province_history/orchard_app.css','utf8');
  assert.match(css,/\.gap-pin-head\{/,'React bundle includes the actual marker shape, not only its empty DOM hit area');
  assert.match(css,/\.gap-group-pin \.gap-pin-head\{/);
});
test('growth timeline highlights only the recorded stage, never the current calendar month',()=>{
  const {OrchardStage}=load('web/react/src/Home.jsx');
  const render=saved=>renderToStaticMarkup(React.createElement(OrchardStage,{observation:{saved,message:'',save(){}}}));
  const empty=render(null);assert.match(empty,/ยังไม่ได้บันทึกระยะการผลิต/);assert.doesNotMatch(empty,/aria-current="step"/);
  const recorded=render({stage:'young',observed_at:'2026-01-01T00:00:00Z'});
  assert.equal((recorded.match(/aria-current="step"/g)||[]).length,1);assert.match(recorded,/<p[^>]*>ติดผล<\/p>/);
  assert.match(recorded,/ยังไม่แยกตามบัญชี/);assert.equal((recorded.match(/<li /g)||[]).length,6);
});
test('care cards preserve invalid/missing status and do not advise on stale rainfall',()=>{
  const {Care}=load('web/react/src/Home.jsx');
  const html=renderToStaticMarkup(React.createElement(Care,{reading:{data:{status:'stale_live',sensor_quality:{soil:'invalid',weather:'valid'},readings:{rain_1h_mm:25}}},observation:{saved:null}}));
  assert.match(html,/ตรวจสอบอุปกรณ์/);assert.match(html,/บันทึกระยะที่เห็นจริง/);assert.doesNotMatch(html,/ติดตามการระบายน้ำ|สวนปกติ|ใส่ปุ๋ย/);
});
test('province estimate has independent current/next-year inputs and does not fetch on page open',()=>{
  let calls=0;const {ProvinceEstimate}=load('web/react/src/Reports.jsx',()=>{calls++;throw Error('no automatic weather request');});
  const html=renderToStaticMarkup(React.createElement(ProvinceEstimate,{initialProvince:'22'}));
  const year=Number(new Date().toLocaleDateString('en-CA',{timeZone:'Asia/Bangkok',year:'numeric'}));
  assert.match(html,new RegExp(`value="${year}"`));assert.match(html,new RegExp(`value="${year+1}"`));
  assert.match(html,/แยกจากปีสถิติด้านบน/);assert.match(html,/ไม่ใช่พยากรณ์รายสวน/);assert.match(html,/เริ่มประเมินจังหวัดที่สนใจ/);assert.equal(calls,0);
});
test('forecast advice uses owner-linked fresh sensors and recent matching orchard stage; never diagnoses disease',()=>{
  const {watchAdvice}=load('web/react/src/OrchardForecast.jsx');
  const now=Date.parse('2026-10-28T12:00:00+07:00');
  const forecast={status:'fresh',orchard_key:'test-orchard',sensor_link_confirmed:true,summaries:[{complete:true,rain_mm:12}]};
  const reading={data:{status:'fresh_live',sensor_quality:{soil:'invalid',weather:'valid'},readings:{soil_moisture_percent:0,outdoor_temperature_c:28}}};
  const observation={saved:{stage:'growth',orchard_key:'test-orchard',observed_at:'2026-10-28T10:00:00+07:00'}};
  let r=watchAdvice(forecast,reading,observation,now);assert.equal(r.items.length,2);assert.equal(r.currentStage,'พัฒนาผล');assert.deepEqual(Array.from(r.sensor),['outdoor_temperature_c']);
  assert.ok(r.items.every(i=>i.source.url.startsWith('https://www.doa.go.th/')));
  assert.match(r.items[0].body,/ไม่สรุปว่ามีโรค/);assert.match(r.items[1].body,/ยังไม่มีหลักฐาน/);
  observation.saved.orchard_key='another';r=watchAdvice(forecast,reading,observation,now);assert.equal(r.currentStage,null);assert.equal(r.items.length,1);
  observation.saved.orchard_key='test-orchard';observation.saved.observed_at='2026-01-01T00:00:00Z';assert.equal(watchAdvice(forecast,reading,observation,now).currentStage,null);
  forecast.status='stale';assert.match(watchAdvice(forecast,reading,observation,now).items[0].title,/รอพยากรณ์/);
  forecast.sensor_link_confirmed=false;assert.equal(watchAdvice(forecast,reading,observation,now).sensor.length,0);
});
test('forecast UI distinguishes forecast, NABC report and orchard diagnosis; empty data remains missing',()=>{
  const {ForecastContent}=load('web/react/src/OrchardForecast.jsx');
  const forecast={status:'cached',hourly:[{time:'2026-10-29T00:00:00+07:00',rain_mm:0,temperature_c:null}],daily:[],summaries:[],quality_flags:['temperature_c'],retrieved_at:'2026-10-28T12:00:00+07:00',spatial_note:'กริด ไม่ใช่เครื่องวัดในสวน'};
  const html=renderToStaticMarkup(React.createElement(ForecastContent,{forecast,reading:{data:null},observation:{saved:null}}));
  for(const text of ['รายงานโรคระดับจังหวัด','ยังไม่มีผลวินิจฉัยโรค','CC BY 4.0','Asia/Bangkok','24 ชั่วโมง','48 ชั่วโมง','ไม่มีข้อมูล','ไม่ใช่ค่าจากเซนเซอร์','ไม่ได้อัปเดตจาก NABC อัตโนมัติ'])assert.ok(html.includes(text),text);
  assert.doesNotMatch(html,/latitude|longitude|เสี่ยงโรค \d+%|พบโรคในสวนแล้ว/);
});
test('forecast charts keep nonnegative scales and humidity within 0 to 100 without changing readings',()=>{
  const {LineChart}=load('web/react/src/ui.jsx');
  for(const value of [0,100]){
    const html=renderToStaticMarkup(React.createElement(LineChart,{rows:[{time:'t',value}],series:[{key:'value',label:'RH',color:'#479990'}],unit:'%',minValue:0,maxValue:100}));
    assert.doesNotMatch(html,/NaN|Infinity/);assert.match(html,new RegExp('t: '+value+' %'));
  }
  const {metrics}=load('web/react/src/data.js');
  assert.ok(!metrics.some(m=>['air_temperature_c','humidity_percent'].includes(m[0])));
  assert.ok(metrics.some(m=>m[0]==='outdoor_temperature_c'));assert.ok(metrics.some(m=>m[0]==='outdoor_humidity_percent'));
});
test('current API cards are explicitly model weather, show accumulation interval and retain genuine zero',()=>{
  const {CurrentWeather}=load('web/react/src/OrchardForecast.jsx');
  const html=renderToStaticMarkup(React.createElement(CurrentWeather,{forecast:{retrieved_at:'2026-10-29T12:01:00+07:00',current:{time:'2026-10-29T12:00:00+07:00',status:'fresh',interval_seconds:900,age_minutes:1,temperature_c:28,humidity_percent:85,rain_mm:0,wind_kmh:2,vpd_kpa:null}}}));
  assert.match(html,/อากาศปัจจุบันจาก API/);assert.match(html,/ไม่ใช่สถานีตรวจวัดหรือเซนเซอร์สวน/);assert.match(html,/ฝนช่วง 15 นาที/);assert.match(html,/>0<\/span>/);assert.match(html,/ไม่มีข้อมูล/);
  const empty=renderToStaticMarkup(React.createElement(CurrentWeather,{forecast:{}}));assert.match(empty,/ยังไม่มีค่าปัจจุบัน/);assert.doesNotMatch(empty,/ข้อมูลล่าสุด|>0<\/span>/);
});
test('estimate display requires a numeric result with the correct model status',()=>{
  const {estimateView}=load('web/react/src/Reports.jsx');
  assert.equal(estimateView({status:'pending_prior_yield',predicted_kg_rai:1000}).ready,false);
  assert.equal(estimateView({status:'retrospective_weather_estimate',predicted_kg_rai:null}).ready,false);
  assert.equal(estimateView({status:'retrospective_weather_estimate',predicted_kg_rai:0}).ready,true);
  assert.equal(estimateView({status:'missing_weather'}).ready,false);
});

test('home starts with an accessible five-tab view and mounts only Today initially',()=>{
  const {HomeTabs}=load('web/react/src/Home.jsx');
  const html=renderToStaticMarkup(React.createElement(HomeTabs,{children:tab=>React.createElement('p',null,'content-'+tab)}));
  assert.equal((html.match(/role="tab"/g)||[]).length,5);
  assert.equal((html.match(/role="tabpanel"/g)||[]).length,1);
  assert.match(html,/aria-selected="true" aria-controls="orchard-panel-today"/);
  assert.doesNotMatch(html,/content-history|content-forecast/);
});

test('care suggestions fail closed for missing, failed and stale sensor/forecast data',()=>{
  const {careSuggestions}=load('web/react/src/OrchardAdvice.jsx');
  for(const reading of [{loading:true},{error:Error('offline')},{data:{status:'stale_live',sensor_quality:{soil:'valid'},readings:{rain_1h_mm:99}}}]){
    const items=careSuggestions(reading,{status:'stale',summaries:[{complete:true,rain_mm:100,expected_hours:24,valid_rain_hours:24}]},{saved:null});
    assert.equal(items[0].id,'sensor');
    assert.ok(!items.find(i=>i.id==='water').title.includes('มีฝนคาดการณ์'));
    assert.match(items.find(i=>i.id==='stage').evidence,/ยังไม่ได้บันทึก/);
  }
});

test('forecast advice only uses complete ready windows and does not turn missing rain into zero',()=>{
  const {careSuggestions}=load('web/react/src/OrchardAdvice.jsx');
  const make=summary=>careSuggestions({}, {status:'cached',summaries:[summary]},{}).find(i=>i.id==='water');
  assert.match(make({complete:true,rain_mm:8,hours:24,expected_hours:24,valid_rain_hours:24}).title,/มีฝนคาดการณ์/);
  assert.doesNotMatch(make({complete:false,rain_mm:8,expected_hours:24,valid_rain_hours:12}).title,/มีฝนคาดการณ์/);
  assert.match(make({complete:false,rain_mm:null,expected_hours:24,valid_rain_hours:0}).evidence,/ยังไม่ครบ/);
});

test('today has at most three actions and advice separates evidence, gaps and sources',()=>{
  const {TodayActions,AdviceCard,careSuggestions}=load('web/react/src/OrchardAdvice.jsx');
  const html=renderToStaticMarkup(React.createElement(TodayActions,{reading:{},forecast:null,observation:{saved:null}}));
  assert.equal((html.match(/<article/g)||[]).length,3);
  const detail=renderToStaticMarkup(React.createElement(AdviceCard,{item:careSuggestions({},null,{})[0]}));
  for(const text of ['ข้อมูลที่ใช้ / เวลา','สิ่งที่ยังไม่ทราบ','แหล่งอ้างอิง'])assert.ok(detail.includes(text));
  assert.doesNotMatch(detail,/สวนปกติ|เสี่ยงโรค \d+%/);
});

test('shared forecast does not duplicate current cards or advice in forecast-only content',()=>{
  const {ForecastContent}=load('web/react/src/OrchardForecast.jsx');
  const html=renderToStaticMarkup(React.createElement(ForecastContent,{forecast:{status:'cached',hourly:[],daily:[],summaries:[]},reading:{},observation:{},includeCurrent:false,includeAdvice:false}));
  assert.match(html,/พยากรณ์รายวัน 7 วัน/);assert.doesNotMatch(html,/อากาศปัจจุบันจาก API|รายงานโรคระดับจังหวัด/);
});

test('seven-day view compares all dates, keeps missing values and explains inspection prompts',()=>{
  const {SevenDayForecast:unused,default:SevenDay}=load('web/react/src/SevenDayForecast.jsx');
  const daily=Array.from({length:7},(_,i)=>({time:`2026-11-0${i+1}`,rain_mm:i===0?0:null,temperature_min_c:22,temperature_max_c:29}));
  const html=renderToStaticMarkup(React.createElement(SevenDay,{forecast:{status:'cached',daily},reading:{},observation:{}}));
  for(const d of daily)assert.ok(html.includes(d.time)||html.includes(new Date(d.time+'T12:00:00+07:00').toLocaleDateString('th-TH',{weekday:'short',day:'numeric',month:'short'})));
  assert.match(html,/ตารางเปรียบเทียบครบ 7 วัน/);assert.match(html,/ใช้ข้อมูลนี้เตรียมอะไรได้บ้าง/);
  assert.match(html,/ไม่ใช่ระดับอันตราย/);assert.match(html,/—/);assert.doesNotMatch(html,/NaN|Infinity|สวนปกติ/);
});

test('weekly reconciliation does not sum incomplete, duplicate or discontinuous forecasts',()=>{
  const {weekOverview}=load('web/react/src/SevenDayForecast.jsx');
  const days=Array.from({length:7},(_,i)=>({time:`2026-11-0${i+1}`,rain_mm:0}));
  assert.equal(weekOverview(days).totalRain,0);assert.equal(weekOverview(days).rainDays,0);
  days[1].rain_mm=null;assert.equal(weekOverview(days).totalRain,null);assert.equal(weekOverview(days).validDays,6);
  days[1].rain_mm=1;days[6].time='2026-11-08';assert.equal(weekOverview(days).totalRain,null);
  days[6].time=days[5].time;assert.equal(weekOverview(days).days.length,0);
});

test('daily action conditions reject old forecasts, missing rain and unrelated or old orchard stages',()=>{
  const {dailyPlan}=load('web/react/src/SevenDayForecast.jsx');
  const f={status:'cached',orchard_key:'orchard-a'},day={time:'2026-11-01',rain_mm:5,rain_probability_percent:80};
  const reading={data:{status:'stale_live',sensor_quality:{soil:'invalid'},sensor_time:'2026-10-31T01:00:00Z'}};
  const observation={saved:{orchard_key:'orchard-a',stage:'growth',observed_at:'2026-11-01T08:00:00+07:00'}};
  let items=dailyPlan(f,day,reading,observation,'2026-11-01');assert.deepEqual(Array.from(items,i=>i.id),['water','sensor','fruit']);
  assert.match(items[0].why,/ยังไม่ยืนยัน/);assert.match(items[1].why,/ยังไม่สั่ง/);
  assert.equal(dailyPlan({...f,status:'stale'},day,reading,observation,'2026-11-01')[0].id,'forecast');
  assert.equal(dailyPlan(f,{...day,rain_mm:null},reading,observation,'2026-11-01')[0].id,'incomplete');
  assert.equal(dailyPlan(f,{...day,time:'2026-10-31'},reading,observation,'2026-11-01')[0].id,'incomplete');
  observation.saved.orchard_key='another';assert.ok(!dailyPlan(f,day,reading,observation,'2026-11-01').some(i=>i.id==='fruit'));
  observation.saved.orchard_key='orchard-a';observation.saved.observed_at='2026-01-01T00:00:00Z';assert.ok(!dailyPlan(f,day,reading,observation,'2026-11-01').some(i=>i.id==='fruit'));
});

test('knowledge covers every displayed metric without inventing stage-specific thresholds',()=>{
  const {measurementGuide,stageGuidance}=load('web/react/src/OrchardKnowledge.jsx'),{metrics}=load('web/react/src/data.js');
  for(const [key] of metrics){const guide=measurementGuide(key);for(const field of ['use','range','caution','source','rangeKind'])assert.ok(guide[field],key+':'+field);}
  assert.match(measurementGuide('vpd_kpa').range,/ยังไม่มี/);
  assert.match(measurementGuide('soil_moisture_percent').range,/สอบเทียบ/);
  assert.match(measurementGuide('soil_ph').range,/5.5–6.5/);
  assert.match(measurementGuide('soil_n').range,/ไม่กำหนด/);
  assert.match(stageGuidance(undefined),/ยังไม่ได้บันทึก/);
  assert.doesNotMatch(stageGuidance('flower'),/งดน้ำทันที|\d+ ลิตร/);
});

test('soil reference image is real LDD excerpt, labels uncertainty and does not reveal coordinates',()=>{
  const {SoilReference}=load('web/react/src/OrchardKnowledge.jsx');
  const html=renderToStaticMarkup(React.createElement(SoilReference,{linked:true}));
  assert.match(html,/data:image\/jpeg;base64,/);assert.match(html,/ทุ่งหว้า/);assert.match(html,/Tg/);
  assert.match(html,/ไม่ใช่ภาพดินจริงของสวนนี้/);assert.match(html,/50 เมตร/);
  assert.match(html,/5.5–6.0/);assert.match(html,/ไม่ยืนยันขอบเขตหรือดินทุกจุด/);
  assert.doesNotMatch(html,/latitude|longitude|8\.833|99\.371/);
  const unlinked=renderToStaticMarkup(React.createElement(SoilReference,{linked:false}));assert.match(unlinked,/ยังไม่ผูกกับบัญชีสวนนี้/);
});
