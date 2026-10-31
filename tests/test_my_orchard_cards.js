const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('web/assets/js/my_orchard_cards.js','utf8');
const scope={esc:String,fmt:String};vm.createContext(scope);vm.runInContext(source,scope);
test('cards preserve measured zero and never show invalid or stale data as live',()=>{
  const data={status:'fresh_live',sensor_time:'2026-10-27T12:00:00Z',sensor_quality:{soil:'invalid',weather:'valid'},readings:{soil_moisture_percent:0,rain_1h_mm:0}};
  const html=scope.orchardReferenceCards(data);
  assert.match(html,/ตรวจสอบอุปกรณ์/);assert.match(html,/<span>0<\/span><small>มม\.<\/small>/);
  assert.doesNotMatch(html,/<span>0<\/span><small>%<\/small>/);
  data.status='stale_live';assert.doesNotMatch(scope.orchardReferenceCards(data),/<span>0<\/span><small>มม\.<\/small>/);
});
