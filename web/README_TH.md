# โค้ดหน้าเว็บ

ตั้งแต่ 22 ตุลาคม 2026 หน้าเปิดเริ่มที่ **สวนของฉัน** (`current-section`) ทุกครั้งตามพฤติกรรมเดิม ไม่ restore แท็บแผนที่จาก sessionStorage แล้ว แผนที่ GAP ยังอยู่แท็บ **แผนที่สวน** และปุ่มเปิด GAP ตามเดิม การเลือก A/B หรือ GAP ไม่เปลี่ยน `ORCHARD_DEVICE_ID` และไม่เพิ่มพิกัดเข้า query ประวัติ IoT ดู [บันทึกอัปเดต](../docs/updates/PROJECT_UPDATE_2026-10-22_TH.md) สำหรับสถานะ local snapshot เทียบกับ Supabase cloud และข้อจำกัดการเชื่อมต่อ

ธีมปัจจุบัน Orchard Studio อยู่ที่ `assets/css/orchard_studio.css` และถูกใส่ท้าย CSS เดิม เพื่อให้แก้ดีไซน์ในไฟล์เดียว แผนที่เต็มพื้นที่กับ sidebar อยู่ใน `assets/js/orchard_monthly_report.js`; การเคลื่อนและซูมอยู่ใน `assets/js/orchard_map_motion.js` ใช้ public API ของ Leaflet, เคารพ reduced motion และหยุด animation เก่าก่อนเริ่มรายการใหม่ ชั้น GAP เก็บกลุ่มหมุดตาม world pixels และ reuse marker แทนการล้างทุกครั้งที่แพน จึงไม่เพิ่ม DOM หลายหมื่นหมุดพร้อมกัน ไม่มีการเปลี่ยนข้อมูล/โมเดลจากงานออกแบบนี้

แก้หน้าตาแดชบอร์ดที่นี่ แล้วสร้างหน้าที่ใช้จริงด้วย `python tools/build_unified_orchard_map.py` จาก root ของโปรเจกต์

ถ้าเครื่องนี้มีหน้าแผนที่ที่ build ไว้แล้ว แต่ไม่มี cache ขอบจังหวัดต้นทาง ให้ใช้ `python tools/build_unified_orchard_map.py --reuse-bundled-data` เพื่ออัปเดตเฉพาะ UI ด้วยข้อมูลในแผนที่เดิม ไม่ดาวน์โหลดหรือเขียนข้อมูลประวัติ/โมเดลใหม่

- `templates/` — HTML ต้นแบบ หน้าหลักคือ `unified_orchard_map.html` ส่วนหน้าอื่นใช้สร้างรายงานเฉพาะเรื่อง
- `assets/js/` — การเลือกพื้นที่ A/B กราฟ ตาราง เซนเซอร์ และส่วนประกอบหน้าเว็บ
- `assets/css/` — รูปแบบหน้าเว็บและ Tailwind ทั้งต้นทางและ CSS ที่ build แล้ว

ไฟล์ที่เปิดใช้งานจริงอยู่ใน `research_data/five_province_history/` ตามเดิม เปิดด้วย `00_OPEN_REPORT.command` บน Mac หรือ `00_OPEN_REPORT.cmd` บน Windows เพื่อให้ API ทำงานด้วย

แก้ `assets/js/orchard_monthly_report.js` สำหรับกราฟและรายงาน, `assets/css/orchard_monthly_report.css` สำหรับรูปแบบหลัก และ `templates/unified_orchard_map.html` สำหรับโครงหน้า

ชั้นหมุด GAP อยู่ใน `assets/js/orchard_gap_layer.js` และ `assets/css/orchard_gap_layer.css`; `assets/js/orchard_gap_integration.js` เชื่อมหมุดกับ A/B และชั้นดินโดยใช้พิกัดจริงจากทะเบียน ไม่ย้ายไปจุดกลางอำเภอ ตั้งแต่ 25 ตุลาคม 2026 snapshot ชั้นหมุดที่ตรวจแล้วรวมใน Git ตามคำขอเจ้าของโปรเจกต์ จึงเปิด local map หลัง clone ได้โดยไม่ต้องสร้างชั้นหมุดใหม่ คำสั่ง `python tools/build_gap_map_layer.py` ใช้เมื่อต้องสร้างใหม่และต้องมีข้อมูลต้นทางแยกซึ่งไม่ได้เผยแพร่ทั้งหมด cloud route ยังไม่เปิดข้อมูลเหล่านี้อัตโนมัติ ดู [คู่มือ GAP](../docs/research/modeling/GAP_SPATIAL_INTEGRATION_TH.md) และ [ขอบเขตการเผยแพร่](../docs/updates/GAP_PUBLICATION_2026-10-25_TH.md)

เมื่อแก้ `assets/js/orchard_lumen.js` ให้รัน `node tools/build_orchard_lumen.mjs` หลังติดตั้ง dependencies ตาม [คู่มือ tools](../tools/README_TH.md) ส่วน `assets/css/orchard_tailwind.css` ต้อง build ด้วย `tools/build_orchard_tailwind.ps1` บน Windows ก่อนสร้างแผนที่ ไม่จำเป็นต้อง build CSS ใหม่เมื่อเพียงเปิดอ่านรายงาน
