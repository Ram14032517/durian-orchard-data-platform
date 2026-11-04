# ผลปรับความเร็ว 2 พฤศจิกายน 2569

ติดตั้งสกิลทางการ `supabase/agent-skills/skills/supabase-postgres-best-practices` ที่ `C:/Users/support/.codex/skills/supabase-postgres-best-practices` และอ่านแนวทาง Query/สิทธิ์ พร้อมใช้ Vercel React Best Practices เดิม ไม่แก้ Schema, Index, RLS หรือข้อมูล Supabase โดยไม่มี Query Plan รองรับ

## สิ่งที่เปลี่ยน

- `web/react/src/main.jsx`: memo หน้าที่เคยเปิดแล้ว เพื่อไม่คำนวณตาราง/กราฟที่ซ่อนอยู่ซ้ำจากการนำทาง คง state ของฟอร์มและส่งภาษาเป็น prop เพื่อไม่ให้ memo ขวางการสลับภาษา
- `web/react/src/data.js`: ใช้ Intl NumberFormat/DateTimeFormat ซ้ำแบบจำกัดขนาด แทนสร้างใหม่ทุกช่องตาราง ตัวเลข หน่วย ภาษา การปัดเศษ และ Asia/Bangkok คงเดิม
- `tools/serve_orchard_cloud.py`: แคชเซนเซอร์ในหน่วยความจำของแต่ละ app instance สูงสุด 30 วินาที หลังตรวจสิทธิ์เท่านั้น แยกตามบัญชี อุปกรณ์ Supabase URL และ fingerprint คีย์ คำนวณอายุจาก sensor_time ใหม่ทุกคำขอ ไม่แช่แข็งสถานะ fresh ไม่เก็บ error เป็นข้อมูลสำเร็จ และไม่คืนแคชหมดอายุแทนข้อผิดพลาด
- แคชใน browser แบบ private/immutable เฉพาะ JS/CSS ที่มี version hash เท่านั้น HTML/API/ข้อมูล GIS ยัง private/no-store ไม่เปลี่ยนสิทธิ์การดาวน์โหลดหรือทำให้ข้อมูลสวนเป็นสาธารณะ
- `web/react/src/Home.jsx`: ระบุช่วงแคชให้ผู้ใช้เห็น สร้าง bundle ใหม่และเปลี่ยน hash ใน UNIFIED_MAP.html

## ผลวัด

เก็บ bundle ก่อนแก้ไว้ที่ `.build/performance_review/before_optimization.js` ใช้ Chrome headless ในเครื่องเดียวกัน ทดสอบแบบเรียงก่อน–หลัง ไม่มีการรัน browser benchmark อื่นพร้อมกัน ใช้ QA login แยก ไม่มีข้อมูลเซนเซอร์จำลองแทนผลจริง ไม่ได้นำรหัสผู้ใช้จริงไปใส่ใน browser QA

สลับหน้า 6 ครั้ง วัดตั้งแต่เรียก click ถึง requestAnimationFrame สองเฟรมบน mobile viewport 390px/CPU throttle 4 เท่า:

| | ก่อน (ms) | หลัง (ms) |
|---|---|---|
| ตัวอย่างทั้งหก | 535, 303, 382, 684, 561, 701 | 174, 226, 66, 447, 56, 116 |
| ค่ากลาง | 548 | 145 |

นี่เป็นการวัดการตอบสนองการเรนเดอร์ในห้องทดลอง ไม่ใช่ INP จริงจากผู้ใช้ และไม่เท่ากับเวลาที่ทุก API โหลดเสร็จ ไม่มีการเรียก API เพิ่มจากการสลับภาษา การคงหน้าที่เคยเปิดไว้ช่วยไม่ให้เรียก OAE ซ้ำทุกครั้งที่ย้อนกลับ

LCP หน้า home ในรอบเดียวกัน CPU 4 เท่า: ก่อน 888/692/628 ms หลัง 552/568/428 ms (อย่างละ 3 ครั้ง) ตัวอย่างน้อยและยังมีผลจาก OS/cache จึงไม่รับประกันผลบนโทรศัพท์จริง

