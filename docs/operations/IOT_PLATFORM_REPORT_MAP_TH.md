# แผนผังไฟล์สำหรับเล่มรายงาน IoT Platform

ตรวจจากไฟล์ในเครื่อง 1 พฤศจิกายน 2569 · เป็นดัชนีหลักฐาน ไม่ใช่การรับรองความแม่นเซนเซอร์หรือโมเดล

## ส่วนที่ใช้งานปัจจุบัน

| เรื่องในเล่ม | ไฟล์/โฟลเดอร์หลัก | สิ่งที่ควรอธิบาย |
|---|---|---|
| ส่วนติดต่อผู้ใช้ | `web/react/src/`, `web/react/README_TH.md` | React, Tailwind, 5 เมนู, แท็บสวน, กราฟ และสถานะข้อมูล |
| สร้างเว็บ | `tools/build_orchard_react.ps1`, `tools/build_unified_orchard_map.py` | Source กับผล Build แยกกัน; `--reuse-bundled-data` ใช้ข้อมูลเดิม |
| เว็บที่สร้างแล้ว | `research_data/five_province_history/UNIFIED_MAP.html`, `orchard_app.js`, `orchard_app.css` ในโฟลเดอร์เดียวกัน | ต้องเก็บร่วมกัน เป็นไฟล์เปิดใช้งาน ไม่ใช่ไฟล์เกิน |
| Gateway และเซนเซอร์ | `iot/receiver_gateway/`, `iot/sender_1/`, `iot/soil_rs485_diag/`, `iot/sensor_docs/` | ตรวจรุ่น firmware ที่อัปโหลดจริงอีกครั้งก่อนระบุผลทดลองในเล่ม |
| รับและบันทึกข้อมูล | `api/supabase/functions/farm-ingest/index.ts`, `api/supabase/migrations/`, `api/google-apps-script/Code.gs` | เส้นทางรับข้อมูล ตาราง สิทธิ์ และการตรวจข้อมูล; โค้ดที่มีไม่ได้ยืนยันว่าทุกปลายทางยังใช้งานอยู่ |
| Backend และบัญชี | `tools/serve_orchard_analysis.py`, `tools/serve_orchard_cloud.py`, `tools/supabase_orchard.py` | API, Authentication, ข้อมูลส่วนบุคคล และสถานะล่าสุด/เก่า/ขาด/ผิดปกติ |
| พยากรณ์และผลผลิตสวน | `tools/orchard_forecast.py`, `tools/orchard_harvest.py`, `docs/orchard/` | แยกแบบจำลองอากาศ เซนเซอร์จริง และผลเก็บเกี่ยวที่เจ้าของบันทึก |
| แผนที่ GAP/ดิน | `web/react/src/MapPage.jsx`, `web/assets/js/orchard_gap_layer.js`, `research_data/priority_provinces/` | ระดับข้อมูลและสิทธิ์เผยแพร่; ทะเบียน GAP ไม่ใช่ผลเก็บเกี่ยวจริง |
| Deploy | `deployment/vercel/`, `tools/prepare_vercel_orchard.py` | ใช้แพ็กเกจที่คัดไฟล์แล้ว ไม่อัปโหลดทั้ง repository; private GIS ต้องคงสิทธิ์เดิม |
| ML และข้อจำกัด | `research_data/internal_research/`, `tools/durian_model/`, `ml/`, `models/` | แยกผลทดลองระดับจังหวัดจากการใช้จริง ไม่อ้างเป็นพยากรณ์รายสวน |
| ตรวจสอบระบบ | `tests/` | อ้างชื่อการทดสอบและผลรันจริง พร้อมวันที่; อย่าอ้างว่าทดสอบฮาร์ดแวร์จาก Tests เว็บ |

## โครงเล่มที่ใช้ดัชนีนี้ได้

1. ปัญหาและวัตถุประสงค์ของระบบติดตามสวน
2. อุปกรณ์ สถาปัตยกรรม และการไหลของข้อมูล
3. ฐานข้อมูล สิทธิ์เข้าถึง และการตรวจคุณภาพข้อมูล
4. หน้าเว็บและการใช้ข้อมูลช่วยตัดสินใจ พร้อมแหล่งวิชาการ
5. การทดสอบระบบ ผลทดลอง ML และข้อจำกัดที่พบจริง
6. สรุปผลและสิ่งที่ยังต้องตรวจภาคสนาม

ก่อนทำภาพสำหรับเล่ม ให้ถ่ายจากเวอร์ชันที่จะอ้างจริง ปกปิดชื่อผู้ใช้ รหัสสวน พิกัดละเอียด และ Secret ทุกชนิด

## ไฟล์เก่าที่เก็บไว้ด้วยเหตุผล

- `UNIFIED_MAP_CLASSIC.html` และ `orchard_lumen.*`: เครื่องมืออ้างอิงเดิม ยังมีลิงก์จากเว็บในเครื่อง เครื่องมือ Build และ Tests จึงยังไม่ลบ
- `HISTORY.html`, `HISTORY_ANALYSIS.html`, `HISTORY_ANALYSIS.ipynb`, `SEASONS_MAP.html`: หลักฐาน/เครื่องมือย้อนหลัง ยังถูกอ้างจากโค้ดและคู่มือ
- `.build/national-analysis-venv`, `.build/tailwind`, `web/react/node_modules`: Environment/เครื่องมือ Build ใช้งานอยู่
- `.build/friend_preview`: เป็น Git worktree แยก ห้ามลบเป็นโฟลเดอร์ธรรมดา
- ข้อมูลต้นทาง งานวิจัย PDF ผลทดลอง Cache ที่ใช้ทำซ้ำ และ Protected Assets: เก็บไว้สำหรับตรวจสอบที่มา

## เก็บกวาดรอบนี้

นำภาพตรวจเว็บชั่วคราว 32 ไฟล์ รวมประมาณ 2.89 MiB ไป Recycle Bin จาก `.build/react-qa`, `.build/orchard-tabs-qa`, `.build/forecast-week-qa`, `.build/orchard-harvest-qa` เท่านั้น กู้คืนได้ผ่าน Recycle Bin ของ Windows; ไม่ได้ล้าง Recycle Bin จึงยังไม่ถือว่าคืนพื้นที่ดิสก์ถาวร

ไม่ได้ย้ายเส้นทางโค้ด/ข้อมูล ไม่ลบหน้าเก่าที่ยังมีผู้เรียก ไม่เปลี่ยน Production หรือสิทธิ์ข้อมูล ไม่ Commit/Push/Deploy ในรอบเก็บกวาดนี้ คง Public HOLD
