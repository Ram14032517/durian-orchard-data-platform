import React,{useCallback,useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {AuthProvider,AccountControl} from './Auth.jsx';
import ThemeControl from './ThemeControl.jsx';
import {useResource} from './api.js';
import Home from './Home.jsx';
import MapPage from './MapPage.jsx';
import Weather from './Weather.jsx';
import {YieldPage,Seasons} from './Reports.jsx';
import {data,provincePoint} from './data.js';
import {Icon,Button,Notice} from './ui.jsx';
const pages=[['home','สวนของฉัน','leaf'],['map','แผนที่ / GAP','map'],['weather','สภาพอากาศ','sun'],['yield','ผลผลิต','chart'],['seasons','ฤดูกาล','calendar']];
function currentPage(){return [location.hash.slice(1),location.pathname.slice(1)].find(id=>pages.some(p=>p[0]===id))||'home';}
const localTools=['localhost','127.0.0.1'].includes(location.hostname);
function LocalSourceNotice({page}){
  const runtime=useResource('/api/project');
  if(page!=='home'||runtime.data?.mode!=='local')return null;
  const snapshot=runtime.data.orchard_source==='local_snapshot';
  return <div className="mx-auto max-w-[1660px] px-4 sm:px-7 xl:px-9"><Notice>{snapshot?'โหมดในเครื่อง: snapshot ที่บันทึกไว้ ไม่ใช่ข้อมูลสดจากเว็บ cloud หากต้องการอ่านสดให้ตั้ง ORCHARD_DATA_SOURCE=supabase พร้อมการเชื่อมต่อฝั่งเซิร์ฟเวอร์':'ตั้งโหมดอ่าน Supabase ฝั่งเซิร์ฟเวอร์นี้ไว้แล้ว ตรวจสถานะและเวลาวัดด้านล่างเพื่อยืนยันความพร้อม ข้อมูลสวนไม่ย้ายตามพื้นที่ A/B'}{runtime.data.capabilities?.orchard?.configured===false?' · แหล่งข้อมูลสวนของเครื่องนี้ยังไม่พร้อม':''}</Notice></div>;
}
class Boundary extends React.Component{state={error:null};static getDerivedStateFromError(error){return {error};}render(){if(this.state.error)return <div className="card m-6"><h1 className="text-xl font-bold">หน้าเว็บมีข้อผิดพลาด</h1><p className="my-4">กรุณาโหลดหน้าใหม่ ข้อมูลที่บันทึกในฐานข้อมูลยังคงอยู่</p><Button onClick={()=>location.reload()}>โหลดหน้าใหม่</Button>{localTools&&<a href="UNIFIED_MAP_CLASSIC.html" className="ml-3 text-link">เปิดหน้าเดิม</a>}</div>;return this.props.children;}}
function App(){
  const [page,setPage]=useState(()=>currentPage()),[menu,setMenu]=useState(false),[collapsed,setCollapsed]=useState(false),[areas,setAreas]=useState({A:provincePoint('84'),B:null}),[range,setRange]=useState(null),[mapVisited,setMapVisited]=useState(currentPage()==='map'),[homeVisited,setHomeVisited]=useState(currentPage()==='home');
  const go=useCallback(id=>{if(!pages.some(p=>p[0]===id))return;setPage(id);setMenu(false);if(location.pathname!=='/'+id||location.hash)history.pushState(null,'','/'+id);window.scrollTo({top:0,behavior:'auto'});if(id==='map')setMapVisited(true);if(id==='home')setHomeVisited(true);},[]);
  useEffect(()=>{window.dispatchEvent(new Event('resize'));},[collapsed]);
  useEffect(()=>{const change=()=>{const id=currentPage();if(pages.some(p=>p[0]===id)){setPage(id);if(id==='map')setMapVisited(true);if(id==='home')setHomeVisited(true);}};window.addEventListener('hashchange',change);window.addEventListener('popstate',change);return()=>{window.removeEventListener('hashchange',change);window.removeEventListener('popstate',change);};},[]);
  useEffect(()=>{document.title=pages.find(p=>p[0]===page)?.[1]+' · Durian Orchard';if(location.pathname.endsWith('/UNIFIED_MAP.html'))history.replaceState(null,'','/'+page);const skip=document.querySelector('a[href$="#main-content"]');if(skip)skip.setAttribute('href','/'+page+'#main-content');},[page]);
  return <div className="app-shell min-h-screen">{menu&&<button className="fixed inset-0 z-[700] bg-slate-900/40 lg:hidden" aria-label="ปิดเมนู" onClick={()=>setMenu(false)}/>}
    <aside className={'sidebar '+(menu?'sidebar-open ':'')+(collapsed?'sidebar-compact':'')} aria-label="เมนูหลัก"><a href="#home" onClick={e=>{e.preventDefault();go('home');}} className="brand"><span className="brand-icon"><Icon name="durian" className="h-10 w-10"/></span><span className="sidebar-label">Durian<span className="block text-sm font-medium tracking-wider text-emerald-200">Orchard</span></span></a><button type="button" aria-label={collapsed?'ขยายแถบเมนู':'ย่อแถบเมนู'} aria-expanded={!collapsed} onClick={()=>setCollapsed(v=>!v)} className="mt-5 hidden min-h-11 items-center justify-center gap-2 rounded-xl border border-emerald-100/20 text-sm text-emerald-50 hover:bg-white/10 lg:flex"><Icon name="menu"/><span className="sidebar-label">ย่อเมนู</span></button><nav className="mt-5 grid gap-2" aria-label="หน้าหลัก 5 เมนู">{pages.map(([id,label,icon])=><button key={id} onClick={()=>go(id)} title={label} aria-label={label} aria-current={page===id?'page':undefined} className={'nav-item '+(page===id?'nav-active':'')}><Icon name={icon}/><span className="sidebar-label">{label}</span>{page===id&&<span className="sidebar-label ml-auto h-1.5 w-1.5 rounded-full bg-emerald-200"/>}</button>)}</nav><div className="mt-auto border-t border-emerald-100/15 pt-4"><AccountControl sidebar/></div></aside>
    <div className={collapsed?"lg:ml-[80px]":"lg:ml-[232px]"}><header className="app-header"><div className="flex min-w-0 flex-1 items-center gap-3"><button className="btn p-2 lg:hidden" aria-label="เปิดเมนู" onClick={()=>setMenu(v=>!v)}><Icon name="menu"/></button><div className="min-w-0"><p className="text-sm font-bold tracking-tight sm:text-lg">ระบบข้อมูลทุเรียน 5 จังหวัด</p><p className="mt-0.5 hidden text-[11px] text-slate-500 sm:block">ข้อมูลพื้นที่ อากาศ และผลผลิต เพื่อการศึกษาและการจัดการสวน</p></div></div><div className="flex shrink-0 items-center gap-3"><ThemeControl/><div className="hidden items-center gap-4 xl:flex"><span className="h-8 w-px bg-slate-200"/><span className="text-xs text-slate-500">GAP Snapshot<br/><b className="text-slate-700">20 ต.ค. 2569</b></span><Button onClick={()=>go('map')}><Icon name="pin"/>ค้นหาหมุด GAP</Button></div></div></header>
      <LocalSourceNotice page={page}/>
      <main id="main-content" tabIndex={-1} className="mx-auto max-w-[1660px] px-4 py-6 sm:px-7 sm:py-8 xl:px-9"><div className={page==='home'?'':'hidden'}>{homeVisited&&<Home go={go}/>}</div>{mapVisited&&<div hidden={page!=='map'}><MapPage areas={areas} setAreas={setAreas} active={page==='map'} go={go}/></div>}{page==='weather'&&<Weather areas={areas} requestedRange={range}/ >}{page==='yield'&&<YieldPage areas={areas} setAreas={setAreas}/ >}{page==='seasons'&&<Seasons areas={areas} setAreas={setAreas} goWeather={r=>{setRange(r);go('weather');}}/>}<footer className="mt-9 flex flex-wrap justify-between gap-3 border-t border-slate-200 pt-5 text-[11px] text-slate-500"><span>ข้อมูลคนละระดับไม่สามารถแทนกันได้ · Public Release HOLD</span>{localTools&&<a href="UNIFIED_MAP_CLASSIC.html" className="underline underline-offset-4">เครื่องมือเพิ่มเติมและหน้าอ้างอิงเดิม</a>}</footer></main>
    </div></div>;
}
createRoot(document.getElementById('orchard-react-root')).render(<Boundary><AuthProvider><App/></AuthProvider></Boundary>);
