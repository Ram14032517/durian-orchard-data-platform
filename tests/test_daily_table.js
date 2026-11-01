const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');

function viewFor(file){
  const html=fs.readFileSync(path.join(__dirname,'..',file),'utf8');
  return new Function(html.slice(html.indexOf('function dailyView('),html.indexOf('function renderDailyTable('))+';return dailyView;')();
}
for(const file of ['web/templates/unified_orchard_map.html','research_data/five_province_history/UNIFIED_MAP_CLASSIC.html']){
  const view=viewFor(file);
  test(file+': chart gaps stay missing while measured zero remains zero',()=>{
    const html=fs.readFileSync(path.join(__dirname,'..',file),'utf8');
    const series=new Function(html.slice(html.indexOf('function chartSeries('),html.indexOf('function chart(a,b)'))+';return chartSeries;')();
    const rows=[{date:'2025-07-01',T2M:''},{date:'2025-07-02',T2M:null},{date:'2025-07-03',T2M:0},{date:'2025-07-04',T2M:20}];
    assert.deepEqual(series(rows,'T2M',false).map(r=>r.value),[null,null,0,20]);
    assert.equal(series(rows,'T2M',true)[0].value,10);
    assert.equal(series(rows.slice(0,2),'T2M',true)[0].value,null);
  });
  test(file+': 7, 10, all and final page keep every day accessible',()=>{
    const rows=Array.from({length:31},(_,i)=>({date:'2025-07-'+String(i+1).padStart(2,'0'),T2M:i}));
    assert.equal(view(rows,null,'date',1,7,0).rows.length,7);
    const last=view(rows,null,'date',1,7,99);
    assert.equal(last.page,4);assert.equal(last.rows.length,3);assert.equal(last.rows[2].date,'2025-07-31');
    assert.equal(view(rows,null,'date',1,10,0).rows.length,10);
    assert.equal(view(rows,null,'date',1,0,9).rows.length,31);
    assert.equal(view(rows,null,'date',-1,7,0).rows[0].date,'2025-07-31');
    assert.equal(view([],null,'date',1,7,0).total,0);
  });
  test(file+': numeric sorting preserves zeros and leaves missing values last in either direction',()=>{
    const rows=[{date:'2025-07-01',PRECTOTCORR:null},{date:'2025-07-02',PRECTOTCORR:9},{date:'2025-07-03',PRECTOTCORR:0},{date:'2025-07-04',PRECTOTCORR:2}];
    assert.deepEqual(view(rows,null,'PRECTOTCORR',1,0,0).rows.map(r=>r.PRECTOTCORR),[0,2,9,null]);
    assert.deepEqual(view(rows,null,'PRECTOTCORR',-1,0,0).rows.map(r=>r.PRECTOTCORR),[9,2,0,null]);
  });
  test(file+': A/B join by date and sorting never changes chart/export input arrays',()=>{
    const a=[{date:'2025-07-02',T2M:27},{date:'2025-07-01',T2M:26}],b=[{date:'2025-07-01',T2M:30}];
    const original=JSON.stringify([a,b]);
    const result=view(a,b,'B_T2M',-1,0,0);
    assert.equal(result.rows[0].date,'2025-07-01');assert.equal(result.rows[0].B_T2M,30);
    assert.equal(result.rows[1].B_T2M,null);assert.equal(JSON.stringify([a,b]),original);
  });
}
