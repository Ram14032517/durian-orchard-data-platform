export const activityKinds=[['water','ให้น้ำ','drop'],['fertilizer','ใส่ปุ๋ย','leaf'],['observation','พบอาการ / สำรวจ','info'],['harvest','เก็บเกี่ยว','durian'],['stage','ระยะการผลิต','calendar']];
export const activityStages=[['recovery','ฟื้นต้น','leaf'],['flower','เตรียมดอก','flower'],['bloom','ดอกบาน','flower'],['young','ติดผล','durian'],['growth','พัฒนาผล','durian'],['harvest','เก็บเกี่ยว','durian']];
export const activityUnits=[['litre','ลิตร'],['kg','กก.'],['minute','นาที'],['tree','ต้น']];
export function monthDays(month){
  const [year,m]=month.split('-').map(Number),first=new Date(Date.UTC(year,m-1,1));
  const count=new Date(Date.UTC(year,m,0)).getUTCDate(),offset=(first.getUTCDay()+6)%7;
  return Array.from({length:Math.ceil((count+offset)/7)*7},(_,i)=>{
    const day=i-offset+1;return day<1||day>count?null:month+'-'+String(day).padStart(2,'0');
  });
}
export function shiftMonth(month,delta){const [year,m]=month.split('-').map(Number);return new Date(Date.UTC(year,m-1+delta,1)).toISOString().slice(0,7);}
