import messages from './en.json';

const thai=/[\u0e00-\u0e7f]/;
const normalized=value=>value.replace(/\s+/g,' ').trim();
const exact=new Map(Object.entries(messages).map(([key,value])=>[normalized(key),value]));
const escape=value=>value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const phrases=new RegExp('(^|[^\\u0e00-\\u0e7f])('+[...exact.keys()].sort((a,b)=>b.length-a.length).map(escape).join('|')+')(?=$|[^\\u0e00-\\u0e7f])','g');
const cache=new Map();
export function text(value){
  if(typeof value!=='string'||!thai.test(value)||/^https?:\/\//.test(value))return value;
  if(cache.has(value))return cache.get(value);
  const key=normalized(value);
  let result=exact.get(key);
  if(result!==undefined){
    result=(value.match(/^\s*/)?.[0]||'')+result+(value.match(/\s*$/)?.[0]||'');
  }else{
    result=value.replace(phrases,(_,prefix,phrase)=>prefix+exact.get(phrase));
  }
  if(cache.size>=2048)cache.delete(cache.keys().next().value);
  cache.set(value,result);return result;
}

export function children(value){
  if(typeof value==='string')return text(value);
  return Array.isArray(value)?value.map(children):value;
}

export function props(type,input){
  if(!input)return input;
  const original=typeof type==='string'&&Object.prototype.hasOwnProperty.call(input,'data-source-original');
  const output={...input,children:original?input.children:children(input.children)};
  if(typeof type==='string'){
    for(const key of ['aria-label','aria-description','title','placeholder','alt','label'])if(typeof input[key]==='string')output[key]=text(input[key]);
    // Translating an implicit option label must never change its submitted value.
    if(type==='option'&&!Object.prototype.hasOwnProperty.call(input,'value')){
      const raw=Array.isArray(input.children)?input.children:[input.children];
      if(raw.every(v=>typeof v==='string'||typeof v==='number'))output.value=raw.join('');
    }
  }
  return output;
}

const skip='script,style,noscript,textarea,input,code,pre,[data-source-original]';
const sealed='script,style,noscript,code,pre,[data-source-original]';
export function observe(element){
  if(!element||typeof MutationObserver==='undefined')return ()=>{};
  function node(item){
    if(item.nodeType===3){if(item.parentElement&&!item.parentElement.closest(skip)){const before=item.nodeValue,after=text(before);if(before!==after)item.nodeValue=after;}return;}
    if(item.nodeType!==1||item.matches(sealed))return;
    if(item.tagName==='OPTION'&&!item.hasAttribute('value'))item.setAttribute('value',item.value);
    for(const attribute of ['aria-label','aria-description','title','placeholder','alt','label'])if(item.hasAttribute(attribute)){
      const before=item.getAttribute(attribute),after=text(before);if(before!==after)item.setAttribute(attribute,after);
    }
    if(!item.matches('input,textarea'))for(const child of item.childNodes)node(child);
  }
  node(element);
  const observer=new MutationObserver(records=>{
    for(const record of records){
      if(record.type==='childList')for(const added of record.addedNodes)node(added);
      else node(record.target);
    }
  });
  observer.observe(element,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['aria-label','aria-description','title','placeholder','alt','label']});
  return ()=>observer.disconnect();
}

export function installClassic(){
  document.documentElement.lang='en';
  document.title=text(document.title);
  // Never mutate React-owned DOM. React uses the JSX adapter below instead.
  if(!document.getElementById('orchard-react-root'))observe(document.body);
}
if(typeof document!=='undefined'){
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',installClassic,{once:true});
  else installClassic();
}
