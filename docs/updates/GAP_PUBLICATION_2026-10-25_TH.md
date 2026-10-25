# 25 ตุลาคม 2569 — รวมข้อมูล GAP เข้า branch สำหรับส่งต่อ

เจ้าของโปรเจกต์ขอให้ push Excel GAP และงานที่ยังไม่ได้ส่งบน branch `codex/organize-project` ไป repository GitHub เดิมซึ่งเป็น public รอบนี้เปลี่ยนขอบเขตจากเก็บ GAP เฉพาะเครื่อง เป็นส่งต่อ snapshot ที่ตรวจแล้วพร้อมโค้ด ไม่ใช่การดึงทะเบียนล่าสุด ไม่ใช่ train โมเดล และไม่ใช่ deploy เว็บ cloud

## ไฟล์ที่เพิ่มเข้า Git

- [Excel GAP รวม 5 จังหวัด](attachments/GAP_5_PROVINCES_20261020.xlsx): 10 ชีต snapshot 20 ตุลาคม 2026 ขนาด 12,282,854 ไบต์ คงข้อมูล สูตร รูปแบบ และทุกไบต์เดิม SHA256 `ef3d25feca214050e5e190d0f6d7f1fcc6e09e704d0bdb7b0205b8cb6c39af6c`
- [ชั้นหมุด GAP](../../research_data/five_province_history/gap_orchards/): manifest และ GeoJSON แยก 5 จังหวัด รวม 6 ไฟล์ มีหมุดทะเบียนที่ผ่านเกณฑ์แสดงผล 32,871 จุด ใช้รหัส hash แทนชื่อ/รหัสแปลงต้นฉบับ พิกัดยังไม่ยืนยันภาคสนาม
- [ชุดเตรียมทดลอง](../../research_data/five_province_history/gap_spatial_experiment/): `gap_spatial_prep_20261021_verified/` เป็นชุดที่ควรเริ่มอ่าน และเก็บ `gap_spatial_prep_20261021/` ไว้ตามประวัติ ทั้งสองมีชุดละ 7 ไฟล์ เป็น snapshot ของงานเตรียมเดียวกัน ไม่ใช่ผลทดลองอิสระสองครั้ง
- [สคริปต์รวบรวม/แยกข้อมูลต้นทาง](../../research_data/gap_public_sources/2026-10-20/): เฉพาะ `.py` ที่ตรวจแล้ว 13 ไฟล์ โดยรักษาโฟลเดอร์เดิมสำหรับ sibling imports ไม่รวมผลดาวน์โหลดหรือข้อมูลส่วนบุคคลที่สคริปต์อาจสร้างเมื่อรัน

รวม payload เดิมที่เพิ่ม 34 ไฟล์ พร้อมปรับเอกสาร manifest การส่งต่อ และ `.gitignore` ให้ยกเว้นเฉพาะไฟล์ที่ตรวจแล้ว snapshot ใหม่หรือไฟล์อื่นยังถูก ignore ตามเดิม

เพิ่ม `.gitattributes` เฉพาะข้อมูล snapshot เพื่อรักษาไบต์และ hash เดิมเมื่อ clone บน Windows หรือ macOS โดยไม่แปลง newline ของ CSV/JSON ที่ใช้ตรวจหลักฐาน ไม่เปลี่ยนค่า `core.autocrlf` ส่วนตัวของผู้ใช้

## เปิดบนเครื่องเพื่อน

ถ้า clone โปรเจกต์ไว้แล้วและไม่มีงานค้างที่ชนกัน:

```sh
git fetch origin
git switch codex/organize-project
git pull --ff-only origin codex/organize-project
```

ถ้ายังไม่มีโปรเจกต์:

```sh
git clone --branch codex/organize-project https://github.com/Ram14032517/durian-orchard-data-platform.git
```

Excel อยู่ที่ `docs/updates/attachments/GAP_5_PROVINCES_20261020.xlsx` เปิดด้วย Excel หรือ Numbers ส่วนแผนที่ให้ตั้งค่าเครื่องตาม [คู่มือ Mac](../setup/MAC_SETUP_TH.md) แล้วใช้ `00_OPEN_REPORT.command` ไม่เปิดหน้าแผนที่แบบ `file://` และไม่ต้องสร้างหมุดใหม่เพื่ออ่าน snapshot นี้

