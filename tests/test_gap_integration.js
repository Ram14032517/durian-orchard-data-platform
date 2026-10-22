const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../web/assets/js/orchard_gap_integration.js'),'utf8');
const helpers=new Function(source+';return gapSpatialHelpers;')();
const ring=[[99,9],[100,9],[100,10],[99,10],[99,9]];
const feature={type:'Feature',geometry:{type:'Polygon',coordinates:[ring]},properties:{district:'อ.ท่าชนะ',soil_code:'Bu',soil_name:'สายบุรี',topsoil_ph:'กรดจัด'}};
const provinces=[{province_code:'84',province_name:'สุราษฎร์ธานี'}];
const districts=[{province_code:'84',district:'อ.ท่าชนะ'}];
const point={code:'84',lat:9.5,lon:99.5,district:'ท่าชนะ',gap_id:'gap-sample',gap_snapshot_date:'2026-10-20'};

test('mapped soil respects holes, multipolygons and outside locations',()=>{
  assert.equal(helpers.pointInGeometry(99.5,9.5,feature.geometry),true);
  const hole=[[99.4,9.4],[99.6,9.4],[99.6,9.6],[99.4,9.6],[99.4,9.4]];
  assert.equal(helpers.pointInGeometry(99.5,9.5,{type:'Polygon',coordinates:[ring,hole]}),false);
  assert.equal(helpers.pointInGeometry(99.5,9.5,{type:'MultiPolygon',coordinates:[[ring]]}),true);
  assert.equal(helpers.pointInGeometry(100.5,9.5,feature.geometry),false);
  assert.equal(helpers.pointInGeometry(NaN,9.5,feature.geometry),false);
});
test('GAP pin retains actual registry position and provenance when soil is joined',()=>{
  const result=helpers.preparePoint(point,provinces,districts,[feature]);
  assert.equal(result.lat,point.lat);assert.equal(result.lon,point.lon);
  assert.equal(result.point_kind,'gap_registry');assert.equal(result.gap_id,'gap-sample');
  assert.equal(result.registry_district,'ท่าชนะ');assert.equal(result.district,'อ.ท่าชนะ');
  assert.equal(result.soil_code,'Bu');assert.equal(result.soil_properties.topsoil_ph,'กรดจัด');
  assert.match(result.note,/ยังไม่ยืนยันภาคสนาม/);assert.match(result.note,/ผลผลิตยังเป็นระดับจังหวัด/);
});
test('missing soil or district conflicts never borrow a provincial soil or reference position',()=>{
  const missing=helpers.preparePoint(point,provinces,districts,[]);
  assert.equal(missing.soil_code,undefined);assert.equal(missing.soil_match_status,'not_mapped');
  const conflict=helpers.preparePoint({...point,district:'อื่น'},provinces,districts,[feature]);
  assert.equal(conflict.soil_code,undefined);assert.equal(conflict.soil_match_status,'district_conflict');
  assert.equal(conflict.lat,point.lat);assert.equal(conflict.district,'');
  const other={...feature,properties:{...feature.properties,soil_code:'Other'}};
  assert.equal(helpers.soilAtPoint([feature,other],99.5,9.5).status,'ambiguous');
});
test('invalid or unrecognized GAP pins cannot be selected',()=>{
  for(const change of [{lat:null},{lon:NaN},{code:'00'},{gap_id:''},{lat:99.5,lon:9.5}])assert.throws(()=>helpers.preparePoint({...point,...change},provinces,districts,[]));
});

test('weather export keeps GAP identity and snapshot beside real source coordinates',()=>{
  const report=fs.readFileSync(path.join(__dirname,'../web/assets/js/orchard_monthly_report.js'),'utf8');
  const code=report.slice(report.indexOf('function weatherCsv('),report.indexOf('downloadWeather.onclick'));
  const csv=new Function('chartMetrics',code+';return weatherCsv;')({T2M:[]})({a:{...point,point_kind:'gap_registry'},b:null,resultA:{rows:[{date:'2025-01-01',T2M:27}],dataLat:9.5,dataLon:99.5,basis:'selected_point'},resultB:null});
  assert.match(csv,/"point_kind","gap_id","gap_snapshot_date","coordinate_quality"/);
  assert.match(csv,/"gap_registry","gap-sample","2026-10-20"/);
});
