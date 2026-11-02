import React,{useEffect,useState} from 'react';
import {data} from './data.js';
import {useResource} from './api.js';
import {ResourceStatus,Button} from './ui.jsx';

let leafletPromise;
function leaflet(){
  if(window.L)return Promise.resolve();
  if(!leafletPromise)leafletPromise=new Promise((resolve,reject)=>{
    const script=document.createElement('script');
    script.src='https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js';script.async=true;
    const fail=()=>{clearTimeout(timer);leafletPromise=null;script.remove();reject(new Error('โหลดแผนที่ไม่ได้ ตรวจอินเทอร์เน็ตแล้วลองใหม่'));};
    const timer=setTimeout(fail,15000);
    script.onload=()=>{clearTimeout(timer);if(window.L)resolve();else fail();};
    script.onerror=fail;
    document.head.appendChild(script);
  });
  return leafletPromise;
}

export default function DeferredData({group,children}){
  const deferred=data._deferred?.includes(group);
  const resource=useResource(deferred?'/api/dashboard-data/'+group:null);
  const [ready,setReady]=useState(!deferred&&group!=='map'),[error,setError]=useState(null),[retry,setRetry]=useState(0);
  useEffect(()=>{
    let active=true;
    if(deferred&&!resource.data)return;
    if(deferred)Object.assign(data,resource.data);
    setError(null);
    (group==='map'?leaflet():Promise.resolve()).then(()=>{if(active)setReady(true);}).catch(e=>{if(active)setError(e);});
    return()=>{active=false;};
  },[group,deferred,resource.data,retry]);
  if(!ready)return <section className="card" aria-live="polite"><p>กำลังเตรียมข้อมูลสำหรับหน้านี้…</p><ResourceStatus resource={resource}/>{error&&<div role="alert"><p>{error.message}</p><Button onClick={()=>setRetry(v=>v+1)}>ลองใหม่</Button></div>}</section>;
  return children;
}
