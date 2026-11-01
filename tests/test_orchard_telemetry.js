const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('web/assets/js/orchard_monthly_report.js','utf8');
const chartSource=source.slice(source.indexOf('function telemetryChart('),source.indexOf('let historyRequest='));
const context={esc:v=>String(v),fmt:v=>v==null?'—':String(v),Date,Number,Math};
vm.createContext(context);vm.runInContext(chartSource,context);
test('telemetry chart preserves missing periods as line gaps and measured zero',()=>{
  const rows=[0,null,25].map((v,i)=>({time:`2026-10-09T0${i}:00:00+07:00`,soil:v,valid_counts:{soil:v===null?0:1}}));
  const output=context.telemetryChart(rows,'soil','ความชื้นดิน','%','#00FFFF');
  const path=output.match(/<path d="([^"]+)"/)[1];
  assert.equal((path.match(/M/g)||[]).length,2);
  assert.equal((path.match(/L/g)||[]).length,0);
  assert.match(output,/มีค่า 2\/3 ช่วง/);
  assert.match(output,/ต่ำสุด 0/);
  assert.match(output,/data-expand-plot/);
  assert.match(output,/aria-label="ขยายกราฟความชื้นดิน"/);
});
test('no data renders an explicit empty state, not invented telemetry',()=>{
  const output=context.telemetryChart([],'soil','ความชื้นดิน','%','#00FFFF');
  assert.match(output,/ไม่มีค่าที่ใช้ได้/);assert.doesNotMatch(output,/<path/);
});
test('rolling rain and wind gust charts identify aggregation without claiming rainfall sum',()=>{
  const rows=[{time:'2026-10-09T01:00:00+07:00',rain_1h_mm:3,wind_gust:10,valid_counts:{rain_1h_mm:1,wind_gust:1}}];
  assert.match(context.telemetryChart(rows,'rain_1h_mm','ฝน','mm','#00FFFF'),/ค่าล่าสุดของแต่ละช่วง/);
  assert.match(context.telemetryChart(rows,'wind_gust','ลม','km\/h','#00FFFF'),/ค่าสูงสุดของแต่ละช่วง/);
});
