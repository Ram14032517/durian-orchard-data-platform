const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const scope={};
vm.runInNewContext(fs.readFileSync(path.join(root,'web/assets/js/orchard_workspace.js'),'utf8'),scope);
const h=scope.OrchardWorkspaceHelpers;

test('missing values stay missing and measured zero stays zero',()=>{
  for(const value of [null,undefined,'','  ','not available',NaN])assert.equal(h.number(value),null);
  assert.equal(h.number(0),0);assert.equal(h.number('24.5'),24.5);
});
test('self-entered garden notes need selection, year and sensible units',()=>{
  assert.throws(()=>h.gardenRecord({note:'test'},null,2026));
  assert.throws(()=>h.gardenRecord({last_harvest_kg:100},'pin-1',2026));
  assert.throws(()=>h.gardenRecord({last_harvest_kg:100,harvest_year:2027},'pin-1',2026));
  assert.throws(()=>h.gardenRecord({bearing_area_rai:0},'pin-1',2026));
  assert.throws(()=>h.gardenRecord({bearing_trees:1.5},'pin-1',2026));
  assert.throws(()=>h.gardenRecord({bearing_trees:-1},'pin-1',2026));
  assert.throws(()=>h.gardenRecord({},'pin-1',2026));
  const r=h.gardenRecord({last_harvest_kg:0,harvest_year:2025},'pin-1',2026);
  assert.equal(r.last_harvest_kg,0);assert.equal(r.bearing_area_rai,null);
  assert.equal(r.source,'user_entered_unverified');assert.equal(r.selection_id,'pin-1');
  assert.equal(r.yield_kg_per_rai,undefined,'no invented garden yield');
});
test('GAP search supports Thai district names without searching owner identity',()=>{
  const window={};vm.runInNewContext(fs.readFileSync(path.join(root,'web/assets/js/orchard_gap_layer.js'),'utf8'),{window,URL});
  const filter=window.createGapOrchardLayer.helpers.filterFeatures;
  const f=(id,district)=>({id,properties:{id,district,tambon:'เขาบายศรี',crop:'ทุเรียน',owner_name:'private-name'},geometry:{type:'Point',coordinates:[102,12]}});
  const rows=[f('gap-1','ท่าใหม่'),f('gap-2','ขลุง')];
  assert.equal(filter(rows,{query:'ท่าใหม่'}).length,1);
  assert.equal(filter(rows,{query:'GAP-1'}).length,1);
  assert.equal(filter(rows,{query:'private-name'}).length,0);
  assert.equal(filter(rows,{query:'ไม่มี'}).length,0);
});
test('classic analysis tools retain their sections after React migration',()=>{
  const html=fs.readFileSync(path.join(root,'research_data/five_province_history/UNIFIED_MAP_CLASSIC.html'),'utf8');
  for(const id of ['current-section','weather-section','soil-analysis','yield-section','report-section'])assert.ok(html.includes('href="#'+id+'"'),id);
  assert.ok(!html.includes('href="#training-section"'),'training downloads page is not in navigation');
  assert.match(html,/<section id="training-section" class="training-section" hidden>/,'internal data references remain hidden');
  assert.ok(html.includes("document.querySelector('.monthly-report').id='report-section'"));
  assert.ok(html.includes('OrchardWorkspaceHelpers'));
  assert.ok(!html.includes('__WORKSPACE_CODE__'));
  const css=fs.readFileSync(path.join(root,'web/assets/css/orchard_workspace.css'),'utf8');
  assert.equal((css.match(/\{/g)||[]).length,(css.match(/\}/g)||[]).length);
  assert.ok(css.includes('flex:none; height:auto'));
});
test('adjacent-cell labels never overlap or drop registry records, even at high zoom',()=>{
  const window={};vm.runInNewContext(fs.readFileSync(path.join(root,'web/assets/js/orchard_gap_layer.js'),'utf8'),{window,URL});
  const group=window.createGapOrchardLayer.helpers.groupViewport;
  const rows=Array.from({length:240},(_,i)=>({id:'p'+i,geometry:{coordinates:[100+(i%20)*.02,12+Math.floor(i/20)*.02]},properties:{}}));
  const project=(lat,lon)=>({x:lon*1000,y:lat*1000});
  for(const zoom of [6,10,14]){
    const groups=group(rows,project,zoom);
    assert.equal(groups.flatMap(g=>g.features).length,rows.length);
    assert.equal(new Set(groups.flatMap(g=>g.features.map(f=>f.id))).size,rows.length);
    for(let i=0;i<groups.length;i++)for(let j=0;j<i;j++){
      const a=project(groups[i].lat,groups[i].lon),b=project(groups[j].lat,groups[j].lon);
      assert.ok(Math.hypot(a.x-b.x,a.y-b.y)>=56-1e-6);
    }
  }
});
