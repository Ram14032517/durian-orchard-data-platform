# ระบบจัดเก็บข้อมูลสวน IoT

โครงสร้างนี้ใช้ Supabase เป็นฐานข้อมูลหลัก และ Google Sheets เป็นสำเนาอิสระอีกหนึ่งชุด

## รอบข้อมูล

- ESP32 เซนเซอร์ดิน: อ่านและส่ง LoRa ทุก 15 นาที
- Gateway: รวมค่าดินล่าสุดกับอากาศ Tuya แล้วส่ง Supabase และ Google Sheets
- TMD forecast: ดึงวันละครั้ง และเก็บแยกตามวันที่ออกพยากรณ์/วันที่พยากรณ์
- NDVI: ตรวจวันละครั้ง แต่ใช้เวลาถ่ายภาพดาวเทียมเป็นคีย์ จึงไม่เกิดแถวซ้ำถ้าภาพยังไม่เปลี่ยน

## ติดตั้ง Supabase

1. สร้าง Supabase project แล้วเปิด SQL Editor
2. รัน `supabase/migrations/001_iot_schema.sql`
3. สร้าง Edge Function ชื่อ `farm-ingest` แล้วใส่โค้ดจาก `supabase/functions/farm-ingest/index.ts`
4. ตั้ง Secret `DEVICE_INGEST_KEY` เป็นข้อความสุ่มยาวอย่างน้อย 32 ตัวอักษร
5. Deploy function โดยปิด JWT verification สำหรับ endpoint อุปกรณ์ แล้วใช้ `x-device-key` ตรวจแทน
6. นำ URL รูปแบบ `https://PROJECT.supabase.co/functions/v1/farm-ingest` ใส่ใน `SUPABASE_INGEST_URL`

ห้ามใส่ Supabase service-role key ลง ESP32 เพราะคีย์นี้อยู่ใน Edge Function เท่านั้น

## ติดตั้ง Google Sheets

1. สร้าง Google Sheet เปล่าหนึ่งไฟล์
2. เปิด Extensions > Apps Script และวาง `google-apps-script/Code.gs`
3. ใน Project Settings > Script properties เพิ่ม `SPREADSHEET_ID` และ `DEVICE_INGEST_KEY`
4. Deploy > New deployment > Web app, Execute as Me, Who has access = Anyone
5. นำ URL `/exec` ใส่ใน `GOOGLE_SHEETS_URL`

สคริปต์จะสร้างแท็บ `readings_15min`, `ndvi_daily`, และ `forecast_daily` ให้อัตโนมัติ

## ตั้งค่า Gateway

ใน `receiver_gateway.ino`:

- ใส่ URL ทั้งสองตัว
- ใส่ `DEVICE_INGEST_KEY` ให้ตรงกับ Supabase และ Apps Script
- เปลี่ยน `ENABLE_SUPABASE` และ `ENABLE_GOOGLE_SHEETS` เป็น `true`

ก่อนใช้งานจริงให้ออก Wi-Fi password, Tuya secret, TMD token และ Agro API key ชุดใหม่ แล้วแยกค่าลับออกจากไฟล์ที่นำขึ้น Git

## รูปแบบ JSON ที่รองรับ

Gateway ต้องมี `device_id`, `event_id`, `recorded_at`, `soil`, และ `weather` ส่วน `ndvi` กับ `forecast_7day` เป็น optional โค้ด gateway รุ่นที่รวม TMD/NDVI สามารถส่งโครงสร้างเดิมเข้าปลายทางนี้ได้ทันที

## Export ข้อมูลสำหรับวิเคราะห์และเทรนโมเดล

ดาวน์โหลด Google Sheets เป็นไฟล์ `.xlsx` แล้วรัน:

```powershell
python tools/export_training_data.py "Farm IoT Data.xlsx" "data/export_YYYY-MM-DD"
```

สคริปต์จะแยกตารางต้นทางเป็น CSV และสร้าง `sensor_training_unlabeled.csv`
ที่เรียงตามเวลา ตัด `event_id` ซ้ำ และเพิ่ม time features แบบวงรอบ พร้อม
`data_quality_report.json` สำหรับตรวจ missing values และช่วงเวลาที่ข้อมูลขาดหาย

ข้อมูลชุดปัจจุบันยังไม่มี `symptom_label` หรือ `disease_label` จึงควรใช้สำหรับ EDA
หรือ anomaly detection ก่อน หากต้องการเทรน supervised model ให้เพิ่มตารางบันทึกอาการ
ที่มี `tree_id`, เวลาที่ตรวจ, ชนิดอาการ/โรค และผลยืนยันจากผู้ตรวจ แล้ว join ตามต้นและเวลา

ไม่ควร commit โฟลเดอร์ `data/export_*` ขึ้น Git เพราะข้อมูลจะโตต่อเนื่องและอาจเป็นข้อมูลจริงจากสวน

## Baseline ตรวจข้อมูลผิดปกติ

สร้างโมเดลสถิติและไฟล์ที่มี anomaly/data-quality flags:

```powershell
python ml/train_statistical_baseline.py `
  data/export_YYYY-MM-DD/sensor_training_unlabeled.csv `
  data/processed/sensor_scored.csv `
  models/statistical_baseline.json
```

เงื่อนไขหลัก:

- `weather_missing`: ค่าอากาศหลักขาดอย่างน้อยหนึ่งค่า
- `weather_stale`: ค่าอากาศหลักเหมือนเดิมต่อเนื่องตั้งแต่ 60 นาทีขึ้นไป
- `invalid_range`: ค่าอยู่นอกขอบเขตทางกายภาพ เช่น humidity นอก 0–100%
- `is_anomaly`: ค่าเบี่ยงจาก median มากกว่า 4.5 robust z-score หลังตัดข้อมูลเสีย
- `wet_environment_alert`: ความชื้นดิน/อากาศอยู่กลุ่มสูงของข้อมูล หรือมีฝน อย่างน้อย 2 เงื่อนไข

`wet_environment_alert` เป็นเพียงลำดับความสำคัญสำหรับตรวจสวน ไม่ใช่ผลวินิจฉัยโรค
