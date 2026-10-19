# โค้ดหน้าเว็บ

แก้หน้าตาแดชบอร์ดที่นี่ แล้วสร้างหน้าที่ใช้จริงด้วย `python tools/build_unified_orchard_map.py` จาก root ของโปรเจกต์

- `templates/` — HTML ต้นแบบ หน้าหลักคือ `unified_orchard_map.html` ส่วนหน้าอื่นใช้สร้างรายงานเฉพาะเรื่อง
- `assets/js/` — การเลือกพื้นที่ A/B กราฟ ตาราง เซนเซอร์ และส่วนประกอบหน้าเว็บ
- `assets/css/` — รูปแบบหน้าเว็บและ Tailwind ทั้งต้นทางและ CSS ที่ build แล้ว

ไฟล์ที่เปิดใช้งานจริงอยู่ใน `research_data/five_province_history/` ตามเดิม เปิดด้วย `00_OPEN_REPORT.command` บน Mac หรือ `00_OPEN_REPORT.cmd` บน Windows เพื่อให้ API ทำงานด้วย

แก้ `assets/js/orchard_monthly_report.js` สำหรับกราฟและรายงาน, `assets/css/orchard_monthly_report.css` สำหรับรูปแบบหลัก และ `templates/unified_orchard_map.html` สำหรับโครงหน้า

เมื่อแก้ `assets/js/orchard_lumen.js` ให้รัน `node tools/build_orchard_lumen.mjs` หลังติดตั้ง dependencies ตาม [คู่มือ tools](../tools/README_TH.md) ส่วน `assets/css/orchard_tailwind.css` ต้อง build ด้วย `tools/build_orchard_tailwind.ps1` บน Windows ก่อนสร้างแผนที่ ไม่จำเป็นต้อง build CSS ใหม่เมื่อเพียงเปิดอ่านรายงาน
