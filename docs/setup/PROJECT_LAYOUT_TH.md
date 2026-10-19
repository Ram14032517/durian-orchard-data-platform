# โครงสร้างโปรเจกต์

เริ่มงานประจำวันที่ [00_START_HERE_TH.md](../../00_START_HERE_TH.md) แล้วเปิดเฉพาะโฟลเดอร์ที่เกี่ยวข้อง

```text
durian-orchard-data-platform/
├── 00_START_HERE_TH.md        จุดเริ่มอ่าน
├── 00_OPEN_REPORT.command    เปิดแดชบอร์ดบน Mac
├── 00_OPEN_REPORT.cmd        เปิดแดชบอร์ดบน Windows
├── 00_OPEN_ME.ipynb          Notebook หลัก
├── web/
│   ├── templates/           โครงหน้า HTML
│   └── assets/
│       ├── js/              การทำงานในหน้าเว็บ
│       └── css/             รูปแบบหน้าเว็บ
├── tools/
│   ├── durian_model/        โมเดลผลผลิต ขั้น 0–6 และงานทดลอง
│   ├── notebooks/           สคริปต์สร้าง Notebook
│   ├── maintenance/         จัดการ configuration ส่วนตัว
│   └── *.py                 API, builder และสคริปต์วิเคราะห์ที่ใช้ร่วมกัน
├── iot/                     โค้ดบอร์ดและคู่มือเซนเซอร์
├── api/                     Supabase และ Google Apps Script
├── data/                    ข้อมูลสวนจริง
├── research_data/           ข้อมูลภูมิภาค ผลทดลอง และหลักฐานต้นทาง
├── ml/                      โค้ดโมเดลเซนเซอร์สวน
├── models/                  โมเดลที่บันทึกไว้
├── notebooks/               Notebook ที่เปิดอ่านได้
├── docs/
│   ├── setup/               ติดตั้ง เริ่มเรียน และแผนผังนี้
│   ├── orchard/             สวน เซนเซอร์ และการคลีน
│   ├── research/modeling/   รายงานโมเดลและการประเมิน
│   ├── research/spatial/    ดิน GIS และข้อมูลรายอำเภอ
│   ├── operations/          สถานะ ส่งต่อ และการเผยแพร่
│   ├── design/              แนวทางหน้าตาเว็บ
│   └── archive/             เอกสารและภาพรวมรุ่นเก่า
├── tests/                   ชุดทดสอบ
└── output/                  รายงานที่สร้างแล้ว
```

## ตำแหน่งที่เปลี่ยน

- HTML ต้นแบบที่เคยอยู่ `tools/*.html` ย้ายไป `web/templates/`
- JavaScript และ CSS จาก `tools/` ย้ายไป `web/assets/js/` และ `web/assets/css/`
- ตัวสร้าง Notebook ย้ายไป `tools/notebooks/` รันจาก root เช่น `python -m tools.notebooks.build_monthly_notebook` ตัวสร้างอาจเขียนผลใหม่ ควรอ่าน [คู่มือ](../../tools/notebooks/README_TH.md) ก่อนรัน
- สคริปต์ดูแล secrets ย้ายไป `tools/maintenance/`
- คู่มือทั่วไปย้ายเข้าหมวดใน `docs/` เลือกอ่านผ่าน [ดัชนีคู่มือ](../README_TH.md)
- คู่มือเริ่มต้นฉบับเต็มอยู่ที่ [WORKFLOW_DETAIL_TH.md](WORKFLOW_DETAIL_TH.md) และ HTML ภาพรวมเดิมอยู่ใน [archive](../archive/PROJECT_OVERVIEW_2026-10-01.html)

ตัวเปิดแผนที่ เส้นทางไฟล์ที่เซิร์ฟเวอร์ให้บริการ ข้อมูลสวน โมเดลที่บันทึกไว้ และผลทดลองยังใช้ตำแหน่งเดิม การจัดหมวดครั้งนี้ไม่ได้คลีนข้อมูลหรือเทรนโมเดลใหม่

## หลักฐานวิจัยย้อนหลัง

`research_data/` และเอกสารรุ่น `docs/phase11d_20261012_v1/` เก็บไบต์เดิมไว้ รายงาน 6 ไฟล์ในชั้น `docs/` ที่เป็น input ของ scientific seals ยังอยู่ตำแหน่งเดิม เปิดได้จาก [ดัชนีเชิงพื้นที่](../research/spatial/README_TH.md)

บางการทดลองย้อนหลังบันทึก hash ของไฟล์ทั้ง workspace รวมถึงคู่มือและตำแหน่งสคริปต์ก่อนจัดหมวด การทำซ้ำการทดลองรุ่นนั้นแบบตรงทุกไบต์ต้องใช้ revision หรือ source snapshot ที่บันทึกกับรุ่นนั้น ไฟล์ manifest เดิมและกฎตรวจ hash ยังเก็บไว้ Tasks ปกติและโมเดลขั้น 0–6 ตั้งเส้นทางตามโครงสร้างปัจจุบันแล้ว

## ผลตรวจหลังจัดโฟลเดอร์

ส่วนที่เกี่ยวกับการย้ายผ่าน Python 40 รายการ และ JavaScript 30 รายการ ได้แก่ลิงก์คู่มือ โครงสร้างอุปกรณ์ แผนที่ การส่งออก launcher และ API ตรวจ syntax ตัวสร้าง Notebook ทั้ง 6 ไฟล์และ launcher บน Mac แล้ว เอกสาร scientific inputs ทั้ง 6 ไฟล์มี SHA256 เดิม

ชุดทดสอบทั้งโปรเจกต์ยังพบ 39 errors ด้านข้อมูลทดลองเก่าขาดหรือ hash ของ snapshot ไม่ตรง เทียบกับ revision `0fc82d1` ก่อนจัดโฟลเดอร์แล้ว พบปัญหาเดียวกันทั้งหมด การจัดโฟลเดอร์นี้ไม่ได้สร้างข้อมูลที่ขาดหรือเทรน/ปรับ snapshot เพื่อให้ผ่าน guard
