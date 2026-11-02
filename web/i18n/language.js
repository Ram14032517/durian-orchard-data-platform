// Reuses the dictionary introduced in friend's commit 093daa9; presentation only.
import messages from './en.json';
const key='durian.orchard.language.v1';
let language='th';
try{if(window.localStorage.getItem(key)==='en')language='en';}catch{}
const listeners=new Set(),cache=new Map(),thai=/[\u0e00-\u0e7f]/;
const normalized=value=>value.replace(/\s+/g,' ').trim();
const exact=new Map(Object.entries(messages).map(([k,v])=>[normalized(k),v]));
let phrases;
export const getLanguage=()=>language;
export const locale=()=>language==='en'?'en-GB':'th-TH';
export const subscribeLanguage=listener=>{listeners.add(listener);return()=>listeners.delete(listener);};
export function setLanguage(value){
 if(!['th','en'].includes(value)||value===language)return;
 language=value;
 try{window.localStorage.setItem(key,value);}catch{}
 if(typeof document!=='undefined')document.documentElement.lang=value;
 listeners.forEach(listener=>listener());
}
if(typeof document!=='undefined')document.documentElement.lang=language;
if(typeof window!=='undefined'&&typeof window.addEventListener==='function')window.addEventListener('storage',e=>{if(e.key===key)setLanguage(e.newValue==='en'?'en':'th');});
export function text(value){
 if(language!=='en'||typeof value!=='string'||!thai.test(value)||/^https?:\/\//.test(value))return value;
 if(cache.has(value))return cache.get(value);
 let result=exact.get(normalized(value));
 if(result!==undefined)result=(value.match(/^\s*/)?.[0]||'')+result+(value.match(/\s*$/)?.[0]||'');
 else{
  // Compile only when English is actually used; keep the Thai startup path cheap.
  if(!phrases){const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');phrases=new RegExp('(^|[^\\u0e00-\\u0e7f])('+[...exact.keys()].sort((a,b)=>b.length-a.length).map(escape).join('|')+')(?=$|[^\\u0e00-\\u0e7f])','g');}
  result=value.replace(phrases,(_,prefix,phrase)=>prefix+exact.get(phrase));
 }
 if(cache.size>=2048)cache.delete(cache.keys().next().value);
 cache.set(value,result);return result;
}
export function translatedProps(type,input){
 if(!input)return input;
 const children=value=>typeof value==='string'?text(value):Array.isArray(value)?value.map(children):value;
 const original=typeof type==='string'&&Object.prototype.hasOwnProperty.call(input,'data-source-original');
 const out={...input,children:original?input.children:children(input.children)};
 if(typeof type==='string'){
  for(const attr of ['aria-label','aria-description','title','placeholder','alt','label'])if(typeof input[attr]==='string')out[attr]=text(input[attr]);
  if(type==='option'&&!Object.prototype.hasOwnProperty.call(input,'value')){const raw=Array.isArray(input.children)?input.children:[input.children];if(raw.every(v=>typeof v==='string'||typeof v==='number'))out.value=raw.join('');}
 }
 return out;
}

// Leaflet/GAP own these DOM subtrees. Never observe or mutate React-owned DOM.
export function observeExternalLanguage(element){
 if(!element||typeof MutationObserver==='undefined')return()=>{};
 const originals=new WeakMap(),attrs=new WeakMap();
 const skip='script,style,noscript,input,textarea,code,pre,[data-source-original]';
 function visit(node){
  if(node.nodeType===3){if(node.parentElement?.closest(skip))return;let saved=originals.get(node);if(!saved||node.nodeValue!==saved.last)saved={original:node.nodeValue};const next=text(saved.original);saved.last=next;originals.set(node,saved);if(node.nodeValue!==next)node.nodeValue=next;return;}
  // Inputs keep their entered values, but their labels and placeholders still need translation.
  if(node.nodeType!==1||node.matches('script,style,noscript,code,pre,[data-source-original]'))return;
  let saved=attrs.get(node);if(!saved){saved={};attrs.set(node,saved);}
  if(node.tagName==='OPTION'&&!node.hasAttribute('value'))node.setAttribute('value',node.value);
  for(const name of ['aria-label','aria-description','title','placeholder','alt','label']){if(!node.hasAttribute(name))continue;const current=node.getAttribute(name);if(!saved[name]||current!==saved[name].last)saved[name]={original:current};const next=text(saved[name].original);saved[name].last=next;if(current!==next)node.setAttribute(name,next);}
  node.childNodes.forEach(visit);
 }
 const refresh=()=>visit(element);refresh();const unsubscribe=subscribeLanguage(refresh);
 const observer=new MutationObserver(records=>{for(const r of records){if(r.type==='childList')r.addedNodes.forEach(visit);else visit(r.target);}});
 observer.observe(element,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['aria-label','title','placeholder','alt','label']});
 return()=>{unsubscribe();observer.disconnect();};
}
