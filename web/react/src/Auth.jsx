import React,{createContext,useContext,useEffect,useRef,useState} from 'react';
import {useResource} from './api.js';
import {Button,Icon} from './ui.jsx';
const AuthContext=createContext(null);
export function loginHref(){return '/login?'+new URLSearchParams({next:location.pathname+location.hash});}
export function AuthProvider({children}){
  const session=useResource('/api/orchard-session');
  useEffect(()=>{const refresh=()=>session.reload();window.addEventListener('focus',refresh);window.addEventListener('orchard:auth-required',refresh);return()=>{window.removeEventListener('focus',refresh);window.removeEventListener('orchard:auth-required',refresh);};},[session.reload]);
  return <AuthContext.Provider value={session}>{children}</AuthContext.Provider>;
}
export const useAuth=()=>useContext(AuthContext);
export function AccountControl({sidebar=false}){
  const session=useAuth(),[open,setOpen]=useState(false),[busy,setBusy]=useState(false);const dialog=useRef(null),trigger=useRef(null);
  useEffect(()=>{if(open){dialog.current?.showModal();return()=>{dialog.current?.close();trigger.current?.focus();};}},[open]);
  useEffect(()=>{if(!session.data){setOpen(false);setBusy(false);}},[session.data]);
  if(session.loading)return <span className="text-xs text-slate-500" role="status">กำลังตรวจบัญชี…</span>;
  if(!session.data)return session.error?.status===401?<a className={sidebar?"sidebar-logout":"btn-primary"} aria-label="เข้าสู่ระบบ" href={loginHref()}><Icon name="user"/><span className={sidebar?"sidebar-label":""}>เข้าสู่ระบบ</span></a>:<Button onClick={session.reload}>ตรวจบัญชีอีกครั้ง</Button>;
  return <div className={sidebar?"sidebar-account":"flex items-center gap-2"}><span className={sidebar?"sidebar-label mb-2 block text-xs text-emerald-100":"hidden text-xs text-slate-500 sm:block"}>บัญชี <b className={sidebar?"text-white":"text-slate-700"}>{session.data.account}</b></span><button type="button" ref={trigger} className={sidebar?"sidebar-logout":"btn"} onClick={()=>setOpen(true)} aria-label={'ออกจากระบบบัญชี '+session.data.account}><Icon name="user"/><span className={sidebar?"sidebar-label":""}>ออกจากระบบ</span></button>
    {open&&<dialog ref={dialog} aria-labelledby="logout-title" onCancel={()=>setOpen(false)} className="auth-dialog"><div className="flex items-start gap-4"><span className="icon-box"><Icon name="user"/></span><div><h2 id="logout-title" className="text-lg font-bold">ออกจากระบบ?</h2><p className="mt-2 text-sm leading-relaxed text-slate-500">บัญชี {session.data.account} จะออกจากระบบในเบราว์เซอร์นี้ ข้อมูลที่บันทึกในฐานข้อมูลยังคงอยู่</p></div></div><form action="/logout" method="post" className="mt-6 flex justify-end gap-2" onSubmit={()=>setBusy(true)}><input type="hidden" name="csrf" value={session.data.csrf}/><Button onClick={()=>setOpen(false)} disabled={busy}>อยู่ในระบบต่อ</Button><button type="submit" className="btn-primary" disabled={busy}>{busy?'กำลังออกจากระบบ…':'ยืนยันออกจากระบบ'}</button></form></dialog>}
  </div>;
}
