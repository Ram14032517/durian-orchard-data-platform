const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const source=fs.readFileSync('web/assets/js/orchard_monthly_report.js','utf8');

test('private data requires sign-in; other API errors do not suggest signing in',async()=>{
  const context={
    fetch:async()=>({ok:false,status:401,headers:{get:()=> 'application/json'},json:async()=>({error:'กรุณาเข้าสู่ระบบ'})}),
    document:{createElement:tag=>({tag})},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('async function currentJson('),source.indexOf('let currentRequest=')),context);
  let denied;try{await context.currentJson('/api/orchard-status');}catch(e){denied=e;}
  assert.equal(denied.status,401);
  const node={append(...items){this.items=items;}};
  context.showOrchardAccessError(node,denied,'อ่านไม่ได้: ');
  assert.equal(node.items[1].href,'/login');assert.match(node.textContent,/ข้อมูลส่วนตัว/);
  const other={append(){throw Error('must not insert login for a database failure');}};
  context.showOrchardAccessError(other,{status:503,message:'database unavailable'},'อ่านไม่ได้: ');
  assert.equal(other.textContent,'อ่านไม่ได้: database unavailable');
});

test('every open starts on the original IoT home, not a saved research-map tab',()=>{
  const calls=[];
  const setup=source.slice(source.indexOf('// Keep the original IoT dashboard'),source.indexOf('const openGapMap='));
  vm.runInNewContext(setup,{
    showWorkspaceView:(...args)=>calls.push(['view',...args]),
    setAreaEditor:value=>calls.push(['editor',value]),
    sessionStorage:{getItem:()=>{throw Error('must not restore an old map-first session');}},
  });
  assert.deepEqual(calls,[['view','current-section',false],['editor',false]]);
  assert.doesNotMatch(source,/orchard\.workspace\.v2/);
  assert.match(source,/'soil-analysis':'แผนที่สวน'/);
  assert.match(source,/openGapMap\.onclick=\(\)=>\{showWorkspaceView\('soil-analysis',false\)/);
});

test('changing A/B reference coordinates does not retarget the IoT status endpoint',async()=>{
  const nodes={
    'current-year':{value:'2026'},
    'current-section':{hidden:false},
    'view-summary':{},
    'current-province':{},
    'current-orchard':{},
    'orchard-data-message':{},
  };
  const calls=[];
  const context={
    $:id=>nodes[id],
    A:{code:'84',lat:9.1,lon:99.3,gap_orchard_id:'registry-a'},
    DATA:{provinces:[{province_code:'84',province_name:'สุราษฎร์ธานี'},{province_code:'22',province_name:'จันทบุรี'}]},
    encodeURIComponent,
    currentJson:async url=>{
      calls.push(url);
      if(url==='/api/orchard-status')return {status:'missing',message:'No sensor reading available'};
      return {predicted_kg_rai:null,message:'Fixture, not a live reading',as_of:'2026-10-22'};
    },
    fmt:String,
    esc:String,
    renderOrchardInsights:()=>{},
    orchardReferenceCards:()=>'<div></div>',
  };
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('let currentRequest='),source.indexOf("$('current-year').onchange=")),context);
  await context.refreshCurrent();
  context.A={code:'22',lat:12.6,lon:102.1,gap_orchard_id:'registry-b'};
  await context.refreshCurrent();
  assert.deepEqual(calls,[
    '/api/orchard-status',
    '/api/province-estimate?province=84&year=2026',
    '/api/orchard-status',
    '/api/province-estimate?province=22&year=2026',
  ]);
  assert.equal(nodes['orchard-data-message'].textContent,'No sensor reading available');
});

test('IoT history uses only its own date range, never GAP or A/B coordinates',async()=>{
  const nodes={
    'orchard-period':{value:'week'},
    'orchard-history-end':{value:'2026-10-22'},
    'orchard-history-note':{},
    'orchard-timeseries':{},
    'orchard-history-table':{replaceChildren(){}},
  };
  const calls=[];
  const context={
    $:id=>nodes[id],
    A:{code:'84',lat:9.1,lon:99.3,gap_orchard_id:'unverified-registry'},
    telemetryFields:[],
    selectedTelemetryFields:()=>[],
    telemetryChart:()=>'',
    table:()=>'',
    currentJson:async url=>{calls.push(url);return {source:'Supabase test fixture',raw_count:0,message:'No observations',rows:[]};},
  };
  vm.createContext(context);
  vm.runInContext(source.slice(source.indexOf('let historyRequest='),source.indexOf('const historyEndLabel=')),context);
  await context.refreshOrchardHistory();
  assert.deepEqual(calls,['/api/orchard-history?period=week&end=2026-10-22']);
  assert.match(nodes['orchard-history-note'].textContent,/0 ระเบียน/);
});
