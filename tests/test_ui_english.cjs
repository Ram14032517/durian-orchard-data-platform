const test=require('node:test');
const assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const path=require('node:path');
const vm=require('node:vm');
const fs=require('node:fs');
const front=createRequire(path.resolve('web/react/package.json'));
const {buildSync}=front('esbuild'),React=front('react');
const {renderToStaticMarkup}=front('react-dom/server');
const runtime=path.resolve('web/react/src/i18n/jsx-runtime.js');
function load(file,extra={}){
  const code=buildSync({entryPoints:[file],bundle:true,write:false,format:'cjs',platform:'node',external:['react','react/jsx-runtime'],jsx:'automatic',jsxImportSource:'@orchard/i18n',alias:{'@orchard/i18n/jsx-runtime':runtime},logLevel:'silent'}).outputFiles[0].text;
  const module={exports:{}};
  vm.runInNewContext(code,{module,exports:module.exports,require:front,window:{__ORCHARD_DATA__:{provinces:[]}},Date,Intl,URLSearchParams,AbortController,console,setTimeout,clearTimeout,setInterval,clearInterval,...extra});
  return module.exports;
}
const en=load('web/i18n/english.js');
test('English presentation preserves raw form values, IDs, keys and source URLs',()=>{
  const raw={children:'สุราษฎร์ธานี',name:'province',id:'province-id',onChange(){}};
  const option=en.props('option',raw);
  assert.equal(option.children,'Surat Thani');assert.equal(option.value,'สุราษฎร์ธานี');
  assert.equal(option.name,raw.name);assert.equal(option.id,raw.id);assert.equal(option.onChange,raw.onChange);
  assert.equal(raw.children,'สุราษฎร์ธานี');assert.equal(raw.value,undefined);
  assert.equal(en.props('option',{children:'ติดผล',value:'young'}).value,'young');
  assert.equal(en.props('span',{'data-source-original':true,children:'สุราษฎร์ธานี'}).children,'สุราษฎร์ธานี');
  const uri='https://example.test/เอกสาร/ทุเรียน.pdf';assert.equal(en.text(uri),uri);
  assert.equal(en.props('input',{value:'ผู้ใช้กรอกเอง',placeholder:'เลือกจังหวัด'}).value,'ผู้ใช้กรอกเอง');
  assert.equal(en.text('  สุราษฎร์ธานี  '),'  Surat Thani  ');
  assert.equal(en.text('ฝน 24 ชม.'),'Rain 24 h');
  assert.equal(en.text('ชื่อเฉพาะต้นทางที่ไม่อยู่ในพจนานุกรม'),'ชื่อเฉพาะต้นทางที่ไม่อยู่ในพจนานุกรม');
});
test('production JSX renders English labels and still escapes hostile text',()=>{
  const {Metric}=load('web/react/src/ui.jsx');
  const html=renderToStaticMarkup(React.createElement(Metric,{label:'อุณหภูมิ',value:0,unit:'°C',note:'<script>unsafe</script>'}));
  assert.match(html,/Temperature/);assert.match(html,/>0<\/span>/);assert.doesNotMatch(html,/[\u0e00-\u0e7f]|<script>/);
});
test('production weather cards keep missing values and model/source caveats in English',()=>{
  const {CurrentWeather}=load('web/react/src/OrchardForecast.jsx');
  const html=renderToStaticMarkup(React.createElement(CurrentWeather,{forecast:{}}));
  assert.match(html,/Current values unavailable/);assert.match(html,/not a weather station or orchard sensor/);
  assert.match(html,/Missing values are not replaced with zero/);
  assert.doesNotMatch(html,/[\u0e00-\u0e7f]|>0<\/span>/);
});
test('production growth stage keeps source enum and all six steps, without guessing from month',()=>{
  const {OrchardStage}=load('web/react/src/Home.jsx');
  const html=renderToStaticMarkup(React.createElement(OrchardStage,{observation:{saved:{stage:'young',observed_at:'2026-01-01T00:00:00Z'},message:'',save(){}}}));
  assert.equal((html.match(/aria-current="step"/g)||[]).length,1);
  assert.equal((html.match(/<li /g)||[]).length,6);
  assert.match(html,/Fruit set/);assert.doesNotMatch(html,/[\u0e00-\u0e7f]/);
});
class Element{
  constructor(tag,attributes={},children=[]){this.nodeType=1;this.tagName=tag.toUpperCase();this.attributes={...attributes};this.childNodes=children;for(const child of children)child.parentElement=this;}
  matches(selector){return selector.split(',').some(s=>s==='[data-source-original]'?this.hasAttribute('data-source-original'):s.toUpperCase()===this.tagName);}
  closest(selector){return this.matches(selector)?this:this.parentElement?.closest(selector);}
  hasAttribute(k){return Object.hasOwn(this.attributes,k);}
  getAttribute(k){return this.attributes[k];}
  setAttribute(k,v){this.attributes[k]=String(v);}
  get value(){return this.attributes.value??this.childNodes.map(n=>n.nodeValue||'').join('');}
}
const textNode=value=>({nodeType:3,nodeValue:value});
test('legacy and Leaflet islands translate input accessibility attributes, never input values or original evidence',()=>{
  let observer,disconnected=false;
  class Observer{constructor(callback){this.callback=callback;observer=this;}observe(_root,options){this.options=options;}disconnect(){disconnected=true;}}
  const core=load('web/i18n/english.js',{MutationObserver:Observer});
  const option=new Element('option',{},[textNode('สุราษฎร์ธานี')]);
  const input=new Element('input',{'aria-label':'ค้นหาหมุด GAP ในจังหวัดที่เลือก',placeholder:'เลือกจังหวัด',value:'ข้อมูลผู้ใช้'});
  const original=new Element('p',{'data-source-original':''},[textNode('อุณหภูมิ')]);
  const script=new Element('script',{},[textNode('อุณหภูมิ')]);
  const textarea=new Element('textarea',{placeholder:'เลือกจังหวัด'},[textNode('ข้อมูลผู้ใช้')]);
  const root=new Element('div',{},[option,input,original,script,textarea]);
  const stop=core.observe(root);
  assert.equal(option.value,'สุราษฎร์ธานี');assert.equal(option.childNodes[0].nodeValue,'Surat Thani');
  assert.equal(input.getAttribute('aria-label'),'Search GAP points in the selected province');
  assert.equal(input.value,'ข้อมูลผู้ใช้');assert.equal(textarea.childNodes[0].nodeValue,'ข้อมูลผู้ใช้');
  assert.equal(original.childNodes[0].nodeValue,'อุณหภูมิ');assert.equal(script.childNodes[0].nodeValue,'อุณหภูมิ');
  const late=textNode('อุณหภูมิ');late.parentElement=root;observer.callback([{type:'childList',addedNodes:[late]}]);assert.equal(late.nodeValue,'Temperature');
  observer.callback([{type:'characterData',target:late}]);assert.equal(late.nodeValue,'Temperature');
  assert.ok(!observer.options.attributeFilter.includes('value'));stop();assert.equal(disconnected,true);
});
test('localization bootstrap never observes the React-owned body',()=>{
  let observers=0;
  const document={readyState:'complete',title:'อากาศ',documentElement:{},getElementById:()=>({}),body:new Element('body')};
  load('web/i18n/english.js',{document,MutationObserver:class{constructor(){observers++;}}});
  assert.equal(observers,0);assert.equal(document.documentElement.lang,'en');assert.equal(document.title,'Weather');
});
test('map transitions share cancellable navigation and resize cleanup, with reduced-motion CSS',()=>{
  const source=fs.readFileSync('web/react/src/MapPage.jsx','utf8');
  assert.match(source,/createOrchardMapMotion\.mapOptions/);assert.match(source,/selectionOwnsNavigation:true,motion/);
  assert.match(source,/resize\.disconnect\(\)/);assert.match(source,/motion\.destroy\(\)/);
  assert.doesNotMatch(source,/map\.stop\(\)\.setView|mapRef\.current\?\.fitBounds/);
  assert.match(fs.readFileSync('web/assets/css/orchard_motion.css','utf8'),/prefers-reduced-motion:\s*reduce/);
  const motion=fs.readFileSync('web/assets/css/orchard_motion.css','utf8');
  assert.doesNotMatch(motion,/animation:\s*orchard-view-in[^;]*both/);
  const frames=motion.match(/@keyframes orchard-view-in\s*\{(?:[^{}]|\{[^{}]*\})*\}/);
  assert.ok(frames);assert.doesNotMatch(frames[0],/transform:/);
});
