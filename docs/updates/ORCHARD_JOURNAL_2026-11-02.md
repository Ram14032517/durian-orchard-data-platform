# บันทึกสวนและปฏิทินส่วนตัว

เพิ่มแท็บที่หก **บันทึกสวน** ภายในสวนของฉัน เมนูหลักห้าหน้าเดิมไม่เปลี่ยน ใช้ React/Tailwind/API/Flask session/Supabase project เดิม ไม่มี Backend ใหม่หรือ Library เพิ่ม

## วิธีใช้

1. เลือกวันที่ในปฏิทิน แล้วกด ให้น้ำ / ใส่ปุ๋ย / พบอาการ–สำรวจ / เก็บเกี่ยว / ระยะการผลิต
2. ระบุหัวข้อ รายละเอียด สถานะ และปริมาณ/หน่วยถ้าทราบ การไม่ทราบปริมาณเก็บ null ไม่แทนศูนย์
3. เลือก **ทำแล้ว / สังเกตแล้ว** สำหรับสิ่งที่เกิดจริง หรือ **วางแผน** สำหรับงานที่จะทำ ห้ามบันทึกทำแล้วในอนาคต ทั้ง API และฐานข้อมูลตรวจเวลาไทย
4. กดวันที่เพื่อดูรายการ ใช้แก้ไขกิจกรรมเพื่อเปลี่ยนข้อมูล ทุกครั้งเพิ่ม version และเก็บ revision เดิม ปฏิเสธการแก้ไขด้วย version เก่าเพื่อไม่เขียนทับงานพร้อมกัน
5. รหัส `sensor-orchard-v1` ใช้กับสวนเซนเซอร์เดิม ระยะที่สังเกตแล้วของสวนนี้ วันที่ล่าสุดไม่เกินวันนี้ จะแสดงใน Timeline หน้าวันนี้ งานวางแผนและสวนรหัสอื่นไม่เปลี่ยนระยะปัจจุบัน

สามารถบันทึกระยะจากแบบเดิมในแท็บวันนี้ได้ด้วย แบบเดิมเก็บวันที่วันนี้พร้อมบริบทจังหวัด/ให้น้ำ/สิ่งที่สังเกตลง Supabase ส่วนปฏิทินเลือกวันที่ย้อนหลังได้ ระยะเก่าใน localStorage ไม่ถูกลบหรือย้ายเข้า DB โดยอัตโนมัติ และไม่นำมาอ้างว่าเป็นบันทึกถาวรแล้ว

## ฐานข้อมูลจริง

นำ migration `api/supabase/migrations/005_private_orchard_activities.sql` ไปใช้กับ Supabase เดิมผ่าน SQL Editor สำเร็จ 2 พฤศจิกายน 2569:

- `public.orchard_activities`: UUID สำหรับคำขอเดิม, owner hash, รหัสสวน, วันที่, ประเภท, ระยะ, บริบท, สถานะ, หัวข้อ, หมายเหตุ, ปริมาณ/หน่วย, version, created_at/updated_at
- `public.orchard_activity_revisions`: เก็บข้อมูลเดิมทุกครั้งที่แก้ไขผ่าน trigger
- Index `(owner_id, activity_date, id)` รองรับปฏิทินรายเดือน
- เปิด RLS ทั้งสองตาราง ไม่มี public policy และ revoke สิทธิ์ anon/authenticated ทั้งหมด ให้ service_role อ่าน–เพิ่ม–แก้กิจกรรม และอ่าน revision เท่านั้น **ไม่ให้ DELETE**
- ระบบเดิมใช้ Flask session ไม่ได้ใช้ Supabase Auth UID จึงคง owner hash แบบเดียวกับผลผลิตสวน: backend ตรวจ session และกรอง owner_id ทุก query ตรวจ owner ของผลตอบกลับอีกครั้ง คีย์อยู่ฝั่งเซิร์ฟเวอร์
- UI ใช้ account guard ป้องกันผลตอบกลับบัญชีก่อนหน้าปรากฏเมื่อสลับบัญชี ฟอร์มเก็บใน state ไม่เก็บใน localStorage และไม่ส่ง owner_id จาก browser
- UUID เดิมป้องกันบันทึกซ้ำจาก retry ของแบบเดียวกัน ไม่ป้องกันการตั้งใจสร้างกิจกรรมใหม่หลายครั้งในวันเดียว เพราะทำงานหลายรอบจริงได้

