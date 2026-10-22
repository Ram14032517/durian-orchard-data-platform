const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const source=fs.readFileSync('web/templates/unified_orchard_map.html','utf8');

function fixture(){
  const element={clientWidth:0,clientHeight:0};
  const calls=[],frames=[];
  let resize;
  const context={
    document:{readyState:'complete'},
    $:()=>element,
    map:{stop:()=>calls.push('stop'),invalidateSize:()=>calls.push('resize-now')},
    mapMotion:{invalidate:()=>calls.push('resize-deferred')},
    areaControl:()=>({value:'84'}),
    fitProvince:(code,options)=>calls.push(['fit',code,options.animate,element.clientWidth,element.clientHeight]),
    requestAnimationFrame:callback=>{frames.push(callback);return frames.length;},
    ResizeObserver:class {constructor(callback){resize=callback;}observe(){}},
  };
  vm.createContext(context);
  vm.runInContext('let mapReady=false,initialMapSettleFrame=null;'+
    source.slice(source.indexOf('function settleInitialMap('),source.indexOf('function areaName('))+
    source.match(/new ResizeObserver\([^\n]+/)[0],context);
  return {context,element,calls,resize:()=>resize(),flush:()=>{while(frames.length)frames.shift()();}};
}

test('opening a hidden map waits for its visible resize before the first province fit',()=>{
  const f=fixture();
  f.context.settleInitialMap();f.flush();
  assert.deepEqual(f.calls,[]);
  // A tab click can run before Lumen has exposed the panel.
  f.context.settleInitialMap();f.flush();
  f.element.clientWidth=960;f.element.clientHeight=550;
  f.resize();f.flush();
  assert.deepEqual(f.calls,['resize-deferred','stop','resize-now',['fit','84',false,960,550]]);
  // Subsequent resize notifications must not reset the user's map position.
  f.resize();f.flush();
  assert.equal(f.calls.filter(call=>Array.isArray(call)&&call[0]==='fit').length,1);
});

test('queued initial fits are coalesced and cannot fit a panel hidden before paint',()=>{
  const f=fixture();
  f.element.clientWidth=960;f.element.clientHeight=550;
  f.context.settleInitialMap();f.context.settleInitialMap();
  f.element.clientWidth=0;f.element.clientHeight=0;
  f.flush();
  assert.deepEqual(f.calls,[]);
  f.element.clientWidth=960;f.element.clientHeight=550;
  f.resize();f.resize();f.flush();
  assert.equal(f.calls.filter(call=>Array.isArray(call)&&call[0]==='fit').length,1);
});

test('interactive DOM can fit the visible map without waiting for external tile or font loads',()=>{
  const f=fixture();
  f.context.document.readyState='interactive';
  f.element.clientWidth=960;f.element.clientHeight=550;
  f.context.settleInitialMap();f.flush();
  assert.deepEqual(f.calls,['stop','resize-now',['fit','84',false,960,550]]);
  assert.match(source,/document\.addEventListener\('DOMContentLoaded'/);
  assert.doesNotMatch(source,/window\.addEventListener\('load',\(\)=>requestAnimationFrame\(settleInitialMap\)/);
});

test('the first fit still waits for the DOM parser to finish',()=>{
  const f=fixture();
  f.context.document.readyState='loading';
  f.element.clientWidth=960;f.element.clientHeight=550;
  f.context.settleInitialMap();f.flush();
  assert.deepEqual(f.calls,[]);
  f.context.document.readyState='interactive';
  f.context.settleInitialMap();f.flush();
  assert.equal(f.calls.filter(call=>Array.isArray(call)&&call[0]==='fit').length,1);
});

test('a province selected while the IoT home hides the map is not fitted at zero size',()=>{
  const f=fixture();
  f.context.provinceLayer={eachLayer:fn=>fn({feature:{properties:{province_code:'84'}},setStyle(){},getBounds:()=>[[8,98],[10,100]]})};
  f.context.moveMapBounds=()=>f.calls.push('navigate');
  vm.runInContext(source.slice(source.indexOf('function fitProvince('),source.indexOf('function updateMapTarget(')),f.context);
  f.context.fitProvince('84');
  assert.deepEqual(f.calls,[]);
  f.element.clientWidth=960;f.element.clientHeight=550;
  f.context.fitProvince('84');
  assert.deepEqual(f.calls,['stop','resize-now','navigate']);
});
