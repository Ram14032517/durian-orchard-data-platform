const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync('web/assets/js/orchard_theme.js','utf8');
const KEY='durian.orchard.theme.v1';
function start({saved=null,dark=false,blocked=false,legacy=false}={}){
  const store=new Map(saved===null?[]:[[KEY,saved]]),writes=[];
  const root=new EventTarget(),media=new EventTarget(),doc=new EventTarget();media.matches=dark;
  if(legacy){media.addListener=listener=>EventTarget.prototype.addEventListener.call(media,'change',listener);media.addEventListener=undefined;}
  doc.documentElement={dataset:{},style:{}};doc.querySelectorAll=()=>[];doc.querySelector=()=>null;doc.getElementById=()=>null;
  root.document=doc;root.CustomEvent=CustomEvent;root.matchMedia=()=>media;
  root.localStorage={getItem(key){if(blocked)throw Error('blocked');return store.get(key)??null;},setItem(key,value){if(blocked)throw Error('blocked');writes.push([key,value]);store.set(key,value);}};
  // Any attempt to transmit theme or touch an API is an error.
  root.fetch=()=>{throw Error('Theme must not request data');};
  vm.runInNewContext(code,{window:root});
  return {root,api:root.OrchardTheme,store,writes,changeSystem(value){media.matches=value;media.dispatchEvent(new Event('change'));},storage(key,value){const event=new Event('storage');Object.assign(event,{key,newValue:value});root.dispatchEvent(event);}};
}
test('first paint follows OS without writing a preference',()=>{
  const a=start({dark:true});assert.equal(a.api.getPreference(),'system');assert.equal(a.root.document.documentElement.dataset.theme,'dark');assert.equal(a.root.document.documentElement.style.colorScheme,'dark');assert.equal(a.writes.length,0);
  assert.equal(start().api.getTheme(),'light');
});
test('explicit light/dark is persisted and survives a new document',()=>{
  const a=start({dark:true});assert.equal(a.api.setPreference('light'),true);assert.equal(a.api.getTheme(),'light');
  assert.equal(start({saved:a.store.get(KEY),dark:true}).api.getTheme(),'light');
  a.api.setPreference('dark');assert.deepEqual(a.writes,[[KEY,'light'],[KEY,'dark']]);
});
test('invalid stored/input values cannot become DOM attributes or stored data',()=>{
  const a=start({saved:'<script>bad</script>'});assert.equal(a.api.getPreference(),'system');assert.equal(a.api.setPreference('anything'),false);assert.equal(a.writes.length,0);
});
test('storage denial still allows theme changes for the current page',()=>{
  const a=start({blocked:true});assert.equal(a.api.setPreference('dark'),true);assert.equal(a.api.getTheme(),'dark');assert.equal(a.writes.length,0);
});
test('OS changes only affect system mode, including older Safari listeners',()=>{
  for(const legacy of [false,true]){const a=start({legacy});a.changeSystem(true);assert.equal(a.api.getTheme(),'dark');a.api.setPreference('light');a.changeSystem(false);a.changeSystem(true);assert.equal(a.api.getTheme(),'light');a.api.setPreference('system');assert.equal(a.api.getTheme(),'dark');}
});
test('other tabs sync theme; unrelated storage entries never change it',()=>{
  const a=start();a.storage(KEY,'dark');assert.equal(a.api.getTheme(),'dark');a.storage('orchard-observations','light');assert.equal(a.api.getTheme(),'dark');a.storage(null,null);assert.equal(a.api.getPreference(),'system');assert.equal(a.writes.length,0);
});
test('subscriptions receive presentation-only state and can unsubscribe',()=>{
  const a=start(),events=[];const stop=a.api.subscribe(state=>events.push({...state}));a.api.setPreference('dark');stop();a.api.setPreference('light');
  assert.equal(events.length,1);assert.deepEqual(events[0],{preference:'dark',theme:'dark'});
});
test('React and classic initialise the theme before CSS without unresolved tokens',()=>{
  for(const name of ['UNIFIED_MAP.html','UNIFIED_MAP_CLASSIC.html']){const html=fs.readFileSync('research_data/five_province_history/'+name,'utf8');assert.ok(html.indexOf('durian.orchard.theme.v1')<html.indexOf('rel="stylesheet"'));assert.doesNotMatch(html,/__THEME_BOOTSTRAP__|__THEME_STYLE__/);}
  const css=fs.readFileSync('research_data/five_province_history/orchard_app.css','utf8');assert.match(css,/data-theme[=\s]/);assert.doesNotMatch(fs.readFileSync('web/assets/css/orchard_theme.css','utf8'),/filter\s*:\s*invert|\.leaflet-tile\s*\{/);
});
