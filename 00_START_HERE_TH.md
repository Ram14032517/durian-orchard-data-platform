# เริ่มตรงนี้ — โปรเจกต์สวนทุเรียน

จัดโฟลเดอร์ใหม่ 19 ตุลาคม 2569 · เปิดโฟลเดอร์ repository นี้ใน VS Code แล้วกด **Command+Shift+V** บน Mac เพื่ออ่านหน้านี้

## วันนี้ต้องการทำอะไร

1. **เปิดแดชบอร์ด:** ดับเบิลคลิก [00_OPEN_REPORT.command](00_OPEN_REPORT.command) บน Mac หรือ [00_OPEN_REPORT.cmd](00_OPEN_REPORT.cmd) บน Windows หรือใช้ Run Task → **Durian: 01 เปิดแผนที่ (เริ่มตรงนี้)**
2. **ดูงานวิจัยและรายงานให้อาจารย์:** เริ่มที่ [ดัชนีงานวิจัย](research_data/internal_research/README_TH.md) แล้วเลือกผลทดลองที่ต้องการอ่าน ไม่ต้องรัน Training ใหม่
3. **อ่านโค้ดโมเดลผลผลิต:** เริ่มที่ [Ridge + VPD ขั้น 0–6](tools/durian_model/README_TH.md) ใช้ Run Task → `Durian ML` เมื่อต้องการทดลองรัน
4. **ทำงานกับเซนเซอร์สวน:** อ่าน [บริบทสวน](docs/orchard/ORCHARD_CONTEXT_TH.md) และ [การติดตั้งเซนเซอร์](docs/orchard/SOIL_SENSOR_INSTALLATION_TH.md) โค้ดบอร์ดอยู่ใน `iot/` และโค้ดรับข้อมูลอยู่ใน `api/`
5. **ตั้งค่าเครื่อง:** อ่าน [คู่มือ Mac](docs/setup/MAC_SETUP_TH.md) หรือ [README](README.md#start-here) เลือก Python environment ของโปรเจกต์ก่อนรัน Notebook

## เปิดโฟลเดอร์ไหน

- `web/` — แก้หน้าเว็บ: HTML อยู่ใน `templates/`, JavaScript และ CSS อยู่ใน `assets/`
- `tools/` — เปิดเซิร์ฟเวอร์ เตรียมข้อมูล และวิเคราะห์; `durian_model/` เป็นโมเดลผลผลิต, `notebooks/` เป็นสคริปต์สร้าง Notebook, `maintenance/` เป็นงานดูแล repository
- `iot/` และ `api/` — อุปกรณ์ เซนเซอร์ และปลายทาง Supabase/Google Sheets
- `data/` — ข้อมูลสวนจริง; `research_data/` — ข้อมูลระดับภูมิภาค ผลทดลอง และหลักฐานย้อนหลัง
- `notebooks/` — Notebook ที่เปิดอ่านได้ ส่วน [00_OPEN_ME.ipynb](00_OPEN_ME.ipynb) เป็นจุดเริ่มหลัก
- `models/` และ `ml/` — โมเดลที่บันทึกไว้กับโค้ดเซนเซอร์สวน
- `docs/` — คู่มือแยกตามเรื่อง เริ่มที่ [ดัชนีคู่มือ](docs/README_TH.md)
- `tests/` — ชุดทดสอบ; `output/` — รายงานที่สร้างแล้ว

## งานที่ใช้เป็นครั้งคราว

- **Durian: 02 อ่านรายงานรายเดือน** — เลือกจังหวัด ปี และเดือน
- **Durian: 03 เตรียม ZIP ข้อมูลเทรน (รักษา snapshot เดิม)** — รวมไฟล์ที่บันทึกไว้สำหรับส่งต่อ
- **Durian: 04 ทดสอบ Python** — ตรวจโค้ด ส่วน JavaScript ใช้ `node --test tests/*.js`
- **Durian: 05 รันโมเดล baseline (เขียนผลทดลองใหม่)** — รันเมื่อจะทดลองโมเดล เพราะเขียนผลใหม่

รายละเอียดการใช้แผนที่ การตั้งค่า cloud และข้อจำกัดอยู่ใน [คู่มือใช้งานฉบับละเอียด](docs/setup/WORKFLOW_DETAIL_TH.md) ส่วน [HTML ภาพรวมเดิม](docs/archive/PROJECT_OVERVIEW_2026-10-01.html) เป็นข้อมูล ณ 1 ตุลาคม ไม่ใช่สถานะล่าสุด

ข้อมูลสวนกับข้อมูลระดับจังหวัดมีขอบเขตต่างกัน อ่านที่มา หน่วย ช่วงเวลา และข้อจำกัดของแต่ละชุดก่อนใช้ฝึกโมเดล หน้าเว็บที่ใช้งานจริงสร้างไว้ใน `research_data/five_province_history/` จึงเปิดผ่าน launcher ด้านบนได้เหมือนเดิม
