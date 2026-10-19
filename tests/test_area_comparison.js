const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');

function harness(fetch=async()=>({ok:true,json:async()=>({features:[]})})){
  const html=fs.readFileSync(path.join(__dirname,'../web/templates/unified_orchard_map.html'),'utf8');
  const code=html.slice(html.indexOf('function areaControl('),html.indexOf('const events='));
  const controls=new Map(),fits=[];
  const $=id=>{
    if(!controls.has(id)){
      const node={value:'',options:[],disabled:false,textContent:'',setAttribute(){},add(option){this.options.push(option);}};
      Object.defineProperty(node,'innerHTML',{set(){this.options=[];this.value='';}});controls.set(id,node);
    }
    return controls.get(id);
  };
  const map={removeLayer(){},stop(){},invalidateSize(){},fitBounds(bounds,options){fits.push({bounds,options});}};
  const L={circleMarker(){return{addTo(){return this;},bindTooltip(){return this;}};}};
  const DATA={provinces:['84','22','53'].map((code,i)=>({province_code:code,province_name:code,weather_latitude:9+i,weather_longitude:99+i})),districts:[]};
  const provinceLayer={eachLayer(fn){for(const code of ['84','22','53'])fn({feature:{properties:{province_code:code}},setStyle(){},getBounds(){return code;}});}};
  const api=new Function('DATA','$','map','L','provinceLayer','document','fetch','Option',`
    let A=null,B=null,markerA=null,markerB=null,soilLayer=null,features=[],activeArea='A',loadVersion=0;
    const soilCache={};function context(){}function invalidateWeather(){}function requestAnimationFrame(fn){fn();}
    ${code}
    return {selectA,selectB,provinceChange,focusArea,fitProvince,clearComparison,setAreaEditor,
      state:()=>({A,B,activeArea,features}),controls:$};
  `)(DATA,$,map,L,provinceLayer,{body:{classList:{toggle(){}}},querySelectorAll:()=>[]},fetch,function(text,value){this.text=text;this.value=value;});
  api.controls('province').value='84';
  api.fits=fits;
  api.selectA({code:'84',lat:9,lon:99,label:'A',note:'reference'});
  return api;
}

test('B province changes independently and zooms to its bounds',async()=>{
  const ui=harness();ui.controls('province-b').value='22';await ui.provinceChange('B');
  assert.equal(ui.state().A.code,'84');assert.equal(ui.state().B.code,'22');
  assert.match(ui.controls('comparison-summary').textContent,/พื้นที่ B:/);
  assert.equal(ui.state().activeArea,'B');assert.equal(ui.fits.at(-1).bounds,'22');
  assert.equal(ui.fits.at(-1).options.animate,false);assert.equal(ui.fits.at(-1).options.maxZoom,10);
});
test('identical coordinates do not create a duplicate B series',()=>{
  const ui=harness();ui.selectB({...ui.state().A});
  assert.equal(ui.state().B,null);assert.match(ui.controls('compare-point').textContent,/ซ้ำ/);
  ui.selectB({code:'22',lat:10,lon:100,label:'B',note:'reference'});
  assert.equal(ui.state().B.code,'22');ui.selectA({...ui.state().B});
  assert.equal(ui.state().B,null);assert.equal(ui.controls('swap-areas').disabled,true);
});
test('clearing B preserves A and disables district/soil selection',async()=>{
  const ui=harness();ui.controls('province-b').value='22';await ui.provinceChange('B');
  ui.controls('province-b').value='';await ui.provinceChange('B');
  assert.equal(ui.state().B,null);assert.equal(ui.state().A.code,'84');
  assert.match(ui.controls('comparison-summary').textContent,/เพิ่มพื้นที่ B/);
  assert.equal(ui.controls('district-b').disabled,true);assert.equal(ui.controls('soil-b').disabled,true);
});
test('focus changes only the map target, never either selected area',async()=>{
  const ui=harness();ui.controls('province-b').value='22';await ui.provinceChange('B');
  const before=JSON.stringify([ui.state().A,ui.state().B]);await ui.focusArea('A');
  assert.equal(JSON.stringify([ui.state().A,ui.state().B]),before);
  assert.equal(ui.state().activeArea,'A');assert.equal(ui.fits.at(-1).bounds,'84');
  assert.equal(ui.controls('map-area-a').checked,true);
  assert.equal(ui.controls('map-area-b').checked,false);
});

test('area editor collapses only on request, never on selection or focus',async()=>{
  const ui=harness();ui.setAreaEditor(false);
  ui.controls('province-b').value='22';await ui.provinceChange('B');
  assert.equal(ui.controls('area-section').hidden,true);
  assert.equal(ui.controls('toggle-area-editor').textContent,'แก้ไขพื้นที่');
  ui.setAreaEditor(true);await ui.focusArea('A');
  assert.equal(ui.controls('area-section').hidden,false);
});

test('soil comparison uses the selected real unit, no district-wide proxy or invented pH',()=>{
  const js=fs.readFileSync(path.join(__dirname,'../web/assets/js/orchard_soil_exploration.js'),'utf8');
  const fn=new Function('DATA',js.slice(js.indexOf('function soilComparisonValues('),js.indexOf('function renderSoilExploration('))+';return soilComparisonValues;')({provinces:[{province_code:'84',province_name:'สุราษฎร์ธานี'}],soil_properties:[{province_code:'84',district:'อ.ท่าชนะ',soil_code:'Bu',soil_name:'สายบุรี',topsoil_ph:'กรดจัด',topsoil_texture:'ดินร่วน',fertility:'ต่ำ'}]});
  assert.equal(fn({code:'84',district:'อ.ท่าชนะ',soil_code:'Bu'})[4],'กรดจัด');
  assert.equal(fn({code:'84',district:'อ.ท่าชนะ',soil_code:'Bu',soil_properties:{topsoil_ph:'กรดปานกลาง'}})[4],'กรดปานกลาง');
  assert.equal(fn({code:'84',district:'อ.ท่าชนะ'})[4],'เลือกหน่วยดินก่อน');
  assert.equal(fn({code:'84',district:'อ.อื่น',soil_code:'Bu'})[4],'ไม่ระบุ');
  assert.equal(fn(null)[0],'ยังไม่เลือก');
});
test('a late B layer response cannot replace the current A layer',async()=>{
  let finishB;
  const ui=harness(async url=>({ok:true,json:()=>url.includes('22.geojson')?new Promise(resolve=>finishB=resolve):Promise.resolve({features:[{id:'53'}]})}));
  ui.controls('province-b').value='22';const pending=ui.provinceChange('B');
  await Promise.resolve();await Promise.resolve();
  ui.controls('province').value='53';await ui.provinceChange('A');
  finishB({features:[{id:'22'}]});await pending;
  assert.equal(ui.state().activeArea,'A');assert.deepEqual(ui.state().features,[{id:'53'}]);
});
test('annual comparison uses the exact province/year, never a different-year PDF total',()=>{
  const js=fs.readFileSync(path.join(__dirname,'../web/assets/js/orchard_monthly_report.js'),'utf8');
  const fn=new Function('DATA',js.slice(js.indexOf('function annualRecords('),js.indexOf('function selectReportMonth('))+';return annualRecords;')({annual:[
    {province_code:'84',year_ce:2023,production_tonnes:77585},
    {province_code:'84',year_ce:2025,production_tonnes:79944},
  ]});
  const selected=fn({code:'84'},{code:'22'},2025);
  assert.equal(selected.a.production_tonnes,79944);assert.equal(selected.b,null);
  assert.equal(fn({code:'84'},null,2026).a,null);
});
