import React,{useEffect,useState} from 'react';

export default function ThemeControl(){
  const [preference,setPreference]=useState(()=>window.OrchardTheme?.getPreference()||'system');
  useEffect(()=>window.OrchardTheme?.subscribe(state=>setPreference(state.preference)),[]);
  function change(event){
    const value=event.target.value;
    if(window.OrchardTheme?.setPreference(value))setPreference(value);
  }
  return <label className="theme-control"><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M12 3a9 9 0 1 0 0 18V3Zm0 0a9 9 0 0 1 0 18"/><path d="M12 3v18"/></svg><span className="sr-only">ธีมหน้าจอ</span><select aria-label="ธีมหน้าจอ" value={preference} onChange={change}><option value="system">ตามระบบ</option><option value="light">Light · สว่าง</option><option value="dark">Dark · มืด</option></select></label>;
}
