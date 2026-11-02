# สลับไทย/อังกฤษและลดการโหลดซ้ำ — 2 พฤศจิกายน 2569

- ฐาน: งานของผู้ใช้บน main และการแก้ค้างเดิม ไม่มี Checkout, Merge หรือเขียนทับงานเพื่อน
- ตรวจ Remote ด้วย `git ls-remote`: codex/organize-project ล่าสุดคือ `093daa9cb149869d199b67caac13cc6673690de2`
- นำเฉพาะพจนานุกรมจาก `web/i18n/en.json` ของ commit นี้มาต่อยอด ไม่คัดลอก CSS, Theme, Motion หรือ Layout ของเพื่อน
- ภาษาเริ่มต้นไทย ปุ่ม TH/EN แทนข้อมูล GAP Snapshot บนหัวเว็บ แสดงได้ทั้ง Desktop/Mobile
- เก็บเฉพาะการเลือกภาษาใน localStorage; ไม่เก็บข้อมูลสวนหรือเปลี่ยนสิทธิ์
- สลับภาษาโดย React rerender ไม่ reload และไม่ remount ฟอร์ม/กราฟ; Home ที่ memo ไว้รับ language prop เพื่อไม่ค้างภาษาเดิม
- ใช้ JSX adapter แปลข้อความแสดงผล ไม่เปลี่ยน value ของ option/input, ค่า API, Label ML หรือ CSV
- Leaflet/GAP ใช้ observer เฉพาะ DOM ที่ไลบรารีเป็นเจ้าของ ย้อนกลับไทยจากข้อความเดิมได้ ไม่แก้ React DOM หรือเฝ้าทั้ง document.body
- ชื่อดิน/ข้อมูลต้นทางและข้อความที่ไม่มีคำแปลอาจยังแสดงภาษาต้นฉบับ หน้า login ไม่ได้เปลี่ยนในงานนี้
- แก้คำแปล Year (CE) ที่ไม่ตรงกับปี พ.ศ. เป็น Year (B.E.) ไม่แอบเปลี่ยนค่าปี

## การตอบสนอง

- หน้า Weather/Yield/Seasons โหลดเมื่อเปิดครั้งแรกและคงไว้เมื่อเปลี่ยนหน้า เช่นเดียวกับ Home/Map เดิม ลดการสร้างกราฟและการอ่านข้อมูลซ้ำ
- Refresh คงข้อมูลเดิมระหว่างอ่าน; เปลี่ยน URL/บัญชีจะล้างข้อมูลเก่าแยกตาม request identity ไม่มี shared cache ข้ามบัญชี
- ไม่มีการเพิ่ม Library หรือบริการแปลภายนอก
- พจนานุกรมเพิ่มขนาด bundle แรก; ใช้พจนานุกรมในเครื่องและ cache ข้อความที่แปลแล้วสูงสุด 2,048 รายการ ไม่เรียก API เมื่อสลับภาษา

## ผลตรวจ

- Node tests: 33 ผ่าน (รวมภาษาใหม่ 3 ข้อ)
- Cloud/auth regression: 20 ผ่าน
- Chromium บน Windows แบบ headless: หน้า Home/Map/Weather/Yield/Seasons สลับ TH→EN→TH ที่ 390px ได้ ไม่มี page error และไม่มี page overflow
- ตรวจ viewport 360/390/768/1440px; ตรวจ Light/Dark, จำภาษาหลัง reload, คงจังหวัด/ปีที่เลือก และสลับภาษาไม่เรียก API เพิ่ม
- ทดสอบ navigation 6 ครั้ง: การร้องขอ annual_yield_feature_comparison.json ลดจาก 3 เป็น 1 ครั้ง โดยไม่ใช้จำนวนคำขออื่นที่เกิดจาก session/project มาปน
- ตัวเลข click-to-two-animation-frames เป็นการตรวจเชิงวินิจฉัยในเครื่อง ไม่ใช่ผล benchmark ผู้ใช้จริงหรือความเร็ว Supabase/Open-Meteo
- หลักฐานทดสอบใน `.build/language_qa/results.json`, `pages.json` และภาพ Desktop/Mobile
- ไม่ได้ทดสอบโทรศัพท์จริง ไม่ได้แก้ Backend/Authentication/ML/Dataset และยังไม่ Commit/Push/Deploy; Public HOLD
