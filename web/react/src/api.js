import {useCallback,useEffect,useState} from 'react';
export async function api(url,options={}){
  const response=await fetch(url,{credentials:'same-origin',cache:'no-store',...options});
  if(!response.headers.get('content-type')?.includes('application/json')){const e=new Error('เซิร์ฟเวอร์ไม่ตอบข้อมูล กรุณาเปิดผ่าน 00_OPEN_REPORT.cmd');e.status=response.status;throw e;}
  const value=await response.json();if(!response.ok||value.error){const e=new Error(value.error||'อ่านข้อมูลไม่ได้');e.status=response.status;if(response.status===401&&url!=='/api/orchard-session'&&typeof window.dispatchEvent==='function')window.dispatchEvent(new Event('orchard:auth-required'));throw e;}return value;
}
// Each request has its own AbortController; changing a range cannot paint an old result.
export function useResource(url,interval=0,context=null){
  const [state,setState]=useState({data:null,error:null,loading:true});const [revision,setRevision]=useState(0);
  useEffect(()=>{if(!url){setState({data:null,error:null,loading:false});return;}let active=true,controller;
    const load=()=>{controller?.abort();controller=new AbortController();setState({data:null,loading:true,error:null});api(url,{signal:controller.signal}).then(data=>{if(active)setState({data,error:null,loading:false});}).catch(error=>{if(active&&error.name!=='AbortError')setState({data:null,error,loading:false});});};
    load();const timer=interval?setInterval(()=>{if(!document.hidden)load();},interval):null;
    return()=>{active=false;controller?.abort();if(timer)clearInterval(timer);};
  },[url,revision,interval,context]);
  const reload=useCallback(()=>setRevision(v=>v+1),[]);
  return {...state,reload};
}
