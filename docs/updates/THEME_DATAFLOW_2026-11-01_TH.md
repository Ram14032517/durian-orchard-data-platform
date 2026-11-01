# Sync, ธีม Dark/Light และ Dataflow — 1 พฤศจิกายน 2569

ทำบน branch `codex/organize-project` ตามคำขอ sync → ปรับเว็บ → ทำไฟล์อธิบาย → ทดสอบ → push โดยไม่ merge กลับ main หรือสั่ง deploy

## รวมโค้ดล่าสุด

ดึง `origin/main` ถึง `09194ad` (4 commits ใหม่) เข้ากับงานเดิม Merge commit `778006e` เก็บหน้า React/Tailwind, clean routes, บัญชี/ประวัติผลผลิต และพยากรณ์ใหม่จาก main พร้อมตัวแก้ hash/NOAA และขอบเขต local/cloud ของ branch เดิม

แก้ conflict ที่ template/generated HTML, server, tests และ README โดยสร้างหน้า React/Classic ใหม่ด้วย DATA snapshot เดิม ไม่เลือกทับโค้ดฝ่ายใดทั้งไฟล์

เพื่อให้ launcher ตรวจได้ว่าเป็น Supabase project เดียวกันโดยไม่ส่ง URL จริงผ่าน `/api/project` ใช้ `private_storage_project_fingerprint` แบบ SHA256 และปรับตัวตรวจ launcher ร่วมกัน ยังปฏิเสธ server ที่ไม่ตรง checkout/configuration เดิม

## ธีม

- ตัวเลือก **ตามระบบ / Light / Dark** อยู่ขวาบนของหน้า React ทั้ง 5 เมนู และมีตัวเลือกเดียวกันในหน้า Classic
- จำค่า `durian.orchard.theme.v1` เท่านั้น ไม่เพิ่ม telemetry/credentials ใน storage และไม่เรียกข้อมูลเมื่อเปลี่ยนธีม
- ตั้งธีมก่อน paint; ตามระบบจะรับการเปลี่ยน OS, เลือกเองไม่ถูก OS ทับ, sync ระหว่างแท็บ origin เดียวกันได้ ถ้า storage ถูกบล็อกยังสลับได้ในหน้าปัจจุบัน
- ปรับการ์ด ตาราง ป้ายสถานะ ฟอร์ม กราฟ และ popup ให้เข้า palette ที่อ่านง่าย ไม่ invert สีแผนที่/หน่วยดิน/เส้นข้อมูล การสลับสีไม่เปลี่ยน A/B, อุปกรณ์ IoT, ฟอร์มที่ค้าง หรือผลโมเดล
- หน้า login/logout ใช้รูปแบบเดิม ไม่เปลี่ยนระบบยืนยันตัวตน

Source หลัก: `web/assets/js/orchard_theme.js`, `web/assets/css/orchard_theme.css`, `web/react/src/ThemeControl.jsx` และ template สองหน้า

## การ build บน Mac

เพิ่ม Tailwind CLI/Tailwind รุ่น **4.3.3** ที่ล็อกใน `web/react/pnpm-lock.yaml` ให้ `node tools/build_orchard_react.mjs` สร้าง JS และ CSS ได้ทั้ง Mac/Windows/Linux ใช้ React/esbuild รุ่นเดิม ไม่ต้องรัน Windows executable บน Mac หรือใช้ runtime CDN compiler

หลัง build ใช้ `tools/build_unified_orchard_map.py --reuse-bundled-data` เพื่อรักษา DATA เดิมและเปลี่ยน cache fingerprint ของ JS/CSS ดู [คู่มือ React](../../web/react/README_TH.md)

## จุดที่แก้เพื่อให้ sync แล้วใช้งานได้

- `/home`, `/map`, `/weather`, `/yield`, `/seasons` และ `/` ในเครื่องที่ยังไม่ได้ตั้ง private configuration เปิดหน้า static เดียวกับ launcher ได้ ไม่ตอบ 503 เพียงเพราะยังไม่มีบัญชี ถ้าตั้ง private configuration ไว้ยังผ่าน Flask auth เช่นเดิม API ส่วนตัวไม่ถูกเปิดเป็น public
- คง `local_snapshot` เป็นค่าเริ่มต้น และอ่านสดเมื่อเลือก `ORCHARD_DATA_SOURCE=supabase`; ประวัติ/การอ่านสดที่ตั้ง Supabase ต้องผ่าน private API เดิม ไม่ fallback ไปใช้ข้อมูลอีกชนิดอย่างเงียบ ๆ
- หน้า React แจ้ง local source/snapshot และอ่าน GAP capabilities เช่นเดียวกับ Classic: cloud ปกติแจ้งไม่เปิด GAP ส่วน Vercel ที่ผู้ดูแลตั้ง private GIS แล้วใช้เส้นทางเดิมภายใต้ login/allowlist/signed URL ไม่เพิ่ม route หรือเปลี่ยน bucket เป็น public
- ปรับ regression tests เดิมให้ตรวจ HTML Classic เมื่อทดสอบเครื่องมือ Classic และ mock Leaflet marker แบบใหม่ ไม่ลบการตรวจ missing/zero, A/B, SVG scoping หรือ auth

