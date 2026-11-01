# Frontend React และ Tailwind

หน้าหลักทั้ง 5 เมนูอยู่ที่ `src/main.jsx` และใช้ React 19.3.1 กับ Tailwind CSS 4.3.3 ที่ build ไว้ในเครื่อง ไม่มี Babel หรือ React CDN ในหน้าใช้งานจริง

- `Home.jsx` — ค่าสดจาก Supabase, กราฟย้อนหลัง, บันทึกระยะ และประวัติผลผลิตส่วนตัว
- `MapPage.jsx` — React ควบคุม A/B และหน่วยดิน ใช้ Leaflet และโมดูลหมุด GAP เดิมที่มีการกรอง/จัดกลุ่ม ไม่แสดงจำนวนกลุ่มจนคลิก
- `Weather.jsx` — อากาศ A/B, ช่วงวัน/เดือน, กราฟ, ตารางเรียงลำดับ/แบ่งหน้า และ CSV พร้อมป้ายข้อมูลสำรอง
- `Reports.jsx` — ผลผลิตรายจังหวัด, ฤดูกาล, รายงานรายเดือน และเครื่องมือนับย้อนอายุผล
- `ui.jsx` — การ์ด, ตาราง, สถานะ และกราฟ SVG ที่ไม่เชื่อมเส้นข้ามค่าที่ขาด
- `api.js` — API เดิม พร้อม credentials, การยกเลิกคำขอเก่า และล้างข้อมูลเมื่อบริบทเปลี่ยน
- `style.css` — Tailwind utilities และ components โทนเขียวพร้อมการ์ดสีอ่อน รองรับมือถือ

## สร้างหน้าเว็บ

จาก `C:\project`:

```powershell
pnpm.cmd --dir web/react install --frozen-lockfile
& tools/build_orchard_react.ps1
& .build/national-analysis-venv/Scripts/python.exe -B tools/build_unified_orchard_map.py --reuse-bundled-data
& .build/national-analysis-venv/Scripts/python.exe -B tools/open_orchard_report.py --port 8871
```

หากใช้ Python environment อื่นที่โครงการรองรับ ใช้ Python จาก environment นั้นได้ การเปิดเว็บไม่ต้องรัน Node และไม่ได้ฝึกโมเดล

ผล build คือ `research_data/five_province_history/orchard_app.js`, `orchard_app.css` และ `UNIFIED_MAP.html` ที่ URL เดิม Node packages อยู่ใน `web/react/node_modules` ซึ่งไม่เข้า Git; เก็บรุ่น dependencies ใน `package.json` และ `pnpm-lock.yaml`

`UNIFIED_MAP_CLASSIC.html` เก็บเครื่องมือวิเคราะห์ละเอียดเดิมไว้เป็นลิงก์เสริม กฎคัดคุณภาพ/การจัดกลุ่มหมุด GAP และการอ่าน API อยู่ในโมดูลเดิม ไม่ได้เขียนใหม่เพื่อเปลี่ยนค่าหรือเกณฑ์วิจัย

## ขอบเขตข้อมูล

API/ฐานข้อมูล/Authentication เดิมยังใช้เหมือนเดิม คีย์ Supabase อยู่ฝั่งเซิร์ฟเวอร์เท่านั้น ไม่อยู่ใน bundle ไม่มีการย้ายข้อมูลจริงลง localStorage ประวัติผลผลิตเก็บในฐานข้อมูล ส่วนระยะสังเกตยังเป็นบันทึกเฉพาะเบราว์เซอร์ตามระบบเดิมและมีข้อความแจ้ง

อากาศ NASA POWER เป็นกริด การใช้ไฟล์สำรองจุดจังหวัดต้องแสดงคำเตือน ผลผลิตจังหวัดไม่ใช้แทนผลผลิตหมุด GAP หรือสวน และการเปลี่ยน UI ไม่รับรองความสดหรือความถูกต้องของอุปกรณ์ ทุกการบันทึกผลผลิตต้องผ่านสิทธิ์/CSRF/การตรวจหน่วย/รุ่นข้อมูลจาก backend

## ทดสอบเฉพาะส่วน

```powershell
node --test tests/test_orchard_react.cjs tests/test_orchard_workspace.js tests/test_weather_fallback.js
& .build/national-analysis-venv/Scripts/python.exe -B -m unittest tests.test_orchard_history tests.test_orchard_harvest tests.test_cloud_dashboard
```

Public Release HOLD; ชุดข้อมูล/Geometry ไม่ได้รับอนุญาตให้นำออกเผยแพร่จากการย้าย frontend นี้ และยังไม่มีคำพยากรณ์ผลผลิตรายสวนที่ผ่านการทดสอบ

แผนที่หน่วยดินใช้สีเพื่อแยกรหัสจากไฟล์เดิมเท่านั้น ไม่ใช่สีมาตรฐาน LDD หรือคะแนนความเหมาะสม รหัสเดียวกันใช้สีเดียวกันทุกจังหวัด โดย SC เป็นสีเทา W เป็นสีฟ้า และคำอธิบายสีใช้ชื่อจากต้นทาง เส้นแผนที่ที่ลดรายละเอียด 50 เมตรใช้เพื่อแสดงผล ไม่ยืนยันขอบเขตดินรายสวน

สถานะบัญชีอยู่มุมขวาบน เข้าสู่ระบบแล้วกลับหน้าเดิมได้ ออกจากระบบต้องยืนยันและส่งรหัสป้องกันคำขอปลอม ระบบสิทธิ์เดิมยังคงอยู่ สไตล์หมุด GAP อยู่ใน `orchard_gap_layer.css` ร่วมกันทั้งหน้า React และเครื่องมือเดิม เพื่อไม่ให้เหลือเฉพาะพื้นที่คลิกที่ไร้รูปหมุด
