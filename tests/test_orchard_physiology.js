const test=require('node:test');const assert=require('node:assert/strict');
const {atmosphere,waterBalance,floweringRange}=require('../web/assets/js/orchard_physiology.js');
test('FAO56 daily calculation, saturated air and zero energy',()=>{
  const x={tmin:20,tmax:30,rh:60,u2:2,rn:12,pressure:101.3};
  const a=atmosphere(x);assert.ok(a.vpd_kpa>1.3&&a.vpd_kpa<1.4);assert.ok(a.et0_mm_day>4&&a.et0_mm_day<6);
  assert.deepEqual(atmosphere({...x,rh:100,rn:0}),{vpd_kpa:0,et0_mm_day:0});
  assert.throws(()=>atmosphere({...x,rh:101}));assert.throws(()=>atmosphere({...x,rn:null}));
});
const soil={et0:5,kc:1,fc:.3,wp:.1,root:1,p:.5,depletion:0,rain:0,irrigation:0,days:31};
test('dry scenario crosses RAW and reduces ET; mass balance and bounds',()=>{
  // A short subtract/multiply/divide chain may round by a few binary64 ulps.
  const near=(actual,expected)=>assert.ok(Math.abs(actual-expected)<=16*Number.EPSILON*Math.max(1,Math.abs(expected)),`${actual} differs from ${expected}`);
  const result=waterBalance(soil);near(result.taw_mm,200);near(result.raw_mm,100);
  assert.equal(result.rows[0].depletion_mm,5);near(result.rows[20].ks,1);assert.ok(result.rows[21].ks<1);
  assert.ok(result.rows.every(r=>r.ks>=0&&r.ks<=1&&r.depletion_mm<=200));
  assert.ok(Math.abs(result.rows.reduce((s,r)=>s+r.etc_adjusted_mm,0)-result.rows.at(-1).depletion_mm)<1e-10);
});
test('water delivery and invalid/missing soil parameters',()=>{
  const r=waterBalance({...soil,rain:10,days:1});assert.equal(r.rows[0].depletion_mm,5);assert.equal(r.rows[0].deep_drainage_mm,10);
  for(const change of [{fc:.1},{root:0},{depletion:201},{p:1},{days:1.5},{kc:NaN}])assert.throws(()=>waterBalance({...soil,...change}));
});
test('backdating preserves month uncertainty, leap day and year crossing',()=>{
  assert.deepEqual(floweringRange(2024,2,1,1),{start:'2024-01-31',end:'2024-02-28'});
  assert.deepEqual(floweringRange(2025,1,120,140),{start:'2024-08-14',end:'2024-10-03'});
  assert.throws(()=>floweringRange(2025,1,140,120));assert.throws(()=>floweringRange(2025,1,120.5,140));
});
