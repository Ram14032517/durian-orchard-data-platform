# ชุดข้อมูลสำหรับทดลองโมเดลรายเดือน 5 จังหวัด

ข้อมูลบันทึกไว้ในเครื่องแล้ว ไม่ต้องล็อกอิน GitHub เปิด CSV ใน Jupyter / VS Code ได้ หรือคัดลอก `training_bundle.zip` ไปอีกเครื่องแล้วแตกไฟล์ ข้อมูลต้นฉบับที่มีอยู่ไม่ได้ถูกลบ และไม่ได้ลบ Google Sheets

## เริ่มจากอะไร

- `monthly_model_panel.csv`: หนึ่งแถวต่อจังหวัด–เดือน เป้าหมายคือผลผลิตเดือนนั้น (ตัน ทุกพันธุ์) และอากาศเดือนก่อนหน้า ณ จุดอ้างอิง NASA ของจังหวัด
- `manifest.json`: จำนวนแถว รายการไฟล์ต้นทาง SHA256 แหล่งอ้างอิง และรายชื่อ features ที่อนุญาตให้ใช้ใน baseline
- `training_bundle.zip`: รวม panel คู่มือนี้ manifest และสำเนาข้อมูลอากาศรายวัน/รายเดือน ผลผลิตรายปี/รายเดือน จุดอ้างอิง ตารางดิน และหลักฐานฤดู ใช้ศึกษาแบบ offline ได้
- ต้นฉบับ API NASA พร้อม provenance อยู่ที่ `../raw/` ในโปรเจกต์ ไม่รวมซ้ำใน ZIP นี้

นี่เป็น **ข้อมูลเตรียมสำหรับทดลอง** ยังไม่ได้ฝึกหรือประเมินโมเดล ไม่ใช่คำตอบเรื่องสุขภาพต้นหรือปริมาณน้ำที่ต้องรด

## คอลัมน์

| คอลัมน์ | ความหมาย |
|---|---|
| province_code / province_name | รหัสจังหวัดแบบข้อความ / ชื่อจังหวัด |
| year_ce / month / target_month | ปี ค.ศ. เดือน และเดือนของผลผลิตที่จะศึกษา |
| feature_month | เดือนก่อนหน้า target_month เสมอ รวมการข้ามปี |
| target_production_tonnes | ผลผลิตรายเดือนระดับจังหวัดจาก สศก. ช่องว่างคือไม่มีระเบียน ไม่ใช่ศูนย์ |
| lag1_temperature_c | อุณหภูมิเฉลี่ยเดือนก่อนหน้า °C |
| lag1_rain_mm | ฝนรวมเดือนก่อนหน้า มม. |
| lag1_humidity_pct | ความชื้นสัมพัทธ์เฉลี่ยเดือนก่อนหน้า % |
| lag1_solar_mj_m2_day | รังสีดวงอาทิตย์เฉลี่ยรายวันในเดือนก่อนหน้า MJ/m²/วัน |
| lag1_temperature_days / lag1_rain_days / lag1_expected_days | วันมีข้อมูลอุณหภูมิ / ฝน / วันตามปฏิทินของเดือนก่อนหน้า |
| eligible_for_baseline | 1 เมื่อมี target และ 4 features ไม่ว่าง โดยอุณหภูมิและฝนครบวันเท่านั้น ยังไม่รับรองคุณภาพทุกมิติ |
| exclusion_reason | เหตุผลที่ยังไม่ใช้ baseline (คั่นด้วย semicolon) ไม่มี target / อากาศไม่ครบ / feature ขาด |
| suggested_split | train ≤2021, validation 2022–2023, test 2024–2025, future_holdout ≥2026 ตามปีเป้าหมาย |

## ลองอ่านใน Jupyter

```python
import json
from pathlib import Path
import pandas as pd

folder = Path(r'C:\project\research_data\five_province_history\training')
df = pd.read_csv(folder / 'monthly_model_panel.csv', dtype={'province_code': str})
meta = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
usable = df[df.eligible_for_baseline.eq(1)].copy()
train = usable[usable.suggested_split.eq('train')]
valid = usable[usable.suggested_split.eq('validation')]
test = usable[usable.suggested_split.eq('test')]
X_train = train[meta['feature_allowlist']]
y_train = train[meta['target']]
print(df.shape, train.shape, valid.shape, test.shape)
```

รันสร้างใหม่จากรากโปรเจกต์: `python tools/prepare_monthly_training.py` ใช้ Python standard library ไม่ต้องติดตั้งเพิ่มสำหรับการเตรียมไฟล์ ส่วนตัวอย่างอ่านด้านบนใช้ pandas

## ก่อนเทรนจริง

1. เริ่ม baseline ค่ากลางผลผลิตแยกจังหวัด–เดือน โดย fit จาก train เท่านั้น แล้วเปรียบเทียบโมเดลอากาศด้วย MAE หน่วยตันและรายจังหวัด ห้ามสุ่มแถวข้ามปี ให้จูนเฉพาะ validation และกัน test ไว้
2. แยก missing ออกจาก 0 อย่าเติมทุกเดือนนอกฤดูเป็น 0 อัตโนมัติ ชุดที่มี target อาจเน้นเฉพาะฤดูเก็บเกี่ยว จึงยังสรุปความแม่นยำทั้งปีไม่ได้
3. ใช้เฉพาะ feature_allowlist อย่านำผลผลิตปีเดียวกัน ตัวแปรเป้าหมาย หรือข่าวที่เผยแพร่ภายหลังมาป้อนเป็น feature อากาศเดือนก่อนช่วยลดการมองอนาคต แต่ข้อมูลนี้เป็นฉบับย้อนหลังที่ปรับปรุงแล้ว ยังไม่รู้วันเผยแพร่/ความล่าช้าของทุกแหล่ง จึงไม่ใช่ backtest การพยากรณ์ใช้งานจริง
4. ปฏิทินกรมวิชาการเกษตรเป็นกรอบภูมิภาค ไม่ใช่ label ระยะจริงรายสวน จึงเก็บแยกและไม่ใช้เป็นคำตอบเทรน ข่าวไม่มีระเบียนไม่ได้แปลว่าไม่มีเหตุ
5. ตารางดินเป็นข้อมูลเชิงพื้นที่ ห้าม join จังหวัดแล้วทำซ้ำยอดผลผลิตให้ดินทุกชุด ยังไม่มีผลผลิตราย polygon ดินให้ฝึก supervised model
6. ชุดนี้ไม่มีข้อมูลเซนเซอร์สวน ไม่ปะปน indoor/outdoor หรือช่วง gateway ค้าง การนำเซนเซอร์มารวมต้องทำ QC อีกชุดก่อน และห้ามเติมอากาศค้างเป็นค่าจริง
7. ผลผลิตรวมเกี่ยวกับพื้นที่ให้ผล อายุ พันธุ์ และการจัดการด้วย โมเดลสัมพันธ์อากาศกับผลผลิตไม่ได้พิสูจน์สาเหตุหรือแนะนำการงดน้ำโดยตรง

แหล่งข้อมูลและขอบเขตเวลา: `../README_TH.md` และ `../PHENOLOGY_SOURCES_TH.md` ในโปรเจกต์ หรือไฟล์ sources/PHENOLOGY_SOURCES_TH.md ใน ZIP; NASA และ สศก. ระบุ URL ใน manifest
