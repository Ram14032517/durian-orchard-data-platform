"""Dependency-free GAP layer checks, including a small mocked DOM/Leaflet runtime."""
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'web/assets/js/orchard_gap_layer.js'
NODE = shutil.which('node')
if NODE is None:
    bundled = Path('/Users/abc/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node')
    NODE = str(bundled) if bundled.is_file() else None


@unittest.skipUnless(NODE, 'Node.js is needed for frontend contract checks')
class GapMapFrontendTests(unittest.TestCase):
    def run_js(self, script):
        result = subprocess.run(
            [NODE, '-e', script, str(SOURCE)], cwd=ROOT, text=True,
            capture_output=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_syntax(self):
        result = subprocess.run([NODE, '--check', str(SOURCE)], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_coordinates_filters_clusters_and_url_guards(self):
        self.run_js(r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const window = {};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), {window, URL});
const h = window.createGapOrchardLayer.helpers;
function feature(id, lon, lat, district='เมือง', date_status='within_dates', quality_flags=[]) {
  return {type:'Feature',id,properties:{id,province_code:'22',district,date_status,quality_flags},geometry:{type:'Point',coordinates:[lon,lat]}};
}
const a=feature('a',100,12), b=feature('b',100,12,'เมือง','expired',['shared_coordinate']), c=feature('c',101,13,'ท่าใหม่');
assert.equal(h.validFeature(a),true);
assert.equal(h.validFeature({...a,geometry:{type:'Point',coordinates:[null,12]}}),false);
assert.equal(h.validFeature({...a,geometry:{type:'Point',coordinates:['100',12]}}),false);
assert.equal(h.validFeature({...a,geometry:{type:'Point',coordinates:[100,95]}}),false);
assert.equal(h.filterFeatures([a,b,c],{district:'เมือง',dateStatus:'expired'}).length,1);
assert.equal(h.filterFeatures([a,b,c],{quality:'shared'})[0].id,'b');
assert.equal(h.filterFeatures([a,b,c],{quality:'no_additional_flags'}).length,2);
assert.equal(h.filterFeatures([a,b,c],{district:'ไม่พบ'}).length,0);
assert.equal(h.sourceUrl('javascript:alert(1)'),null);
assert.equal(h.sourceUrl('https://gap.doa.go.th.attacker.test/'),null);
assert.equal(h.sourceUrl('https://user:pass@gap.doa.go.th/'),null);
assert.equal(h.sourceUrl('https://gap.doa.go.th/'),'https://gap.doa.go.th/');
assert.equal(h.dataUrl('../gap/','province_22.geojson','https://example.test/report/UNIFIED_MAP.html'),'https://example.test/gap/province_22.geojson');
for (const filename of ['../../private.json','https://attacker.test/a','province_22.geojson?q=secret']) {
  assert.throws(()=>h.dataUrl('../gap/',filename,'https://example.test/report/UNIFIED_MAP.html'));
}
assert.throws(()=>h.dataUrl('../gap/','manifest.json','file:///Users/abc/report.html'));
const project=(lat,lon)=>({x:lon*100,y:lat*100});
const clusters=h.groupViewport([a,b,c],project,6);
assert.equal(clusters.length,2);
assert.equal(clusters.reduce((total,row)=>total+row.features.length,0),3);
const shared=clusters.find(row=>row.features.length===2);
assert.equal(shared.lon,100); assert.equal(shared.lat,12);
assert.equal(h.groupViewport([a,b,c],project,14).length,2,'identical registry coordinates stay selectable as a group at high zoom');
assert.ok(h.groupViewport(Array.from({length:35000},(_,i)=>feature('f'+i,100+(i%100)/10000,12+(i%90)/10000)),project,14).length<1200);
""")

    def test_lazy_province_selection_clicks_and_accessible_list(self):
        self.run_js(r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.attrs={};this.events={};this.style={};this.value='';this.hidden=false;this.classList={add:()=>{}};}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=[...nodes];}
  setAttribute(name,value){this.attrs[name]=String(value);}
  addEventListener(name,handler){this.events[name]=handler;}
  querySelector(tag){for(const child of this.children){if(child.tagName===tag)return child;const found=child.querySelector?.(tag);if(found)return found;}return null;}
  focus(){this.focused=true;}
}
const doc={baseURI:'https://orchard.test/report/UNIFIED_MAP.html',createElement(tag){return new Element(tag,this);},createTextNode(text){return {textContent:text};}};
const container=new Element('section',doc);
const markerGroups=[];
const map={zoom:6,panes:{},events:{},getPane(name){return this.panes[name];},createPane(name){return this.panes[name]={style:{}};},
  getZoom(){return this.zoom;},getBounds(){return {pad(){return this;},contains(){return true;}};},project([lat,lon]){return {x:lon*100,y:lat*100};},
  setView(position,zoom){this.position=position;this.zoom=zoom;},fitBounds(value){this.fitted=value;},on(name,handler){this.events[name]=handler;},off(name){delete this.events[name];},removeLayer(){}};
const L={canvas:()=>({}),layerGroup(){const group={layers:[],addTo(){return this;},clearLayers(){this.layers=[];},addLayer(layer){this.layers.push(layer);},removeLayer(layer){this.layers=this.layers.filter(item=>item!==layer);}};markerGroups.push(group);return group;},
  circleMarker(position,options){return {position,options,events:{},bindTooltip(node){assert.equal(typeof node,'object');return this;},on(name,handler){this.events[name]=handler;return this;},setStyle(style){Object.assign(this.options,style);},setRadius(radius){this.options.radius=radius;}};},DomEvent:{stopPropagation(event){event.stopped=true;}}};
function feature(id,code,lon,lat,district='เมือง',flags=[]){return {type:'Feature',id,geometry:{type:'Point',coordinates:[lon,lat]},properties:{id,province_code:code,province_name:code==='22'?'จันทบุรี':'ชุมพร',district,tambon:'ตัวอย่าง',date_status:'within_dates',quality:'province_checked',quality_flags:['registry_gps_unverified',...flags],source_ids:['DOA'],field_verified:false}};}
const features=[feature('gap-a','22',100,12,'เมือง',['shared_coordinate']),feature('gap-b','22',100,12,'เมือง',['shared_coordinate']),feature('gap-c','22',101,13,'ท่าใหม่')];
const manifest={schema_version:1,snapshot_date:'2026-10-20',provinces:[{code:'22',name:'จันทบุรี',file:'province_22.geojson',bbox:[100,12,101,13],source_rows:4,excluded_counts:{invalid:1}},{code:'86',name:'ชุมพร',file:'province_86.geojson',source_rows:1}],sources:{DOA:{url:'https://gap.doa.go.th/',retrieved_date:'2026-10-20'},unsafe:{url:'https://attacker.test/'}}};
const calls=[], selections=[];
const window={document:doc,location:{href:doc.baseURI},setTimeout,clearTimeout,fetch:async(url,options)=>{
  calls.push(url);assert.equal(options.credentials,'same-origin');
  return {ok:true,json:async()=>url.endsWith('manifest.json')?manifest:{type:'FeatureCollection',features:url.endsWith('province_22.geojson')?features:[feature('gap-d','86',99,10)]}};
}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,URL});
const api=window.createGapOrchardLayer({map,L,container,dataBaseUrl:'../gap/',selectPoint:point=>selections.push(point)});
const descendants=node=>[node,...node.children.flatMap(child=>child.children?descendants(child):[child])];
(async()=>{
  assert.equal(calls.length,0,'factory must not fetch all provinces');
  await api.setProvince('22');
  assert.equal(calls.length,2);assert.equal(api.getState().loadedCount,3);
  assert.equal(markerGroups[0].layers.length,2,'low-zoom same-pixel points cluster');
  const first=markerGroups[0].layers.find(marker=>marker.position[0]===12);
  const event={originalEvent:{}};first.events.click(event);assert.equal(event.originalEvent.stopped,true);
  const list=descendants(container).find(node=>node.tagName==='ol');
  assert.equal(list.children.length,2,'cluster click offers only the selected cluster in keyboard list');
  list.children[0].children[0].events.click();
  assert.equal(selections.length,1);assert.equal(selections[0].point_kind,'gap_registry');
  assert.equal(selections[0].code,'22');assert.equal(selections[0].gap_id,'gap-a');
  assert.equal(selections[0].lat,12);assert.equal(selections[0].lon,100);
  assert.equal(selections[0].soil_code,undefined,'registry location does not invent a soil unit');
  assert.equal(selections[0].coordinate_quality,'province_checked');
  await api.setProvince('22');assert.equal(api.getState().selectedId,'gap-a','A/B integration must preserve same-province selection');
  assert.equal(calls.length,2,'same province is cached');
  const district=descendants(container).find(node=>node.tagName==='select'&&node.attrs['aria-label']==='อำเภอของหมุด GAP');
  district.value='ท่าใหม่';district.events.change();assert.equal(api.getState().filteredCount,1);
  api.setVisible(false);assert.equal(markerGroups[0].layers.length,0);
  api.setVisible(true);assert.equal(markerGroups[0].layers.length,1);
  assert.ok(descendants(container).filter(node=>node.tagName==='a').every(node=>!node.href.includes('attacker')));
  await api.setProvince('86');assert.equal(api.getState().loadedCount,1);assert.equal(api.getState().filters.district,'');
  assert.equal(calls.length,3,'province switch loads one file, not all');
  await api.setProvince('');assert.equal(api.getState().loadedCount,0);assert.equal(markerGroups[0].layers.length,0);
  api.destroy();assert.equal(container.children.length,0);assert.equal(Object.keys(map.events).length,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
""")

    def test_registry_copy_and_rendering_are_explicit(self):
        source = SOURCE.read_text(encoding='utf-8')
        self.assertNotIn('innerHTML', source)
        self.assertNotIn('.bindPopup(', source)
        self.assertIn('bubblingMouseEvents: false', source)
        self.assertIn("L.canvas({pane: paneName", source)
        self.assertIn('ยังไม่ยืนยันภาคสนาม', source)
        self.assertIn('ไม่ใช่เซนเซอร์ IoT', source)
        self.assertIn('หมุดไม่ทำให้ผลผลิตจังหวัดกลายเป็นผลผลิตรายสวน', source)

    def test_world_clusters_retain_markers_and_coalesce_navigation(self):
        self.run_js(r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.events={};this.attrs={};this.style={};this.value='';this.classList={add(){}};}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=[...nodes];}
  setAttribute(name,value){this.attrs[name]=String(value);}
  addEventListener(name,handler){this.events[name]=handler;}
  querySelector(){return null;}
}
const doc={baseURI:'https://orchard.test/map/',createElement(tag){return new Element(tag,this);},createTextNode(text){return {textContent:text};}};
const container=new Element('section',doc), frames=new Map(), navigation=[];
let nextFrame=0, projectionCalls=0, creations=0, tooltipBindings=0, clears=0, boundsTests=0;
let contains=()=>true;
const map={zoom:6,panes:{},events:{},getPane(name){return this.panes[name];},createPane(name){return this.panes[name]={style:{}};},
  getZoom(){return this.zoom;},getBounds(){return {pad(){return this;},contains(position){boundsTests++;return contains(position);}};},
  project([lat,lon],zoom){projectionCalls++;assert.equal(zoom,Math.round(map.zoom));return {x:lon*100,y:lat*100};},
  latLngToContainerPoint(){throw new Error('viewport-relative pixels would make clusters jump while panning');},
  setView(){throw new Error('navigation must use supplied motion helper');},fitBounds(){throw new Error('navigation must use supplied motion helper');},
  on(name,handler){this.events[name]=handler;},off(name){delete this.events[name];},removeLayer(){}};
