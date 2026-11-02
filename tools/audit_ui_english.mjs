/* Inventory presentation strings without executing application or data code. */
import {createRequire} from 'node:module';
import {readFileSync,readdirSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,relative} from 'node:path';
import vm from 'node:vm';
const root=resolve(import.meta.dirname,'..');
const req=createRequire(resolve(root,'web/react/package.json'));
const {buildSync,transformSync}=req('esbuild');
const module={exports:{}};
vm.runInNewContext(buildSync({entryPoints:[resolve(root,'web/i18n/english.js')],bundle:true,write:false,format:'cjs',platform:'node',logLevel:'silent'}).outputFiles[0].text,{module,exports:module.exports});
const english=module.exports.text;
const thai=/[\u0e00-\u0e7f]/;
const files=['web/react/src','web/assets/js'].flatMap(folder=>readdirSync(resolve(root,folder)).filter(name=>/\.(jsx|js)$/.test(name)&&name!=='soilTgImage.js').map(name=>folder+'/'+name));
files.push('web/templates/unified_orchard_map.html','web/templates/unified_orchard_react.html','tools/serve_orchard_cloud.py');
const apiSources=['tools/serve_orchard_analysis.py','tools/supabase_orchard.py','tools/orchard_harvest.py','tools/orchard_forecast.py','tools/orchard_current_context.py','tools/orchard_private_assets.py'];
files.push(...apiSources);
const literalContext=vm.createContext({});
function literals(code){return [...code.matchAll(/(['"])(?:\\[^]|(?!\1)[^\\\r\n])*\1/g)].flatMap(match=>{try{const value=vm.runInContext(match[0],literalContext,{timeout:100});return typeof value==='string'?[value]:[];}catch{return [];}});}
function displayParts(value){
  if(!value.includes('<')&&!/^["']?>/.test(value))return [value];
  const attributes=[...value.matchAll(/(?:aria-label|title|placeholder|alt)=["']([^"']*)["']/g)].map(match=>match[1]);
  return attributes.concat(value.replace(/<[^>]*>/g,'\n').replace(/^["']?>/,'').split('\n'));
}
const inventory={};
for(const name of files){
  const raw=readFileSync(resolve(root,name),'utf8');
  let strings;
  if(apiSources.includes(name))strings=literals(raw);
  else if(name.endsWith('.html')||name.endsWith('.py')){
    const html=name.endsWith('.py')?raw.match(/LOGIN_PAGE='''([^]*?)'''/)[1]:raw;
    strings=displayParts(html.replace(/<script\b[^>]*>[^]*?<\/script>/gi,'').replace(/<style\b[^>]*>[^]*?<\/style>/gi,''));
    for(const match of html.matchAll(/<script\b[^>]*>([^]*?)<\/script>/gi))strings.push(...literals(transformSync(match[1],{supported:{'template-literal':false},charset:'utf8'}).code).flatMap(displayParts));
    if(name.endsWith('.py'))strings.push(...literals(raw.replace(/LOGIN_PAGE='''[^]*?'''/,'')));
  }else{
    const compiled=transformSync(raw,{loader:name.endsWith('.jsx')?'jsx':'js',jsx:'automatic',supported:{'template-literal':false},charset:'utf8'}).code;
    strings=literals(compiled).flatMap(displayParts);
  }
  const missing=[...new Set(strings.map(value=>value.replace(/\s+/g,' ').trim()).filter(value=>!/^https?:\/\//.test(value)&&thai.test(value)&&thai.test(english(value))))];
  if(missing.length)inventory[name]=missing;
}
const folder=resolve(root,'.build');mkdirSync(folder,{recursive:true});
// Audit the display vocabulary without changing any embedded source records.
const html=readFileSync(resolve(root,'research_data/five_province_history/UNIFIED_MAP.html'),'utf8');
const data=JSON.parse(html.match(/const DATA=([^]*?);window\.__ORCHARD_DATA__/)[1]);
const dataStrings=[];
const displayKeys=new Set(['title','locator','scope','method','label','short','description','check','range','note','kind','summary']);
function collect(value){if(Array.isArray(value))value.forEach(collect);else if(value&&typeof value==='object')for(const [key,item]of Object.entries(value)){if(typeof item==='string'&&displayKeys.has(key))dataStrings.push(item);else if(typeof item==='object')collect(item);}}
collect(data.phenology);
for(const soil of data.soil_properties)for(const key of ['topsoil_texture','topsoil_ph','fertility','source'])if(typeof soil[key]==='string')dataStrings.push(soil[key]);
const manifest=JSON.parse(readFileSync(resolve(root,'research_data/five_province_history/gap_orchards/manifest.json'),'utf8'));
dataStrings.push(...manifest.warnings,...Object.values(manifest.sources).map(source=>source.title));
const dataMissing=[...new Set(dataStrings.filter(value=>thai.test(english(value))))];
if(dataMissing.length)inventory['display-data/phenology-soil-gap-notes']=dataMissing;
writeFileSync(resolve(folder,'ui_language_inventory.json'),JSON.stringify(inventory,null,2)+'\n');
const count=Object.values(inventory).reduce((sum,items)=>sum+items.length,0);
console.log(JSON.stringify({untranslatedStaticStrings:count,files:Object.fromEntries(Object.entries(inventory).map(([name,items])=>[name,items.length])),inventory:relative(root,resolve(folder,'ui_language_inventory.json'))}));
if(process.argv.includes('--check')&&count)process.exitCode=1;
