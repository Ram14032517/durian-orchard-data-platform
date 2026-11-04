import React,{useEffect,useMemo,useState} from 'react';
import {api,useResource} from './api.js';
import {useAuth} from './Auth.jsx';
import {today,format,dateTime} from './data.js';
import {activityKinds,activityStages,activityUnits,monthDays,shiftMonth} from './activityData.js';
import {Button,Card,Field,Icon,Notice,ResourceStatus} from './ui.jsx';
import {locale,text} from '../../i18n/language.js';

const kindName=k=>activityKinds.find(v=>v[0]===k)?.[1]||k;
const stageName=k=>activityStages.find(v=>v[0]===k)?.[1]||'ยังไม่ระบุ';
const blank=(day,kind='water')=>({id:crypto.randomUUID(),orchard_code:'sensor-orchard-v1',activity_date:day,kind,
  production_stage:kind==='stage'?'recovery':null,stage_context:{},status:day>today()?'planned':'done',
  title:kindName(kind),_automaticTitle:true,notes:'',amount:'',unit:''});
export default function OrchardJournal(){
  const session=useAuth(),[month,setMonth]=useState(()=>today().slice(0,7)),[day,setDay]=useState(today),
    [form,setForm]=useState(null),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  const records=useResource(session.data?'/api/orchard-activities?'+new URLSearchParams({month}):null,0,session.data?.account);
  const currentLocale=locale();
  const monthLabels=useMemo(()=>{const f=new Intl.DateTimeFormat(currentLocale,{month:'short',timeZone:'Asia/Bangkok'});return Array.from({length:12},(_,i)=>f.format(new Date(Date.UTC(2026,i,1,12))));},[currentLocale]);
  const weekdayLabels=useMemo(()=>{const f=new Intl.DateTimeFormat(currentLocale,{weekday:'short',timeZone:'Asia/Bangkok'});return Array.from({length:7},(_,i)=>f.format(new Date(Date.UTC(2026,10,2+i,12))));},[currentLocale]);
  const monthTitle=useMemo(()=>new Intl.DateTimeFormat(currentLocale,{timeZone:'Asia/Bangkok',month:'long',year:'numeric'}).format(new Date(month+'-01T12:00:00+07:00')),[currentLocale,month]);
  const rows=records.data?.account===session.data?.account?(records.data?.records||[]):[],selected=rows.filter(r=>r.activity_date===day);
  useEffect(()=>{setForm(null);setError('');setMessage('');},[session.data?.account]);
  const set=(key,value)=>setForm(old=>({...old,[key]:value}));
  const open=(kind)=>{setError('');setMessage('');setForm({...blank(day,kind),_account:session.data?.account});};
  const move=delta=>{const next=shiftMonth(month,delta);if(next<'1981-01'||next>'2100-12')return;setMonth(next);setDay(next+'-01');};
  async function save(event){
    event.preventDefault();if(busy||!session.data||form?._account!==session.data.account)return;
    setBusy(true);setError('');setMessage('');
    const {id,version,created_at,updated_at,_account,_automaticTitle,...fields}=form;
    const payload={...fields,title:_automaticTitle?text(kindName(form.kind)):form.title,amount:form.amount===''?null:form.amount,unit:form.amount===''?null:form.unit};
    try{
      const response=await api('/api/orchard-activities'+(version?'/'+id:''),{method:version?'PATCH':'POST',
        headers:{'Content-Type':'application/json','X-CSRF-Token':session.data.csrf},
        body:JSON.stringify(version?{...payload,expected_version:version}:{...payload,id})});
      setMonth(response.record.activity_date.slice(0,7));setDay(response.record.activity_date);setForm(null);
      records.reload();window.dispatchEvent(new Event('orchard:stage-saved'));setMessage('บันทึกใน Supabase แล้ว');
    }catch(e){setError(e.message+' · ถ้ายังยืนยันการบันทึกไม่ได้ ให้โหลดปฏิทินก่อนลองอีกครั้ง');}
    finally{setBusy(false);}
  }
  return <div className="page-stack orchard-journal"><header className="journal-heading"><div><h2 className="text-xl font-bold">บันทึกสวนและปฏิทิน</h2><p className="mt-2 text-sm text-slate-500">เลือกวัน แล้วเพิ่มสิ่งที่ทำหรือวางแผนไว้</p></div><span className="journal-private"><Icon name="leaf" className="h-4 w-4"/>ข้อมูลที่เจ้าของสวนบันทึก</span></header>
    <ResourceStatus resource={session}/><ResourceStatus resource={records}/>
    <div className="journal-quickactions grid grid-cols-2 gap-2 sm:grid-cols-5">{activityKinds.map(([kind,label,icon])=><Button key={kind} data-activity={kind} className={kind==='stage'?'col-span-2 sm:col-span-1':''} disabled={!session.data||busy} onClick={()=>open(kind)}><span className="journal-action-icon"><Icon name={icon} className="h-4 w-4"/></span>{label}</Button>)}</div>
    {message&&<p role="status" className="notice">{message}</p>}{error&&<p role="alert" className="notice">{error}</p>}
    {form&&form._account===session.data?.account&&<Card title={form.version?'แก้ไขกิจกรรม':'เพิ่มกิจกรรม'} icon="calendar"><form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
      <Field label="รหัสสวนของฉัน"><input required maxLength={64} value={form.orchard_code} onChange={e=>set('orchard_code',e.target.value)}/></Field>
      <Field label="วันที่กิจกรรม"><input type="date" required min="1981-01-01" max={form.status==='done'?today():'2100-12-31'} value={form.activity_date} onChange={e=>set('activity_date',e.target.value)}/></Field>
      <Field label="ประเภทกิจกรรม"><select aria-label="ประเภทกิจกรรม" value={form.kind} onChange={e=>setForm(old=>({...old,kind:e.target.value,title:kindName(e.target.value),_automaticTitle:true,production_stage:e.target.value==='stage'?'recovery':null,stage_context:{},amount:'',unit:''}))}>{activityKinds.map(([k,t])=><option key={k} value={k}>{t}</option>)}</select></Field>
      <Field label="สถานะกิจกรรม"><select aria-label="สถานะกิจกรรม" value={form.status} onChange={e=>set('status',e.target.value)}><option value="planned">วางแผน</option><option value="done">ทำแล้ว / สังเกตแล้ว</option></select></Field>
      {form.kind==='stage'&&<Field label="ระยะการผลิตที่บันทึก"><select aria-label="ระยะการผลิตที่บันทึก" value={form.production_stage} onChange={e=>set('production_stage',e.target.value)}>{activityStages.map(([k,t])=><option key={k} value={k}>{t}</option>)}</select></Field>}
      <Field label="หัวข้อกิจกรรม"><input required maxLength={120} value={form._automaticTitle?text(kindName(form.kind)):form.title} onChange={e=>setForm(old=>({...old,title:e.target.value,_automaticTitle:false}))}/></Field>
      {form.kind!=='stage'&&<><Field label="ปริมาณ (ไม่ทราบให้เว้นว่าง)"><input type="number" min="0" max="1000000000" step="any" value={form.amount??''} onChange={e=>set('amount',e.target.value)}/></Field><Field label="หน่วยปริมาณ"><select aria-label="หน่วยปริมาณ" required={form.amount!==''&&form.amount!==null} value={form.unit||''} onChange={e=>set('unit',e.target.value)}><option value="">เลือกหน่วย</option>{activityUnits.map(([k,t])=><option key={k} value={k}>{t}</option>)}</select></Field></>}
      <div className="sm:col-span-2"><Field label="รายละเอียดที่สังเกต / สิ่งที่ทำ"><textarea rows={3} maxLength={2000} value={form.notes} onChange={e=>set('notes',e.target.value)}/></Field></div>
      <p className="text-xs leading-6 text-slate-500 sm:col-span-2">sensor-orchard-v1 คือสวนที่ติดตั้งเซนเซอร์ · ระยะที่ทำแล้วของสวนนี้จะแสดงในภาพรวมตามวันที่สังเกตล่าสุด แผนในอนาคตจะไม่เปลี่ยนระยะปัจจุบัน · บันทึกเก็บเกี่ยวที่นี่ไม่ใช่ยอดปิดฤดู ให้ใช้แบบประวัติผลผลิตเดิมสำหรับ กก./ไร่</p>
      <div className="flex flex-wrap gap-2 sm:col-span-2"><button className="btn-primary" type="submit" disabled={busy||!session.data}>{busy?'กำลังบันทึก…':'บันทึกกิจกรรม'}</button><Button disabled={busy} onClick={()=>{setForm(null);setError('');}}>ยกเลิก</Button></div>
    </form></Card>}
    <div className="journal-workspace"><section className="card journal-calendar-card" aria-label="ปฏิทินกิจกรรมสวน"><div className="journal-calendar-heading"><h3 className="font-semibold">{monthTitle}</h3><Button onClick={()=>{setMonth(today().slice(0,7));setDay(today());}}>วันนี้</Button></div><div className="journal-month-controls"><Button aria-label="เดือนก่อนหน้า" onClick={()=>move(-1)}>‹</Button><Field label="เดือนปฏิทิน"><select aria-label="เดือนปฏิทิน" value={Number(month.slice(5))} onChange={e=>{const next=month.slice(0,4)+'-'+e.target.value.padStart(2,'0');setMonth(next);setDay(next+'-01');}}>{Array.from({length:12},(_,i)=><option key={i} value={i+1}>{monthLabels[i]}</option>)}</select></Field><Field label="ปีปฏิทิน"><select aria-label="ปีปฏิทิน" value={month.slice(0,4)} onChange={e=>{const next=e.target.value+month.slice(4);setMonth(next);setDay(next+'-01');}}>{Array.from({length:120},(_,i)=><option key={i} value={1981+i}>{1981+i+(locale()==='th-TH'?543:0)}</option>)}</select></Field><Button aria-label="เดือนถัดไป" onClick={()=>move(1)}>›</Button></div>
      <div className="journal-calendar"><div className="mb-1 grid grid-cols-7 text-center text-xs text-slate-500">{weekdayLabels.map((label,i)=><span key={i}>{label}</span>)}</div><div className="grid grid-cols-7 gap-0.5">{monthDays(month).map((stamp,i)=>{
        if(!stamp)return <span key={'blank-'+i}/>;
        const events=rows.filter(r=>r.activity_date===stamp),done=events.filter(r=>r.status==='done').length;
        return <button key={stamp} type="button" aria-pressed={stamp===day} aria-current={stamp===today()?'date':undefined}
          aria-label={stamp+' · '+events.length+' กิจกรรม · ทำแล้ว '+done+' · วางแผน '+(events.length-done)}
          className={'journal-day '+(stamp===day?'journal-day-selected':'')} onClick={()=>setDay(stamp)}>
          <span className="font-bold">{Number(stamp.slice(-2))}</span>{events.length>0&&<span className="text-[10px]">{events.length} งาน</span>}{stamp===today()&&<span className="text-[9px]">วันนี้</span>}
        </button>;
      })}</div></div><p className="mt-3 text-xs text-slate-500">เลือกวันที่เพื่อดูงาน · เวลาสร้างและแก้ไขใช้เวลาไทย · ไม่มีการย้ายงานวางแผนเป็นทำแล้วอัตโนมัติ</p>
    </section>
    <Card className="journal-day-card" title={'กิจกรรมวันที่ '+dateTime(day)} icon="calendar" actions={<Button aria-label="โหลดปฏิทินใหม่" title="โหลดปฏิทินใหม่" onClick={records.reload}><Icon name="refresh" className="h-4 w-4"/><span className="hidden sm:inline">โหลดปฏิทินใหม่</span></Button>}>
      {!records.loading&&!records.error&&selected.length===0&&<div className="journal-empty"><span className="journal-empty-icon"><Icon name="calendar"/></span><p className="text-sm text-slate-500">ยังไม่มีบันทึกในวันที่เลือก กดประเภทกิจกรรมด้านบนเพื่อเพิ่ม</p><Button primary onClick={()=>open('water')}>เพิ่มกิจกรรม</Button></div>}
      <div className="grid gap-3">{selected.map(row=><article key={row.id} className="rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs text-slate-500">{kindName(row.kind)} · {row.status==='done'?'ทำแล้ว / สังเกตแล้ว':'วางแผน'} · <span data-source-original>{row.orchard_code}</span></p><h3 data-source-original className="mt-1 font-bold">{row.title}</h3>{row.kind==='stage'&&<p>ระยะ: {stageName(row.production_stage)}</p>}{row.amount!==null&&<p>{format(row.amount,2)} {activityUnits.find(v=>v[0]===row.unit)?.[1]}</p>}</div><Button disabled={busy} onClick={()=>{setForm({...row,_account:session.data?.account,amount:row.amount??'',unit:row.unit??''});setError('');}}>แก้ไขกิจกรรม</Button></div>{row.notes&&<p data-source-original className="mt-2 whitespace-pre-wrap break-words text-sm">{row.notes}</p>}<p className="mt-3 text-xs text-slate-500">แก้ไขล่าสุด {dateTime(row.updated_at)} · รุ่น {row.version}</p></article>)}</div>{selected.length>0&&<p className="mt-4 text-xs text-slate-500">ชื่อและบันทึกที่คุณพิมพ์คงภาษาต้นฉบับ</p>}
    </Card></div><details className="card journal-notes"><summary>รายละเอียดการบันทึก</summary><Notice>บันทึกนี้เป็นข้อมูลที่เจ้าของรายงาน ไม่ใช่การยืนยันโรคหรือคำสั่งให้น้ำ/ปุ๋ย ระบบยังไม่ฝึกโมเดลอัตโนมัติ และไม่รวมเป็นผลผลิตสวนจริงครบฤดู</Notice></details>
  </div>;
}
