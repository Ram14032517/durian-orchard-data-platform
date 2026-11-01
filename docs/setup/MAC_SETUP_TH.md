# ใช้งานบน macOS

เปิดโฟลเดอร์ repository ใน VS Code แล้วใช้ Terminal → Run Task → Durian: 01 เปิดแผนที่ (เริ่มตรงนี้)
หรือดับเบิลคลิก `00_OPEN_REPORT.command` ใน Finder

อ่านจุดเริ่มปัจจุบันที่ [00_START_HERE_TH.md](../../00_START_HERE_TH.md) ด้วย Markdown Preview ส่วน [HTML ภาพรวมเดิม](../archive/PROJECT_OVERVIEW_2026-10-01.html) เปิดใน Safari/Chrome ได้โดยตรง เป็นข้อมูล ณ 1 ตุลาคม 2569

## Environment

เครื่องนี้ใช้ `.build/national-analysis-venv/bin/python` ซึ่งแยกจาก Python ของระบบ
VS Code Tasks เลือก executable ตามระบบปฏิบัติการ ส่วนค่า default interpreter ชี้โฟลเดอร์ environment
หาก VS Code จำ interpreter เดิม ให้กด Command+Shift+P → Python: Select Interpreter → Enter interpreter path
แล้วเลือก `.build/national-analysis-venv/bin/python` ภายใน repository
สำหรับ notebook ให้ใช้ Select Kernel → Python Environments แล้วเลือก environment เดียวกัน

สำหรับ Mac เครื่องใหม่ ใช้ Python 3.11 ขึ้นไปและสร้าง environment บนเครื่องนั้น:

```sh
python3 -m venv .build/national-analysis-venv
.build/national-analysis-venv/bin/python -m pip install -r tools/requirements-national-analysis.txt
```

อย่าคัดลอก environment ข้ามเครื่อง โดยเฉพาะ environment จาก Windows

## คำสั่งที่ใช้บ่อย

รันจากโฟลเดอร์ repository:

```sh
.build/national-analysis-venv/bin/python tools/open_orchard_report.py
.build/national-analysis-venv/bin/python tools/read_monthly_report.py --province 84 --year 2025 --month 7
.build/national-analysis-venv/bin/python -m unittest discover -s tests -v
node --test tests/test_weather_fallback.js tests/test_weather_export.js
```

แผนที่ต้องเปิดผ่านเซิร์ฟเวอร์ที่ launcher เริ่มให้ ส่วน docs/archive/PROJECT_OVERVIEW_2026-10-01.html เปิดจากไฟล์ได้โดยตรง
ตัว launcher จะพิมพ์ URL ที่ใช้งานจริงและไม่หยุดโปรแกรมอื่นที่ใช้พอร์ตอยู่

เมื่อต้องทดสอบทุกส่วน รวมเว็บ cloud และ GIS ให้ติดตั้งเพิ่มด้วย `python -m pip install -r tools/requirements-test.txt` ใน environment ของโปรเจกต์ แล้วรัน `python -m unittest discover -s tests` และ `node --test tests/*.js tests/*.cjs` เทสต์ React ต้องติดตั้ง packages ที่ล็อกไว้ก่อนด้วย `pnpm --dir web/react install --frozen-lockfile --ignore-scripts`

ถ้าแก้หน้า React/ธีม ให้ใช้ `node tools/build_orchard_react.mjs` แล้ว `python tools/build_unified_orchard_map.py --reuse-bundled-data` เพื่อ build JS/CSS ด้วยข้อมูลเดิม ดู [คู่มือ frontend](../../web/react/README_TH.md) และ [Dataflow](../architecture/DATAFLOW_TH.html)

## เลือกแหล่งข้อมูล IoT ในเครื่อง

ค่าเริ่มต้นเป็น `local_snapshot` และไม่เชื่อมต่อ Supabase อัตโนมัติ แม้จะมี credentials ใน environment ถ้าต้องการอ่านข้อมูลสดและตั้ง `SUPABASE_URL`, server key และ `ORCHARD_DEVICE_ID` ฝั่งเซิร์ฟเวอร์ไว้แล้ว ให้หยุดเซิร์ฟเวอร์ของงานนี้ก่อน แล้วเริ่มด้วย:

```sh
ORCHARD_DATA_SOURCE=supabase .build/national-analysis-venv/bin/python tools/serve_orchard_analysis.py --port 8871
```

ตั้งค่าลับด้วยวิธีเดิมของเซิร์ฟเวอร์ ไม่ใส่ลง Git/แชต ไม่ใส่ key ใน JavaScript ฝั่ง browser โหมดสดจะไม่ fallback เป็น snapshot เมื่อเชื่อมต่อไม่ได้ หน้าเว็บแสดงแหล่งข้อมูลและบอกการตั้งค่าที่ยังขาด ส่วนเว็บ cloud ใช้ Supabase ตามเดิม ไม่เปลี่ยนตามตัวแปรโหมด local นี้

รายละเอียดการตรวจและข้อจำกัดของเทสต์อยู่ที่ [tests/README_TH.md](../../tests/README_TH.md)
