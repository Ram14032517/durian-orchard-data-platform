import React from 'react';

function Fruit({x=50,y=55,scale=1}){
  return <g transform={`translate(${x} ${y}) scale(${scale})`}>
    <path d="M0-22q-3-14 7-17" fill="none" stroke="#8a7347" strokeWidth="3" strokeLinecap="round"/>
    <path d="m0-23 5 3 6-1 2 6 5 3-1 6 5 5-3 5 1 6-5 3-2 6-6 1-5 4-5-3-6 1-3-5-6-2 1-6-4-5 3-5-1-6 5-3 2-6 6 1Z" fill="#769849" stroke="#476b34" strokeWidth="1.5"/>
    <path d="M0-16q-11 17 0 34M4-16q9 16 2 31" fill="none" stroke="#b8ca74" strokeWidth="2"/>
    <path d="m-10-10 3 2m-8 6 4 1m-2 6 4-1m-1 7 3-2m17-18-3 2m6 5-4 1m4 5-4-1m-1 7-2-2" stroke="#d6dd9a" strokeWidth="2" strokeLinecap="round"/>
  </g>;
}

export default function GrowthArt({stage,className='h-20 w-20'}){
  const flowering=stage==='flower'||stage==='bloom';
  return <svg viewBox="0 0 100 100" className={className} fill="none" aria-hidden="true">
    <ellipse cx="50" cy="89" rx="31" ry="5" fill="#c5d6ba" opacity=".45"/>
    {stage==='recovery'&&<g>
      <path d="M48 86q7-32 0-62" stroke="#6c8751" strokeWidth="4" strokeLinecap="round"/>
      <path d="M50 58Q17 61 17 35q28-6 33 23" fill="#6b9f62"/><path d="M50 42Q79 47 83 20q-28-7-33 22" fill="#447b4e"/>
      <path d="M49 27Q30 26 33 10q16-1 16 17" fill="#a5c579"/>
      <path d="m23 40 26 18m27-32L51 42" stroke="#d3e3b8" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="m32 87 5-8 22-1 11 9Z" fill="#b59a74"/>
    </g>}
    {flowering&&<g>
      <path d="M12 29q40 8 76-13" stroke="#886b44" strokeWidth="6" strokeLinecap="round"/>
      <path d="M63 26Q73 6 91 9q-3 18-28 17" fill="#5c8c52"/>
      {[30,48,65].map((x,i)=><g key={x}>
        <path d={`M${x} 30v${16+i*5}`} stroke="#8a9b62" strokeWidth="2"/>
        {stage==='flower'?<g><ellipse cx={x} cy={55+i*5} rx="6" ry="11" fill="#cdd39a" stroke="#98ab70" strokeWidth="1.5"/><path d={`M${x} ${46+i*5}v17`} stroke="#eef0c8" strokeWidth="1.5"/></g>:<g transform={`translate(${x} ${55+i*5})`}>
          {[0,72,144,216,288].map(a=><ellipse key={a} cy="-7" rx="5" ry="9" transform={`rotate(${a})`} fill="#fff4ce" stroke="#d9bb75"/>) }
          <circle r="5" fill="#d7ac50"/><path d="m-3 5-4 12m7-12v15m3-15 5 12" stroke="#cfab59" strokeWidth="1.2" strokeLinecap="round"/>
        </g>}
      </g>)}
    </g>}
    {stage==='young'&&<g><path d="M15 20q35 7 70-7" stroke="#886b44" strokeWidth="5" strokeLinecap="round"/><path d="M62 21q4-17 23-15-3 17-23 15" fill="#739d59"/><Fruit x={36} y={56} scale={.65}/><Fruit x={65} y={66} scale={.48}/></g>}
    {stage==='growth'&&<g><path d="M17 16q37 9 68-6" stroke="#886b44" strokeWidth="6" strokeLinecap="round"/><path d="M18 18q-9 18 13 22 6-17-13-22" fill="#739d59"/><Fruit x={52} y={60} scale={1.1}/></g>}
    {stage==='harvest'&&<g><path d="m16 66 7 23h54l7-23Z" fill="#b18b52"/><path d="M23 72h54m-51 7h48M33 68l3 20m13-20v20m13-20-3 20" stroke="#dbc59a" strokeWidth="2"/><Fruit x={39} y={52} scale={.95}/><path d="M70 35q31 28-3 46-27-24 3-46" fill="#eff1c7" stroke="#749452" strokeWidth="3"/><path d="M69 44q18 10 7 19-19 1-7-19m-2 21q19-4 4 11-12-3-4-11" fill="#ecc66e"/></g>}
  </svg>;
}
