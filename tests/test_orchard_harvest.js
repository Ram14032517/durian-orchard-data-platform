const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('web/assets/js/orchard_harvest.js','utf8');
const scope={};vm.runInNewContext(source,scope);const h=scope.OrchardHarvestHelpers;
test('missing weights remain null; reported zero remains zero',()=>{
  const p=h.payload({harvest_year:'2025',harvested_kg:'0',bearing_area_rai:''},2026);
  assert.equal(p.harvested_kg,0);assert.equal(p.bearing_area_rai,null);
});
test('future year, invalid weight, and planted zero area are rejected',()=>{
  assert.throws(()=>h.payload({harvest_year:2027},2026));
  assert.throws(()=>h.payload({harvest_year:2025,harvested_kg:'NaN'},2026));
  assert.throws(()=>h.payload({harvest_year:2025,bearing_area_rai:0},2026));
});
test('owner and calculated target are never accepted from form data',()=>{
  const p=h.payload({harvest_year:2025,owner_id:'other',yield_kg_per_rai:999},2026);
  assert.equal(p.owner_id,undefined);assert.equal(p.yield_kg_per_rai,undefined);
});
test('harvest graph separates orchards and seasons and excludes incomplete records',()=>{
  const rows=[{orchard_code:'A',season_key:'main',harvest_year:2024,yield_kg_per_rai:10,status:'complete'},
    {orchard_code:'A',season_key:'main',harvest_year:2023,yield_kg_per_rai:0,status:'complete'},
    {orchard_code:'B',season_key:'main',harvest_year:2024,yield_kg_per_rai:20,status:'complete'},
    {orchard_code:'A',season_key:'main',harvest_year:2025,yield_kg_per_rai:null,status:'draft'}];
  const groups=h.historyGroups(rows);assert.equal(groups.length,2);assert.equal(groups[0].points.length,2);
  assert.equal(groups[0].points[0].value,0);assert.equal(groups[0].points[0].year,2023);
});
test('private history uses authenticated server persistence and literal DOM text',()=>{
  assert.doesNotMatch(source,/localStorage|sessionStorage/);
  assert.match(source,/credentials:'same-origin'/);assert.match(source,/'X-CSRF-Token'/);
  assert.match(source,/expected_version/);assert.match(source,/td\.textContent=text/);
  assert.match(source,/Baseline ไม่ใช่ AI Forecast/);assert.doesNotMatch(source,/A\.gap_id|B\.gap_id/);
});
