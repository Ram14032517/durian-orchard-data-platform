import React,{useEffect,useState} from 'react';

export default function ThemeControl(){
  const [theme,setTheme]=useState(()=>window.OrchardTheme?.getTheme()||'light');
  useEffect(()=>window.OrchardTheme?.subscribe(state=>setTheme(state.theme)),[]);
  const dark=theme==='dark';
  return <button type="button" className="theme-control theme-toggle" aria-label="โหมดมืด" aria-pressed={dark} title={dark?'เปลี่ยนเป็นโหมดสว่าง':'เปลี่ยนเป็นโหมดมืด'} onClick={()=>window.OrchardTheme?.setPreference(dark?'light':'dark')}><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{dark?<path d="M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11Z"/>:<><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></>}</svg><span>{dark?'โหมดมืด':'โหมดสว่าง'}</span></button>;
}
