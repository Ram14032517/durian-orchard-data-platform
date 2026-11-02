import React,{useEffect,useState} from 'react';

export default function ThemeControl(){
  const [theme,setTheme]=useState(()=>window.OrchardTheme?.getTheme()||'light');
  useEffect(()=>window.OrchardTheme?.subscribe(state=>setTheme(state.theme)),[]);
  function toggle(){
    const next=theme==='dark'?'light':'dark';
    if(window.OrchardTheme?.setPreference(next))setTheme(next);
  }
  return <button type="button" className="theme-control theme-toggle" data-mode={theme} aria-pressed={theme==='dark'} aria-label={'Mode: '+(theme==='dark'?'Dark':'Light')+'. Switch to '+(theme==='dark'?'light':'dark')+' mode'} title="Click to switch appearance" onClick={toggle}><svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6">{theme==='dark'?<path d="M20.5 13A8.6 8.6 0 0 1 11 3.5 8.8 8.8 0 1 0 20.5 13Z"/>:<><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></>}</svg><span className="mode-caption">Mode:</span><span className="mode-value">{theme==='dark'?'Dark':'Light'}</span></button>;
}
