# เว็บสวนบน Vercel — สถานะส่งมอบ

ตรวจเมื่อ 31 ตุลาคม 2569

เว็บใช้งานจริง: https://map-durian-analysis.vercel.app

เปิดหน้าหลัก: https://map-durian-analysis.vercel.app/research_data/five_province_history/UNIFIED_MAP.html

## สิ่งที่เชื่อมสำเร็จ

- Vercel project `durian6/map-durian-analysis` สถานะ Ready; deployment `5oiibvCG3ZU9c1nv6rRopHgUeNqE`
- ใช้ React / Flask / Supabase เดิม ไม่เปลี่ยนโมเดล ML และไม่ฝึกโมเดลใหม่
- เข้าสู่ระบบด้วยบัญชีเว็บเดิมก่อนอ่านข้อมูลสวนและ GIS
- Supabase Storage bucket `durian-gis-private` เป็นส่วนตัว เก็บเฉพาะ manifest, GAP 5 จังหวัด และดิน 5 จังหวัด รวม 11 ไฟล์ ตามที่เจ้าของอนุญาต
- ตรวจ SHA256 หลังอัปโหลดครบ 11 ไฟล์ ตรงต้นฉบับ รวมไฟล์ดินขนาด 12,266,103 bytes
- ไฟล์ GIS ส่งผ่านลิงก์ชั่วคราว 60 วินาทีหลังตรวจบัญชี เพื่อไม่ติดข้อจำกัดขนาด response ของ Vercel ห้ามแชร์ลิงก์ชั่วคราว
- ตั้งค่าฝั่งเซิร์ฟเวอร์เป็น Secret: SUPABASE_URL, SUPABASE_SECRET_KEY, DASHBOARD_USER, DASHBOARD_PASSWORD, ORCHARD_DEVICE_ID, ORCHARD_GIS_PRIVATE_BUCKET, ORCHARD_FORECAST_LOCATION_JSON
- ไม่คัดลอก secret ลง frontend/Git และปิดตัวเลือกใช้ข้อมูลโปรเจกต์ปรับปรุงโมเดลของ Vercel
- คง Public Release HOLD ไม่มี public GIS bucket และไม่อัปโหลดทะเบียนดิบหรือชื่อบุคคล

## หลักฐานการตรวจ

Focused Python tests ผ่านรวม 52 tests: private assets, Vercel package, cloud authentication, forecast, launcher และ harvest; ไม่รัน repo-wide หรือฝึก ML

ตรวจ URL ออนไลน์จริง:

| รายการ | ผล |
|---|---|
| healthz | 200 |
| API ส่วนตัวเมื่อยังไม่ล็อกอิน | 401 |
| หน้าหลักและ GIS เมื่อยังไม่ล็อกอิน | ส่งไปหน้าเข้าสู่ระบบ |
| session / sensor status / forecast / harvest / history หลังล็อกอิน | 200 |
| history | Supabase ตอบกลับ 24 แถว |
| forecast | Open-Meteo ตอบกลับ fresh |
| GIS หลังล็อกอิน | redirect ไป signed URL ของ Supabase ที่อนุญาต |
| GAP manifest | 200 ครบ 5 จังหวัด |
| public Storage URL | ถูกปฏิเสธ 400 |
| secret path / private export ที่ไม่อนุญาต | 404 |
| session cookie | Secure |

ตรวจ Browser จริงบนเว็บ Production: หน้าสวนแสดง API อากาศปัจจุบันและพยากรณ์รายชั่วโมง/7 วัน; แผนที่จันทบุรีแสดงหมุด GAP, เลือก A/B ได้, หน่วยดินแสดง legend 83 ประเภทตามรหัส; เปิดหน้าผลผลิต ฤดูกาล และอากาศได้ โดยไม่สั่งประเมินโมเดลใหม่ ไม่พบ console error ในการตรวจแผนที่

ตรวจมือถือด้วย viewport override 390×844: DOM รายงาน clientWidth=scrollWidth=375 ไม่มีหน้าล้นแนวนอน ณ จุดตรวจ และคืนขนาดหน้าจอแล้ว ไม่ใช่การทดสอบทุกอุปกรณ์

ภาพหลักฐาน: `C:\project\.build\react-qa\vercel_home.png`

## อัปเดตเว็บครั้งถัดไป

จาก C:\project ใช้ Python environment เดิม:

```powershell
& ./.build/national-analysis-venv/Scripts/python.exe -B -X utf8 tools/prepare_vercel_orchard.py --private-gis
```

อัปโหลดเฉพาะ `C:\project\.build\vercel_orchard_private` ผ่าน Choose a folder to deploy ในโปรเจกต์ Vercel เดิม แล้ว Deploy to Production ห้ามอัปโหลด C:\project ทั้งก้อน และอย่าใช้ Redeploy source เก่าหลังเปลี่ยนโค้ด

ชุด deploy ใช้ Python 3.12 / Flask หนึ่ง Function, Singapore, maxDuration 60 วินาที; entrypoint `app:app` ใน pyproject.toml ใช้ React bundle ที่ build แล้ว ไม่ต้องเปิดเครื่อง local ค้างไว้

`tools/upload_orchard_private_gis.py` ใช้สำหรับไฟล์ allowlist เดิมเท่านั้น ตรวจ private bucket และ hash ก่อน/หลัง ไม่เขียนทับไฟล์ที่ hash ต่าง

## ข้อจำกัดที่ยังคงอยู่

- ข้อมูลเซนเซอร์จริงตอบกลับเป็น stale_live และดินอาจ invalid ตามฮาร์ดแวร์/ข้อมูลต้นทาง ไม่ได้แทนด้วยค่าจำลองหรือถือว่าเซนเซอร์ปกติ
- Open-Meteo เป็นอากาศจากแบบจำลองกริด แยกจากเซนเซอร์ ใช้ Free API เฉพาะ non-commercial ตามเงื่อนไขและเครดิตเดิม
- แคชใน /tmp เป็นชั่วคราวต่อ instance ไม่ใช่ฐานข้อมูล และยังไม่รับรอง shared cache/rate limit สำหรับผู้ใช้จำนวนมาก
- ประวัติผลผลิตสวนถาวรอยู่ใน Supabase ตรวจ owner และ CSRF แต่ไม่ได้เพิ่ม/แก้ผลผลิตทดสอบปลอมบนบัญชีจริงในการตรวจออนไลน์ ใช้ automated tests ตรวจ CRUD/สิทธิ์แทน
- ระยะการผลิตที่ยังบันทึก browser-local ไม่ sync ข้ามเครื่อง
- CSV หน้า React ดาวน์โหลดฝั่งเบราว์เซอร์; endpoint ส่งออกเก่าที่เขียนไฟล์บนเซิร์ฟเวอร์ไม่รับรองข้าม instance
- คำขออากาศย้อนหลังยาวอาจเกินเวลา Function ยังไม่ได้ทดสอบทุกช่วงปี/ทุกตัวกรอง
- โมเดลจังหวัดเดิมยังเป็นผลทดลอง ไม่ใช่คำทำนายผลผลิตสวน ไม่มีการรับรองโมเดลใหม่จากการ deploy
