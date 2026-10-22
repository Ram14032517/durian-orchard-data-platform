// Registry positions select A/B; mapped soil is context, never a field measurement.
const gapSpatialHelpers=(()=>{
  function ringLocation(lon,lat,ring){
    let inside=false;
    for(let i=0,j=ring.length-1;i<ring.length;j=i++){
      const [xi,yi]=ring[i],[xj,yj]=ring[j];
      const cross=(lon-xi)*(yj-yi)-(lat-yi)*(xj-xi);
      if(Math.abs(cross)<1e-10&&lon>=Math.min(xi,xj)-1e-10&&lon<=Math.max(xi,xj)+1e-10&&lat>=Math.min(yi,yj)-1e-10&&lat<=Math.max(yi,yj)+1e-10)return 2;
      if((yi>lat)!==(yj>lat)&&lon<(xj-xi)*(lat-yi)/(yj-yi)+xi)inside=!inside;
    }
    return inside?1:0;
  }
  function inPolygon(lon,lat,rings){
    if(!rings.length||!ringLocation(lon,lat,rings[0]))return false;
    return !rings.slice(1).some(ring=>ringLocation(lon,lat,ring)===1);
  }
  function pointInGeometry(lon,lat,geometry){
    if(!Number.isFinite(lon)||!Number.isFinite(lat)||!geometry)return false;
    if(geometry.type==='Polygon')return inPolygon(lon,lat,geometry.coordinates);
    if(geometry.type==='MultiPolygon')return geometry.coordinates.some(rings=>inPolygon(lon,lat,rings));
    return false;
  }
  function soilAtPoint(features,lon,lat){
    const matches=features.filter(feature=>pointInGeometry(lon,lat,feature.geometry));
    const units=new Map(matches.map(feature=>[feature.properties.district+'|'+feature.properties.soil_code,feature.properties]));
    if(units.size!==1)return {properties:null,status:units.size?'ambiguous':'not_mapped'};
    return {properties:units.values().next().value,status:'mapped_not_field_measured'};
  }
  function districtKey(value){return String(value||'').normalize('NFC').replace(/^(?:อำเภอ|อ\.)\s*/,'').replace(/\s+/g,'');}
  function preparePoint(point,provinces,districts,soilFeatures){
    const province=provinces.find(row=>row.province_code===String(point.code));
    if(!province||!Number.isFinite(point.lat)||!Number.isFinite(point.lon)||point.lat<5||point.lat>21||point.lon<97||point.lon>106||!point.gap_id)throw Error('ข้อมูลพิกัด GAP ไม่ถูกต้อง');
    const registryDistrict=point.registry_district||point.district||'';
    const district=districts.find(row=>row.province_code===point.code&&districtKey(row.district)===districtKey(registryDistrict));
    const soil=soilAtPoint(soilFeatures||[],point.lon,point.lat);
    const soilDistrict=soil.properties?.district;
    const consistent=!!soil.properties&&(!registryDistrict||districtKey(soilDistrict)===districtKey(registryDistrict));
    const soilNote=soil.status==='ambiguous'?'ทับซ้อนหลายหน่วยดิน จึงยังไม่เลือกหน่วยดิน':soil.properties&&!consistent?'ชื่ออำเภอในทะเบียนกับชั้นดินไม่ตรงกัน จึงยังไม่กำหนดหน่วยดิน':consistent?'ดินจับคู่จากตำแหน่งในแผนที่ LDD 2561 ไม่ใช่ผลตรวจดินในสวน':'ยังไม่พบหน่วยดินที่จับคู่ตำแหน่งได้';
    return {...point,code:String(point.code),point_kind:'gap_registry',registry_district:registryDistrict,
      district:district?.district||'',soil_code:consistent?soil.properties.soil_code:undefined,
      soil_properties:consistent?{...soil.properties}:undefined,soil_match_status:consistent?soil.status:soil.properties?'district_conflict':soil.status,
      label:province.province_name+' / แปลง GAP '+point.gap_id,
      note:'พิกัดตามทะเบียน GAP ยังไม่ยืนยันภาคสนาม · ทะเบียน ณ '+(point.gap_snapshot_date||'ไม่ระบุ')+' · '+soilNote+' · อากาศเป็นข้อมูลกริด ผลผลิตยังเป็นระดับจังหวัด'};
  }
  return {pointInGeometry,soilAtPoint,districtKey,preparePoint};
})();

function selectGapRegistryPoint(point){
  const which=activeArea,selection=gapSpatialHelpers.preparePoint(point,DATA.provinces,DATA.districts,soilCache[point.code]?.features);
  syncAreaControls(selection,which);selectArea(selection,which);updateMapTarget(which);
  if($('gap-open-weather'))$('gap-open-weather').hidden=false;
  if(which==='B')$('comparison-controls').open=true;
  if(typeof mapMotion!=='undefined')mapMotion.setView([selection.lat,selection.lon],Math.max(14,map.getZoom()));
  else map.setView([selection.lat,selection.lon],Math.max(13,map.getZoom()),{animate:false});
  if(soilCache[point.code])return;
  // A slow soil response may enrich this same pin, never overwrite a later choice.
  fetch('../priority_provinces/soil_layers/'+encodeURIComponent(point.code)+'.geojson')
    .then(response=>{if(!response.ok)throw Error('soil layer unavailable');return response.json();})
    .then(data=>{
      soilCache[point.code]=data;
      if((which==='B'?B:A)!==selection)return;
      Object.assign(selection,gapSpatialHelpers.preparePoint(point,DATA.provinces,DATA.districts,data.features));
      syncAreaControls(selection,which);selectArea(selection,which);
    }).catch(()=>{ /* Missing mapped soil does not turn province soil into orchard data. */ });
}