## เอกสาร Dataflow

- [DATAFLOW_TH.md](../architecture/DATAFLOW_TH.md) — source อ่านใน VS Code/GitHub
- [DATAFLOW_TH.html](../architecture/DATAFLOW_TH.html) — ผังภาพและคำอธิบาย เปิด offline ใน Safari ได้
- `tools/build_dataflow_doc.py` สร้าง HTML จาก Markdown; ใช้ `--check` ตรวจว่าตรงกัน

แยกสาย sensor, NASA ย้อนหลัง, GAP/LDD, โมเดลจังหวัด, Open-Meteo ส่วนตัว, ผลผลิตที่เจ้าของบันทึก และ local observations/theme พร้อม API/ไฟล์ต้นทาง สิทธิ์ หน่วย คุณภาพข้อมูล และส่วนโรคที่ยังเป็นงานอนาคต ไม่อ้างว่าการมีโค้ดหมายถึง deploy หรือยืนยันภาคสนามแล้ว

## ผลตรวจ

- Python: พบ 525 กรณี ผ่าน 464, ไม่มี fail/error; อีก 61 กรณีข้ามตามเงื่อนไข (ไฟล์วิจัย optional ไม่ครบ และไม่มี Postgres ทดสอบจริง) ตัว runner รัน 474 และรายงาน 14 skip records รวม 4 class-setup skips ซึ่งขวาง 51 กรณี ไม่อ้างว่าเทสต์ที่ข้ามผ่านแล้ว
- JavaScript/React: ผ่าน 106/106 ไม่มีข้าม รวม 8 กรณีของ theme bootstrap และ 1 กรณี selector React พร้อม regression ของ A/B, weather, GAP, missing/zero และ UI สวน
- เว็บ localhost จริง: `/home` เปิดได้ สลับ Dark → reload ยังเป็น Dark → Light → ไป `/map` ยังเป็น Light → Dark อีกครั้งได้ โดยจังหวัด A เดิม สุราษฎร์ธานี 11,081 หมุดตามตัวกรองยังคงเดิม ตรวจภาพสี/ตัวหนังสือจริงบน desktop ไม่ได้ทดสอบฮาร์ดแวร์เซนเซอร์หรืออุปกรณ์มือถือจริง
- ตรวจ Classic ด้วยภาพจริงและแก้ tokens ที่กำหนดทับบน body/การ์ด ให้พื้นหลังและตัวเลขอ่านได้ใน Dark จากนั้นเปลี่ยนเป็นตามระบบใน Classic แล้วตัวเลือก React อีกแท็บเปลี่ยนตามผ่าน storage event จริง คืนค่าตอนจบเป็นตามระบบ ไม่เลือกธีมถาวรแทนผู้ใช้
- ตรวจเอกสาร HTML ตรงกับ Markdown, ไม่มี live scripts/iframe และลิงก์ภายในชี้ไฟล์ที่มีจริง เครื่องมือตรวจเบราว์เซอร์ไม่อนุญาต `file://` จึงไม่ได้ยืนยันภาพเอกสารด้วยเบราว์เซอร์อัตโนมัติ ไม่แก้ข้อจำกัดนี้ด้วยการเผยแพร่เอกสาร/ข้อมูลส่วนตัวขึ้น server
- ชุดทดสอบ Python ปฏิเสธ requests ออกภายนอก ยอมรับเฉพาะ localhost สำหรับ HTTP fixture งานทดสอบไม่เพิ่มข้อมูลอากาศจริงหรือ train production
- ตรวจ SHA256 ของ input/model/artifacts ที่ป้องกันไว้ 27 ไฟล์ไม่เปลี่ยน, DATA ใน React/Classic ตรงกับ `e65632f`, `SEASONS_MAP.html` และ Excel GAP ไม่เปลี่ยนไบต์

ไม่มีการ train/เปลี่ยน production model, เผยแพร่ไฟล์ private เพิ่ม, upload พิกัด, migrate ฐานข้อมูล, deploy firmware หรือสั่ง deploy cloud การ push อาจเข้ากระบวนการ auto-deploy ของผู้ดูแลได้หากตั้งไว้เอง ต้องตรวจสถานะแพลตฟอร์มแยกต่างหาก
