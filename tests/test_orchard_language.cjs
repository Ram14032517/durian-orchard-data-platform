const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const{createRequire}=require('node:module');const req=createRequire(path.resolve('web/react/package.json'));const{buildSync}=req('esbuild');
function language(initial){const memory=new Map(initial?[['durian.orchard.language.v1',initial]]:[]),document={documentElement:{lang:'th'}},window={localStorage:{getItem:k=>memory.get(k),setItem:(k,v)=>memory.set(k,v)},addEventListener(){}};const module={exports:{}};const code=buildSync({entryPoints:['web/i18n/language.js'],bundle:true,write:false,format:'cjs',platform:'node'}).outputFiles[0].text;class MutationObserver{observe(){}disconnect(){}}vm.runInNewContext(code,{module,exports:module.exports,window,document,console,MutationObserver});return {...module.exports,document,memory};}
test('language defaults to English, respects stored Thai, reverses and persists without transforming data',()=>{
 const l=language();assert.equal(l.getLanguage(),'en');assert.equal(l.text('สวนของฉัน'),'My orchard');
 l.setLanguage('th');assert.equal(l.text('สวนของฉัน'),'สวนของฉัน');
 let changes=0;const unsub=l.subscribeLanguage(()=>changes++);
 l.setLanguage('en');assert.equal(l.text('สวนของฉัน'),'My orchard');
 assert.equal(l.document.documentElement.lang,'en');assert.equal(l.locale(),'en-GB');
 assert.equal(l.memory.get('durian.orchard.language.v1'),'en');
 assert.equal(l.text(1300),1300);assert.equal(l.text('https://example.com/สวน'),'https://example.com/สวน');
 l.setLanguage('th');assert.equal(l.text('สวนของฉัน'),'สวนของฉัน');assert.equal(changes,2);
 unsub();l.setLanguage('xx');assert.equal(l.getLanguage(),'th');
 assert.equal(language('th').getLanguage(),'th');assert.equal(language('en').text('สวนของฉัน'),'My orchard');
 assert.equal(language('invalid').getLanguage(),'en');
});
test('translation preserves explicit and implicit option values, form state and original evidence',()=>{const l=language('en');const a=l.translatedProps('option',{children:'สุราษฎร์ธานี'});assert.equal(a.value,'สุราษฎร์ธานี');assert.notEqual(a.children,'สุราษฎร์ธานี');const b=l.translatedProps('option',{children:'สุราษฎร์ธานี',value:'84'});assert.equal(b.value,'84');const input=l.translatedProps('input',{value:'ผลผลิต',placeholder:'จังหวัด'});assert.equal(input.value,'ผลผลิต');assert.equal(l.translatedProps('span',{'data-source-original':true,children:'ผลผลิต'}).children,'ผลผลิต');});
test('header replaces snapshot with language control and navigation retains visited pages',()=>{const s=fs.readFileSync('web/react/src/main.jsx','utf8');assert.ok(s.includes('<LanguageControl/>'));assert.ok(s.includes('<Home go={go} language={language}/>'));assert.ok(!s.includes('GAP Snapshot'));for(const page of ['weather','yield','seasons'])assert.ok(s.includes(`visited.has('${page}')`));const i=fs.readFileSync('web/i18n/language.js','utf8');assert.ok(!i.includes('observe(document.body)'));assert.ok(!i.includes('fetch('));});

test('new journal controls and validation messages have complete English translations and preserve submitted values',()=>{
 const l=language('en');
 for(const label of ['บันทึกสวน','บันทึกสวนและปฏิทิน','ใส่ปุ๋ย','สถานะกิจกรรม','ระยะการผลิตที่บันทึก','รายละเอียดที่สังเกต / สิ่งที่ทำ','ปีปฏิทิน','กิจกรรมที่ทำแล้วต้องไม่เป็นวันที่ในอนาคต','โหลดแผนที่ไม่ได้ ตรวจอินเทอร์เน็ตแล้วลองใหม่']){
  assert.notEqual(l.text(label),label);assert.ok(!/[\u0e00-\u0e7f]/.test(l.text(label)));
 }
 assert.equal(l.translatedProps('option',{value:'planned',children:'วางแผน'}).value,'planned');
 assert.equal(l.translatedProps('input',{value:'บันทึกสวนของฉัน'}).value,'บันทึกสวนของฉัน');
 const raw=l.translatedProps('h3',{'data-source-original':true,children:'ให้น้ำ'});
 assert.equal(raw.children,'ให้น้ำ');
 l.setLanguage('th');assert.equal(l.text('บันทึกสวนและปฏิทิน'),'บันทึกสวนและปฏิทิน');
});

test('external GAP inputs translate labels and placeholders, keep values, and restore Thai',()=>{
 const l=language('en'),attributes={placeholder:'ค้นรหัสแสดงผล อำเภอ หรือตำบล','aria-label':'ค้นหาหมุด GAP ในจังหวัดที่เลือก'};
 const input={nodeType:1,tagName:'INPUT',childNodes:[],value:'ชื่อสวนที่ผู้ใช้พิมพ์',matches:()=>false,hasAttribute:k=>k in attributes,getAttribute:k=>attributes[k],setAttribute:(k,v)=>attributes[k]=v};
 const stop=l.observeExternalLanguage(input);
 assert.ok(!/[\u0e00-\u0e7f]/.test(attributes.placeholder));
 assert.ok(!/[\u0e00-\u0e7f]/.test(attributes['aria-label']));
 assert.equal(input.value,'ชื่อสวนที่ผู้ใช้พิมพ์');
 l.setLanguage('th');assert.equal(attributes.placeholder,'ค้นรหัสแสดงผล อำเภอ หรือตำบล');stop();
});

test('system copy in React source has English coverage, including expanded measurement explanations',()=>{
 const l=language('en'),missing=[];
 for(const file of fs.readdirSync('web/react/src').filter(f=>/\.(jsx|js)$/.test(f))){
  const source=fs.readFileSync('web/react/src/'+file,'utf8');
  for(const match of source.matchAll(/(['"])((?:\\.|(?!\1)[^\r\n\\])*?)\1/g)){
   const value=match[2];
   if(!/[\u0e00-\u0e7f]/.test(value)||/^https?:\/\//.test(value)||value===' น. (เวลาไทย)')continue;
   if(/[\u0e00-\u0e7f]/.test(l.text(value)))missing.push(file+': '+value);
  }
 }
 assert.deepEqual(missing,[]);
});

test('built page references the current JavaScript content hash',()=>{
 const crypto=require('node:crypto'),hash=crypto.createHash('sha256').update(fs.readFileSync('research_data/five_province_history/orchard_app.js')).digest('hex').slice(0,12);
 assert.ok(fs.readFileSync('research_data/five_province_history/UNIFIED_MAP.html','utf8').includes('orchard_app.js?v='+hash));
});