อ่านเซนเซอร์จริงผ่าน backend test client โดยคืนเฉพาะ timing/status ไม่บันทึกค่าหรือพิกัด: ครั้งแรก 2,075.96 ms, cache hit 0.72 และ 0.55 ms **เวลานี้ไม่รวมเครือข่ายจาก browser ไปเว็บ** คำขอแรก/หลังหมดแคชยังต้องรอ Supabase ไม่ใช่ทุกคำขอเร็วระดับนี้ ข้อมูลที่ตอบยังเป็น stale_live ตาม timestamp จริง

## การตรวจ

- Python cloud 25 ข้อ: login/logout, cache TTL, เปลี่ยนอุปกรณ์/คีย์, กันผู้ไม่มีสิทธิ์และข้ามบัญชี, ไม่แก้ payload ต้นฉบับ, ไม่เก็บ failure, private asset headers
- React/language 34 ข้อ: ตัวเลข/เวลาเดิม, Missing/ศูนย์, เซนเซอร์ผิดปกติ, โมเดลเดิม, ภาษา/ธีม และกราฟ
- OAE updater 8 ข้อ: ไม่แก้สูตร/ข้อมูล/เงื่อนไขนำเข้า
- Browser QA: 360/390/768/1440px ไม่ล้นแนวนอน, ห้าหน้าสลับ TH/EN ได้, Dark Mode, ปี/จังหวัดที่เลือกไว้คงอยู่หลังสลับหน้า, ไม่พบ pageerror
- ภาพจริงใน `.build/performance_review/desktop_after.png` และ `mobile_after.png`; ผลดิบ `controlled_comparison.json` และ `backend_after.json`

## ข้อจำกัด

ยังไม่ได้ทดสอบมือถือเครื่องจริงหรือเครือข่ายมือถือ ไม่ได้ Deploy/Push/Commit ไม่แก้ Production ML หรือข้อมูลต้นทาง ขนาด bundle เริ่มต้นยังใหญ่ (JS gzip ประมาณ 281 KB และ HTML gzip ประมาณ 166 KB) ยังไม่ได้ทำ code splitting ในงานนี้ ไม่มีการสร้าง Index โดยเดาว่า Query ช้า ไม่ได้แยก API ค่าดินย้อนหลังออกจากสถานะเซนเซอร์ ดังนั้น cold request อาจยังช้าตาม Supabase และการค้นประวัติ แคชไม่รับประกันอยู่ข้าม cold start ของ Vercel


## ปรับกราฟและคำขอเริ่มต้นเพิ่มเติม

- `web/react/src/ui.jsx`: แยกชั้นเส้น/แท่งเป็น React.memo; การเลือกเวลาเปลี่ยนเฉพาะเส้นชี้และค่าที่อ่าน ไม่สร้างเส้นและ tooltip ของทุกจุดซ้ำ กราฟมากกว่า 100 จุดไม่สร้างวงกลมรัศมีศูนย์หลายพัน element ใช้วงกลมจุดที่เลือกแทน เส้นยังมีค่าจริงครบทุกจุด และยังตัดช่วง Missing
- `web/react/src/Home.jsx`: เรียกเซนเซอร์หลัง session พร้อม เพื่อลดคำขอที่ถูกยกเลิกแล้วส่งใหม่ตอนเริ่มหน้า ตรวจจริงพบคำขอ orchard-status หนึ่งครั้ง
- Controlled benchmark: ข้อมูลทดสอบแยก 2,880 จุด, Chrome CPU slowdown 4x, เลือกต้น/ท้าย 16 ครั้งรวมรอ 2 animation frames ค่ากลางก่อน 198 ms หลัง 51 ms (~74% ลดลง) เป็น benchmark ปฏิสัมพันธ์กราฟ ไม่ใช่ INP หรือคำรับรองว่าเว็บทั้งระบบเร็วขึ้น 4 เท่า
- Browser จริงบน Local: กราฟรายจังหวัดเลือกเวลาผ่านคีย์บอร์ดได้ แบบฟอร์ม Journal ที่กรอกค้างไม่หายเมื่อสลับแท็บ หน้าจอ 360/390/768/1440 ไม่มี horizontal overflow ไม่ส่งรายการทดสอบไปฐานจริง
- Tests React + ภาษา 41 ผ่าน ภาพจริง `.build/performance_review/chart_after_actual.png`; benchmark `.build/performance_review/chart_comparison.json`
- ไม่เปลี่ยน API, สิทธิ์, Production ML หรือ Dataset และยังไม่ Deploy ผลบนเครือข่าย Vercel/อุปกรณ์จริงอาจต่างจาก Local