## API

- GET `/api/orchard-activities?month=YYYY-MM`: อ่านเดือนเดียว ไม่ส่งข้อมูลตัดทอนเงียบ ๆ ถ้าเกิน 999 รายการ
- POST `/api/orchard-activities`: เพิ่มกิจกรรม ต้อง login, CSRF และ Origin ถูกต้อง
- PATCH `/api/orchard-activities/<uuid>`: แก้ไขโดยตรวจ owner และ expected_version
- GET `/api/orchard-activities/stage`: ระยะล่าสุดของสวนเซนเซอร์ที่สังเกตแล้ว ไม่ใช้แผนในอนาคต

## ไฟล์หลักที่แก้

- `tools/orchard_activities.py`: validation และ store ใช้ transport `HarvestStore` เดิม (เพิ่ม class attribute table โดยไม่เปลี่ยนตารางผลผลิตเดิม)
- `tools/serve_orchard_cloud.py`, `tools/serve_orchard_analysis.py`: API และ routing ภายใต้สิทธิ์เดิม
- `tools/prepare_vercel_orchard.py`: รวมโมดูลใหม่ในการเตรียม deploy ครั้งถัดไป ยังไม่ Deploy
- `web/react/src/OrchardJournal.jsx`, `activityData.js`: ปฏิทิน/ฟอร์ม/รายการ/แก้ไข
- `web/react/src/Home.jsx`: แท็บใหม่และเชื่อมระยะเดิมกับ DB
- `web/react/src/data.js`: ค่าวันที่ล้วนแสดงเฉพาะวันที่ ไม่เติมเวลาสังเกตปลอม
- `web/react/src/style.css`: แท็บ 3×2 บนมือถือ/6 คอลัมน์จอใหญ่ และปฏิทิน Light/Dark
- Rebuild `orchard_app.js`, `orchard_app.css` และเปลี่ยน hash ใน `UNIFIED_MAP.html`

## หลักฐานทดสอบ

- Unit/API: กิจกรรม 8, cloud 26, ผลผลิตสวนเดิม 14, OAE 8, React/language 36 รวม 92 tests
- สร้าง/แก้ไขในฐานข้อมูลจริงผ่าน Transaction โดยใช้ service_role ตรวจ version 2, revision 1, และปฏิเสธ done ในอนาคต แล้ว **ROLLBACK** ตรวจซ้ำผ่าน REST ว่า QA rows เหลือ 0 สคริปต์ `tests/orchard_activities_transaction_probe.sql`
- Query สิทธิ์จริง: ทั้งสองตาราง RLS=true, anon SELECT=false, authenticated SELECT=false, service_role DELETE=false
- UI CRUD ทดสอบผ่าน backend จริงกับ adapter ในหน่วยความจำที่ port 8878 แยกจากฐานจริง ไม่สร้างรายการสวนปลอมใน production: เพิ่ม แก้ รีเฟรช ระยะปัจจุบัน และแผนอนาคตไม่เปลี่ยนระยะจริง
- Viewports 360/390/768/1440px ไม่มี horizontal overflow/pageerror
- อ่านปฏิทินจาก Supabase จริงที่ port 8871 สำเร็จ ขณะตรวจยังไม่มีรายการของเจ้าของ ภาพจริง `.build/journal_qa/actual_desktop.png`, `actual_mobile.png` ไม่ใส่ข้อมูลตัวอย่าง

## ข้อจำกัด

ยังไม่ Deploy/Commit/Push ไม่ Auto-train ML ไม่สั่งให้น้ำหรือปุ๋ย ไม่สร้างผลผลิตสวนจากจังหวัด บันทึกเก็บเกี่ยวรายกิจกรรมไม่รวมเป็นผลผลิตครบฤดูหรือ Label ML อัตโนมัติ ให้ใช้แบบผลผลิตสวนเดิมเพื่อยืนยันพื้นที่ให้ผลและยอดทั้งฤดู ข้อมูลเป็นผู้ใช้รายงาน ไม่ใช่หลักฐานอิสระ ขณะนี้ไม่มีการลบกิจกรรม (แก้ไขได้และมี revision) และยังไม่ได้ทดสอบบนมือถือเครื่องจริง