let group;
const L={canvas:()=>({}),layerGroup(){return group={layers:[],addTo(){return this;},clearLayers(){clears++;this.layers=[];},addLayer(layer){this.layers.push(layer);},removeLayer(layer){this.layers=this.layers.filter(item=>item!==layer);}};},
  divIcon(options){assert.equal(typeof options.html,'object','cluster count must be a safe DOM node, not HTML text');return options;},
  marker(position,options){const marker=this.circleMarker(position,options);marker.kind='cluster';return marker;},
  circleMarker(position,options){creations++;return {position,options,events:{},bindTooltip(){tooltipBindings++;return this;},on(name,handler){this.events[name]=handler;return this;},setStyle(style){Object.assign(this.options,style);},setRadius(radius){this.options.radius=radius;}};},DomEvent:{stopPropagation(){}}};
function feature(id,lon,lat){return {type:'Feature',id,geometry:{type:'Point',coordinates:[lon,lat]},properties:{province_code:'22',district:'เมือง',date_status:'within_dates',quality_flags:[]}};}
// The first two records share a world-grid cell, but not an exact coordinate.
const features=[feature('a',100.001,12),feature('b',100.2,12.01),feature('c',101,13)];
const manifest={schema_version:1,provinces:[{code:'22',name:'จันทบุรี',file:'province_22.geojson',bbox:[100,12,101,13]}],sources:{}};
const window={document:doc,location:{href:doc.baseURI},setTimeout,clearTimeout,
  requestAnimationFrame(fn){const id=++nextFrame;frames.set(id,fn);return id;},cancelAnimationFrame(id){frames.delete(id);},
  fetch:async url=>({ok:true,json:async()=>url.endsWith('manifest.json')?manifest:{type:'FeatureCollection',features}})};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,URL});
