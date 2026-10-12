# ข้อมูลสวนจริง — แยกจากข้อมูลภูมิภาค

อ่าน [บริบทสวน](../docs/ORCHARD_CONTEXT_TH.md) และ [กฎคลีนอากาศค้าง](../docs/WEATHER_CLEANING_TH.md) ก่อนใช้ตัวเลข

| โฟลเดอร์ | หน้าที่ |
| --- | --- |
| `export_2026-09-13/` | export รอบเดิม รวม readings_15min.csv ไม่ใช่ข้อมูลสดล่าสุด |
| `export_2026-10-09_live/` | snapshot ที่อ่านจากชีตสวนจริง 9 ต.ค. 2569; เซนเซอร์ถึง 19:00 น. ไม่อัปเดตเอง |
| `backups/` | สำรองและชุดแปลงในแต่ละรอบ เก็บ raw ไว้ย้อนตรวจ |
| `processed/` | ผลแปลง/คลีนและ quality flags แยกจาก raw |
| `analysis_soil_2026-09-19/` | สำเนาและผลตรวจรอบ 19 ก.ย. เช่น daily.csv, data_gaps.csv และ suspected_weather_flatlines.csv |

ลำดับใช้: สำรอง → ตรวจคุณภาพ → อ่านสำเนาคลีน → features → แบ่งตามเวลา → ทดลองโมเดล ไม่ลบต้นฉบับ รอบจัดระเบียบนี้ไม่ได้คลีนหรือเทรนข้อมูลสวนใหม่

บางโฟลเดอร์ถูก ignore และไม่มีหลัง clone การ push Git ไม่ใช่ backup ข้อมูลทั้งหมด อย่าเพิ่มไฟล์ส่วนตัวเข้า Git เพียงเพื่อให้เพื่อนรันได้ สำหรับ 5 จังหวัดเปิด [research_data](../research_data/README_TH.md) แทน ไม่ join ข้อมูลคนละระดับพื้นที่โดยไม่มีหลักฐานรองรับ

## ทดลองข้อมูลสวนล่วงหน้า 6 ชั่วโมง

โค้ดอยู่ที่ `ml/orchard_live_model.py`; อ่าน `readings_15min.csv` กับ `forecast_hourly.csv` ใน snapshot แล้วประเมินค่าเฉลี่ยความชื้นจุดเซนเซอร์รายชั่วโมงในอีก 6 ชั่วโมง ไม่ใช่ผลผลิตหรือความต้องการน้ำของทั้งสวน

```powershell
python -X utf8 ml/orchard_live_model.py --input-dir data/export_2026-10-09_live
python -X utf8 -m unittest discover -s tests -p test_orchard_live_model.py
```

ต้องมี numpy/pandas ใน Python ที่ใช้ ผลอยู่ใน `data/processed/orchard_live/LIVE_REPORT_TH.md` พร้อม JSON โมเดลและ CSV ผลทดสอบ เลือกรุ่น/alpha จาก validation ตามเวลาและเว้น label 6 ชั่วโมงก่อนจุดแบ่ง; เปรียบเทียบ persistence, ประวัติดิน, และประวัติดิน+อากาศ+พยากรณ์บนแถวเดียวกัน

การอัปเดต: export XLSX ใหม่จากชีตที่มีสิทธิ์อ่าน แล้วใช้ `tools/export_training_data.py <xlsx> <โฟลเดอร์ snapshot ใหม่>` ก่อนรันโมเดลกับ snapshot ใหม่นั้น อย่าเขียนทับ snapshot เก่า ไฟล์ข้อมูลส่วนตัวและผลคำนวณยังถูก ignore; โค้ดนี้ไม่ดึงชีตอัตโนมัติและไม่สั่งปั๊ม

รอบ 9 ต.ค. ได้ 288 จุดที่จับคู่ครบ (train/validation/test 166/52/58): test MAE persistence 4.372, ดิน 4.005, ดิน+อากาศ+พยากรณ์ 3.858 จุดเปอร์เซ็นต์ แต่ validation เลือก persistence เพราะช่วงนั้นค่าดินนิ่งกว่า จึงยังไม่เปลี่ยนรุ่นใช้งานจากคะแนน test เพียงอย่างเดียว ต้องสะสมพยากรณ์ที่ไม่ถูกเขียนทับและบันทึกเหตุการณ์ให้น้ำ/ฝนก่อนประเมินความเสถียรหลายช่วง