## สิ่งที่ไม่ส่งและข้อจำกัด

ไม่ส่งค่าลับ/ข้อมูลอุปกรณ์ส่วนตัว, `.build`/virtual environment, cache และผลดาวน์โหลดต้นทางที่มีชื่อเกษตรกร เลขประจำตัว ที่อยู่ หรือข้อมูลติดต่อ เก็บต้นทางส่วนนี้ในเครื่องเดิม ไม่ได้ลบ การ ignore ไม่ใช่การสำรองข้อมูล

Excel และพิกัดที่ส่งมีการลดข้อมูลส่วนตัวแล้ว แต่รหัสทะเบียน/พิกัดยังอาจเชื่อมกลับไปหาสวนได้ ไม่รับรองว่าเป็นข้อมูลนิรนามหรืออนุญาตให้ใช้ต่อได้ทุกวัตถุประสงค์ ต้องอ่านข้อจำกัดและแหล่งอ้างอิงใน Excel ก่อนใช้งานต่อ

สคริปต์ต้นทางบางตัวต้องมี HTML/PDF/CSV/manifest ต้นทางในเครื่อง และ dependencies เช่น `requests`, `openpyxl`, `pypdf`, `pdfplumber`, `lxml` หรือ `curl` จึงยัง rebuild หลักฐานเดิมทั้งหมดจาก clean clone ไม่ได้ ตัวสร้างแผนที่ต้องใช้ `records_sanitized.json` ต้นทางที่ไม่ได้เผยแพร่ในรอบนี้ ใช้ GeoJSON ที่ commit ไว้สำหรับเปิดแผนที่ได้ ไม่ควรรัน collectors เพียงเพื่อเปิดอ่าน เพราะอาจดาวน์โหลดข้อมูลส่วนบุคคลและเป็น snapshot คนละวัน

## สิ่งที่คงเดิม

ไม่มีการ fit, สร้าง prediction หรือคะแนนประเมินใหม่ `fit_count=0`, `metrics_created=false`, `train_eligible=false` ผลผลิตเป้าหมายยังเป็น 80 จังหวัด–ปี ไม่ใช่ผลผลิตจริงรายสวน และยังไม่มีหลักฐานว่าความแม่นเพิ่มกี่เปอร์เซ็นต์

ไม่เปลี่ยนโมเดล หน้าแรกสวนของฉัน รหัสอุปกรณ์ สัญญา API การรับข้อมูล IoT หรือ Supabase ไม่เปลี่ยน Docker allowlist หรือข้อจำกัดเส้นทาง local/cloud dashboard การเข้าถึงไฟล์ผ่าน GitHub สาธารณะจึงแยกจากการอนุญาตให้ดาวน์โหลดผ่านเว็บ IoT และการ push นี้ไม่ได้ merge เข้า `main`

## ผลตรวจรอบส่งต่อ

ตรวจ Excel แบบอ่านอย่างเดียว: ZIP สมบูรณ์, 10 ชีต, hash ตรงต้นฉบับ ไม่พบ macro/external workbook link หรือสูตรเรียกคำสั่งภายนอกในไฟล์ ตรวจ schema และ hash ของหมุดทั้งห้าจังหวัดกับ artifacts เตรียมทดลองทั้งสองชุดตรง manifest และตรวจสคริปต์ต้นทางแบบไม่รันดาวน์โหลด

ชุดทดสอบที่เลือก (`test_gap_publication`, `test_project_update`, `test_gap_asset_privacy`, `test_gap_map_layer`, `test_gap_map_build`, `test_gap_spatial_experiment`, `test_cloud_dashboard`) รัน 49 กรณี ผ่าน 48 กรณี อีกกรณีคือ `test_portable_context_contains_model_inputs_but_no_private_exports` ติด guard hash ของ snapshot โมเดลเดิมตาม [ข้อจำกัดที่บันทึกไว้ก่อนหน้านี้](../research/modeling/GAP_SPATIAL_INTEGRATION_TH.md) ไม่ได้แก้ข้อมูล ปิด guard หรือ train เพื่อทำให้ผ่าน จึงไม่อ้างว่าทดสอบทั้ง repository ผ่านทั้งหมด