const api=window.createGapOrchardLayer({map,L,container,selectPoint(){},motion:{setView(...args){navigation.push(['setView',...args]);},fitBounds(...args){navigation.push(['fitBounds',...args]);}}});
const flush=()=>{const pending=[...frames.values()];frames.clear();pending.forEach(fn=>fn());};
(async()=>{
  await api.setProvince('22');
  assert.equal(group.layers.length,2);assert.equal(projectionCalls,3);
  const retained=group.layers.find(marker=>marker.position[0]<13), originalPosition=[...retained.position];
  assert.equal(retained.kind,'cluster');assert.equal(retained.options.keyboard,true);
  assert.ok(retained.options.title.includes('ยังไม่ยืนยันภาคสนาม'));
  assert.equal(retained.options.alt,retained.options.title);
  assert.equal(retained.options.icon.className,'gap-cluster-icon');
  assert.equal(retained.options.icon.html.className,'gap-cluster-number');
  assert.equal(retained.options.icon.html.textContent,Number(2).toLocaleString('th-TH'));
  assert.deepEqual(Array.from(retained.options.icon.iconSize),[36,36]);
  assert.equal(group.layers.find(marker=>marker.position[0]===13).kind,undefined,'single registry locations stay on canvas');
  const initialCreations=creations, initialBindings=tooltipBindings, initialClears=clears;
  // Only one member of the first cluster is inside the next viewport. Its
  // centroid, tooltip membership and marker identity must nevertheless stay put.
  contains=([lat,lon])=>lon<100.1;
  map.events.moveend();map.events.moveend();map.events.zoomend();
  assert.equal(frames.size,1,'navigation events must share a single animation frame');
  flush();
  assert.equal(group.layers.length,1);assert.equal(group.layers[0],retained);
  assert.deepEqual(Array.from(group.layers[0].position),originalPosition);
  assert.equal(projectionCalls,3,'panning must reuse world-pixel cluster geometry');
  assert.equal(creations,initialCreations);assert.equal(tooltipBindings,initialBindings);
  assert.equal(clears,initialClears,'panning must not clear the canvas layer');
  retained.events.click({});assert.equal(navigation.at(-1)[0],'fitBounds');
  const beforeZoomTests=boundsTests;
  map.events.moveend();assert.equal(frames.size,1);
  map.events.zoomstart();assert.equal(frames.size,0,'zoom cancels a pending redraw');
  map.zoom=7;map.events.moveend();
  await api.setProvince('22');
  assert.equal(projectionCalls,3);assert.equal(boundsTests,beforeZoomTests,'no regroup/culling during animated zoom');
  map.events.zoomend();map.events.moveend();assert.equal(frames.size,1);flush();
  assert.equal(projectionCalls,6,'new zoom geometry is computed only after animation settles');
  map.events.moveend();api.setVisible(false);assert.equal(frames.size,0);assert.equal(group.layers.length,0);
  api.setVisible(true);assert.equal(projectionCalls,6,'visibility toggle reuses cached cluster geometry');
  map.events.moveend();api.destroy();assert.equal(frames.size,0);assert.equal(Object.keys(map.events).length,0);
  assert.equal(group.layers.length,0);assert.equal(container.children.length,0);
  flush();assert.equal(group.layers.length,0,'destroyed layer cannot be resurrected by queued work');
})().catch(error=>{console.error(error);process.exitCode=1;});
""")

    def test_reduced_motion_and_late_province_response_do_not_resurrect_layer(self):
        self.run_js(r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Element {
  constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.events={};this.style={};this.value='';this.classList={add(){}};}
  append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=[...nodes];}
  setAttribute(){}addEventListener(name,fn){this.events[name]=fn;}querySelector(){return null;}
}
const doc={baseURI:'https://orchard.test/map/',createElement(tag){return new Element(tag,this);},createTextNode(text){return {textContent:text};}},container=new Element('section',doc);
const navigation=[],groups=[];
const map={panes:{},events:{},getPane(name){return this.panes[name];},createPane(name){return this.panes[name]={style:{}};},getZoom(){return 14;},getBounds(){return {pad(){return this;},contains(){return true;}};},
  project(){throw new Error('small high-zoom groups need no projection');},setView(...args){navigation.push(args);},fitBounds(){},on(name,fn){this.events[name]=fn;},off(name){delete this.events[name];},removeLayer(){}};
const L={canvas:()=>({}),layerGroup(){const group={layers:[],addTo(){return this;},clearLayers(){this.layers=[];},addLayer(marker){this.layers.push(marker);},removeLayer(marker){this.layers=this.layers.filter(item=>item!==marker);}};groups.push(group);return group;},
  circleMarker(){return {events:{},bindTooltip(){return this;},on(name,fn){this.events[name]=fn;return this;},setStyle(){},setRadius(){}};},DomEvent:{stopPropagation(){}}};
const one={type:'Feature',id:'a',geometry:{type:'Point',coordinates:[100,12]},properties:{province_code:'22',date_status:'within_dates',quality_flags:[]}};
let releaseProvince;
const window={document:doc,location:{href:doc.baseURI},setTimeout,clearTimeout,matchMedia(){return {matches:true};},fetch:async url=>({ok:true,json:async()=>url.endsWith('manifest.json')?{schema_version:1,provinces:[{code:'22',name:'จันทบุรี',file:'province_22.geojson'}],sources:{}}:await new Promise(resolve=>{releaseProvince=resolve;})})};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{window,URL});
(async()=>{
 const api=window.createGapOrchardLayer({map,L,container,selectPoint(){}}),pending=api.setProvince('22');
 while(!releaseProvince)await new Promise(resolve=>setTimeout(resolve,0));
 releaseProvince({type:'FeatureCollection',features:[one]});await pending;
 const walk=node=>[node,...node.children.flatMap(child=>child.children?walk(child):[])];
 const list=walk(container).find(node=>node.tagName==='ol');list.children[0].children[0].events.click();
 assert.equal(navigation[0][2].animate,false,'reduced-motion navigation must not animate');
 api.destroy();
 // A second instance is destroyed while its province file is in flight.
 releaseProvince=null;const delayed=window.createGapOrchardLayer({map,L,container,selectPoint(){}}),late=delayed.setProvince('22');
 while(!releaseProvince)await new Promise(resolve=>setTimeout(resolve,0));
 delayed.destroy();releaseProvince({type:'FeatureCollection',features:[one]});await late;
 assert.equal(container.children.length,0);assert.equal(groups.at(-1).layers.length,0);
 assert.equal(Object.keys(map.events).length,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
""")


if __name__ == '__main__':
    unittest.main()
