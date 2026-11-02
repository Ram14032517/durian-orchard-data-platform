import React,{useSyncExternalStore} from 'react';
import {getLanguage,setLanguage,subscribeLanguage} from '../../i18n/language.js';
export default function LanguageControl(){
 const lang=useSyncExternalStore(subscribeLanguage,getLanguage,getLanguage);
 return <div className="language-control" role="group" aria-label="เปลี่ยนภาษา"><button type="button" lang="th" aria-label="ภาษาไทย" aria-pressed={lang==='th'} onClick={()=>setLanguage('th')}>TH</button><button type="button" lang="en" aria-label="ภาษาอังกฤษ" aria-pressed={lang==='en'} onClick={()=>setLanguage('en')}>EN</button></div>;
}
