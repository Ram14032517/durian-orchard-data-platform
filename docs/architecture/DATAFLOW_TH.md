# Dataflow ของระบบสวนทุเรียน

ฉบับ 1 พฤศจิกายน 2569 · อ่านจากโค้ดหลังรวม `origin/main` ถึง `09194ad` กับงานบน `codex/organize-project` ไม่ใช่หลักฐานว่า firmware, cloud หรือฐานข้อมูลจริงถูก deploy/ตรวจภาคสนามครบแล้ว

[เปิดฉบับภาพสำหรับ Safari](DATAFLOW_TH.html) · [จุดเริ่มโปรเจกต์](../../00_START_HERE_TH.md) · [ดัชนีหลักฐานทำเล่ม IoT](../operations/IOT_PLATFORM_REPORT_MAP_TH.md)

## ภาพรวมที่ต้องแยกให้ออก

ระบบมีหลายสายข้อมูล ไม่ใช่การเอา GAP กับเซนเซอร์ทั้งหมดเข้าโมเดลเดียว อากาศจาก API ไม่ใช่ค่าที่เซนเซอร์วัด ผลผลิตจังหวัดไม่ใช่ผลผลิตสวน และการกดสลับธีมไม่เกี่ยวกับการ train

```text
เซนเซอร์ → Gateway → farm-ingest → sensor_readings → Backend → สวนของฉัน
NASA POWER → ตรวจช่วงวัน/คุณภาพ + cache → /api/weather → อากาศ A/B
GAP + LDD → ตรวจพิกัด/ธงคุณภาพ → manifest + GeoJSON → แผนที่ / A/B
CSV จังหวัด → QC + เตรียมคุณลักษณะ → โมเดลที่บันทึกไว้ → ผลผลิตจังหวัด
พิกัดสวนที่เจ้าของยืนยัน → สิทธิ์บัญชี → Open-Meteo → พยากรณ์ส่วนตัว
แบบบันทึกผลผลิต → บัญชี + CSRF + ตรวจหน่วย → Supabase → ประวัติผลผลิตสวน
```

## 1. เซนเซอร์จริงและสวนของฉัน

ต้นทางอยู่ใน [iot/receiver_gateway](../../iot/receiver_gateway/) และ [iot/sender_1](../../iot/sender_1/) ต้องตรวจรุ่น firmware ที่อัปโหลดจริงแยกจากไฟล์ใน repository การสื่อสาร/ระยะส่งที่ทำงานจริงยังต้องมีบันทึกภาคสนาม

1. Gateway ส่ง JSON ที่มี `event_id`, เวลา, อุปกรณ์ และชุดค่าดิน/อากาศ ไปยัง [farm-ingest](../../api/supabase/functions/farm-ingest/index.ts)
2. Edge Function ตรวจ `POST` และ device key ฝั่งเซิร์ฟเวอร์ แปลงค่าที่ไม่ใช่ตัวเลขเป็น `null`, เก็บเวลา/quality flags/อายุข้อมูล แล้ว upsert `sensor_readings` ตาม `event_id` ช่วยกันการส่งซ้ำ **ไม่ได้รับรองการสอบเทียบ sensor จากการผ่าน ingest**
3. ingest ฉบับนี้เก็บหลักฐานเซนเซอร์ ไม่เก็บ `ndvi`, `forecast_7day` หรือ `forecast_hourly` จาก payload เป็นข้อมูลใหม่ในสายนี้ ตารางพยากรณ์เก่าอาจยังมีอยู่ แต่ไม่ควรอ้างว่ามีการอัปเดตจาก ingest ปัจจุบัน
4. [supabase_orchard.py](../../tools/supabase_orchard.py) อ่านเฉพาะ `ORCHARD_DEVICE_ID` ที่ตั้งไว้ ตรวจ freshness/validity แยกดินกับอากาศ คำนวณ VPD และทำ hourly/daily aggregation ประวัติฝนแบบ rolling ไม่ถูกบวกซ้ำให้กลายเป็นยอดฝนสะสมจริง
5. `GET /api/orchard-status` และ `GET /api/orchard-history` ส่งข้อมูลที่คัดไว้ให้ [Home.jsx](../../web/react/src/Home.jsx) แสดงตัวเลข กราฟ และสถานะ ข้อมูลหายไม่ใช่ศูนย์ สถานะ valid ไม่เท่ากับผลตรวจห้องปฏิบัติการ

หากมี `models/orchard_soil_6h.json` backend อาจเรียกโมเดลความชื้นล่วงหน้าตาม features ที่โมเดลต้องการ ผลนี้เป็นคนละโมเดลกับผลผลิตจังหวัด และไม่ใช่ผลวินิจฉัยโรค ถ้าต้องใช้ forecast ที่ขาดอยู่ ห้ามเอา Open-Meteo ฉบับใหม่มาสวมแทนโดยไม่ตรวจ feature/time contract

[Google Apps Script](../../api/google-apps-script/Code.gs) เป็นเส้นทางรับข้อมูลลง Sheets/`readings_15min` อีกแบบที่มีในโครงการ ไม่ใช่ฐานข้อมูลที่หน้า React อ่านโดยตรง ต้องยืนยัน configuration ของ Gateway และ deployment จริงก่อนเขียนในเล่มว่าใช้ช่องทางใดพร้อมกัน CSV ที่ export จาก Sheets ต้องมีขั้น clean/ตรวจหน่วยและเวลา ไม่กลายเป็นข้อมูล train โดยอัตโนมัติ

## 2. อากาศย้อนหลังและการเทียบพื้นที่ A/B

ผู้ใช้เลือก A/B จากจุดอ้างอิงจังหวัด อำเภอ หน่วยดิน หรือพิกัดตามทะเบียน GAP จากนั้น [Weather.jsx](../../web/react/src/Weather.jsx) ขอ `GET /api/weather?lat=...&lon=...&start=...&end=...`

Backend [serve_orchard_analysis.py](../../tools/serve_orchard_analysis.py) ตรวจพิกัดในขอบเขตไทย ช่วงวันไม่เกินสองปี และไม่เกินปัจจุบัน → อ่าน cache ที่ตรวจ SHA256/โครงสร้าง/อายุ → เรียก NASA POWER เมื่อจำเป็น → ส่งค่ารายวันพร้อม provenance กลับ

Frontend ใช้ข้อมูลเดียวกันทำกราฟ ตาราง และ CSV ไม่แทนช่องว่างด้วยศูนย์ ถ้าต้องใช้ไฟล์สำรองจุดจังหวัดจะแจ้งว่าเป็น province proxy ไม่ใช่อากาศตรงสวน การเรียกไม่สำเร็จหรือ session หมดอายุไม่ใช่เหตุให้สร้างข้อมูลทดแทนเอง

Cache/exports เก็บใต้ runtime ของ server: ค่าเริ่มต้น `research_data/five_province_history/` หรือ `ORCHARD_RUNTIME_DIR` ในสภาพแวดล้อม deploy ค่าเก็บ cache ไม่ใช่ ground truth และไม่ควรถูก push แบบเหมารวม

## 3. GAP และแผนที่ดิน

ไฟล์ registry ต้นทาง → [build_gap_map_layer.py](../../tools/build_gap_map_layer.py) ตรวจรูปแบบพิกัด CRS, พิกัดนอกขอบเขต, พิกัดขัดกัน, ข้อมูลซ้ำ และวันที่ทะเบียน → `gap_orchards/manifest.json` + `province_*.geojson` ที่มี SHA256/ธงคุณภาพ → [orchard_gap_layer.js](../../web/assets/js/orchard_gap_layer.js) กรอง/จัดกลุ่มเฉพาะจังหวัดและขอบจอ → [MapPage.jsx](../../web/react/src/MapPage.jsx)

หมุดที่แสดงใน snapshot รวม 32,871 จุด ยังเป็น **ตำแหน่งตามทะเบียน ไม่ใช่ทุกสวนที่ลงพื้นที่ยืนยันแล้ว** ระเบียนที่พิกัดไม่ผ่านเกณฑ์ไม่ได้ถูกย้ายไปกลางอำเภอเพื่อทำให้แสดงได้

หน่วยดินมาจาก GeoJSON ใน [priority_provinces/soil_layers](../../research_data/priority_provinces/soil_layers/) การจับคู่ใช้ตำแหน่งกับ geometry และข้อจำกัดของแผนที่ ไม่ใช่ผลตรวจดินรายสวน สีใช้แยกรหัส ไม่ใช่คะแนนความเสี่ยง/ความเหมาะสม

เมื่อเลือก GAP เป็น A/B จะเปลี่ยนพื้นที่อ้างอิงและคำขออากาศของ A/B เท่านั้น **ไม่เปลี่ยน `ORCHARD_DEVICE_ID`, เจ้าของสวน, พิกัดพยากรณ์ส่วนตัว หรือบัญชีผลผลิต** หากจับคู่ดินไม่ได้ ต้องคงสถานะไม่ทราบ

Local อ่านชุดหมุดที่ได้รับอนุญาตใน branch ได้ Cloud ปกติไม่เปิด static GAP/experimental preparations ส่วน Vercel มีเส้นทาง private Storage ที่ต้องตั้งค่าโดยผู้ดูแล ผ่าน login และ allowlist; เป็น signed URL อายุสั้น ไม่ใช่การเปลี่ยน bucket เป็น public ดู [orchard_private_assets.py](../../tools/orchard_private_assets.py) การมีโค้ดไม่ยืนยันว่ามีไฟล์หรือสิทธิ์บน cloud จริงแล้ว

## 4. ข้อมูลประวัติและโมเดลผลผลิตจังหวัด

Input หลัก `production_annual.csv`, `harvest_monthly.csv`, `weather_daily.csv` → [common.py](../../tools/durian_model/common.py) ตรวจ snapshot/หน่วย/ปี/จังหวัด → เตรียมช่วงดอก–ผลและตัวแปรอากาศ/VPD → ขั้นตอนฝึกและประเมิน **offline** ใน [durian_model](../../tools/durian_model/) → artifacts/audit/`ridge_vpd_final_model.json`

ข้อมูลเป้าหมายใน panel หลักมี 80 province-years ระหว่าง 2010–2025 สำหรับ 5 จังหวัด ไม่ใช่ 80 สวน ผลผลิตต่อไร่คำนวณจากผลผลิตตันและพื้นที่ให้ผลจริง ไม่ใช้ GAP area แทนพื้นที่ให้ผล

หน้าเว็บไม่ได้ train ทุกครั้งที่เปิด: ผู้ใช้กดประเมิน → `GET /api/province-estimate` → [orchard_current_context.py](../../tools/orchard_current_context.py) ตรวจโมเดลเดิม ผลผลิตปีก่อน และความพร้อมอากาศ → ใช้โมเดลเมื่อครบเงื่อนไข หรือคืน `pending_prior_yield`/สถานะรอพร้อมเหตุผล ไม่เอาผลทำนายปีก่อนมาปลอมเป็นค่าจริง

ผลออกเป็นประมาณการ **จังหวัด** ไม่ใช่หมุด GAP หรือสวนของผู้ใช้ งานทดลองขยายจังหวัด/ENSO/GAP มี preparation, seals และข้อจำกัด point-in-time แยก ไม่ถูก promote เป็น production จากการรวม branch หรือเปลี่ยนธีม

## 5. พยากรณ์อากาศส่วนตัวและคำแนะนำ

[orchard_forecast.py](../../tools/orchard_forecast.py) อ่านพิกัดที่เจ้าของยืนยันจาก configuration ฝั่งเซิร์ฟเวอร์ → `GET /api/orchard-forecast` ตรวจ session/เจ้าของ/การผูก sensor → เรียก Open-Meteo Forecast API (current/hourly/daily, 7 วัน) → ตรวจช่วงเวลา หน่วย ค่าที่ขาด และคำนวณ summary 24/48/72 ชั่วโมง → ส่งข้อมูลโดยไม่เปิดเผยพิกัดละเอียด

Cache พยากรณ์อยู่ในหน่วยความจำ อายุใช้งานปกติ 15 นาที ภาวะเรียกไม่สำเร็จมี cooldown และป้าย stale ไม่เขียนพิกัดลง disk cache พยากรณ์รายวัน/ET0 เป็นผลแบบจำลอง ไม่ใช่ฝนหรือความชื้นที่ sensor วัด และ ET0 ไม่เท่ากับคำสั่งให้น้ำรายต้น

[OrchardForecast.jsx](../../web/react/src/OrchardForecast.jsx), [OrchardAdvice.jsx](../../web/react/src/OrchardAdvice.jsx) และ [SevenDayForecast.jsx](../../web/react/src/SevenDayForecast.jsx) ใช้สถานะจริงของข้อมูล พยากรณ์ และระยะที่เจ้าของบันทึก เพื่อแสดงสิ่งที่ควรตรวจ ไม่สร้างเปอร์เซ็นต์ความเสี่ยงโรค ผลวินิจฉัย หรือสูตรปุ๋ยจากค่าหัววัดที่ยังไม่สอบเทียบ

ลิงก์ NABC ในหน้าเว็บเป็นแหล่งให้เปิดตรวจรายงาน ไม่ใช่ pipeline ที่ดึงรายงานโรคเข้ามาอัตโนมัติ และรายงานระดับจังหวัดไม่ใช่โรคที่ยืนยันในสวนนี้

## 6. บันทึกผลผลิตจริงกับบันทึกระยะ

ฟอร์มผลผลิตใน Home → `POST/PATCH /api/orchard-harvest` → [serve_orchard_cloud.py](../../tools/serve_orchard_cloud.py) ตรวจ session, CSRF และเจ้าของ → [orchard_harvest.py](../../tools/orchard_harvest.py) ตรวจหน่วย วันที่ สถานะ version/conflict → Supabase ผ่าน [migration 004](../../api/supabase/migrations/004_private_orchard_harvest.sql) → `GET /api/orchard-harvest` → ประวัติ/กราฟเฉพาะสวนและฤดู

ข้อมูล draft/ไม่ครบไม่ถูกนับเป็นผลผลิตจริงที่ใช้ประเมินอัตโนมัติ ยังต้องยืนยันหลักฐานการเก็บเกี่ยวและสิทธิ์ใช้ข้อมูลก่อนนำไปสร้างชุดฝึกใหม่ การบันทึกผลผลิตไม่เรียก train ให้เอง

บันทึกระยะ/สิ่งที่สังเกตใน Home เก็บใน localStorage ตามบัญชีและรหัสสวนของเบราว์เซอร์นี้ มีวันที่สังเกต **ยังไม่ sync เข้า Supabase** จึงไม่ใช่ชุด labels โรคที่ผ่านการยืนยัน หากเปลี่ยนเครื่อง/ล้าง storage อาจไม่มีบันทึกนี้

## 7. ธีมและการสร้างเว็บ

[orchard_theme.js](../../web/assets/js/orchard_theme.js) อ่านค่า `durian.orchard.theme.v1` → ถ้าไม่มีใช้ `prefers-color-scheme` → ตั้ง `data-theme` และ `color-scheme` ใน `<head>` ก่อนแสดงหน้า → [orchard_theme.css](../../web/assets/css/orchard_theme.css) เปลี่ยนสี → [ThemeControl.jsx](../../web/react/src/ThemeControl.jsx) ให้เลือก Light / Dark / ตามระบบ

บันทึกเฉพาะค่าธีม ไม่เรียก API, ไม่เก็บ telemetry/credentials เพิ่ม และไม่เปลี่ยน A/B/ฟอร์ม/ข้อมูลที่วัด เลือกตามระบบแล้ว OS เปลี่ยนตามได้ ค่าที่เลือกเองคงเดิม มีการ sync ระหว่างแท็บ origin เดียวกัน หาก storage ถูกบล็อก ยังสลับได้ในหน้าปัจจุบัน แผนที่ฐาน/สีชุดดิน/เส้นข้อมูลไม่ถูก invert เพื่อไม่เปลี่ยนความหมายข้อมูล

Source React/CSS → `node tools/build_orchard_react.mjs` (React + Tailwind รุ่นล็อก ทำงานบน Mac/Windows/Linux) → `orchard_app.js`/`orchard_app.css` → `tools/build_unified_orchard_map.py --reuse-bundled-data` ใส่ DATA snapshot เดิม, theme bootstrap และ fingerprint ของ assets → `UNIFIED_MAP.html` กับ `UNIFIED_MAP_CLASSIC.html`

การ build/push ไม่ train โมเดล ไม่เปลี่ยน audit/CSV เดิม และไม่ใช่คำสั่ง deploy หรือเปิดเผย private GIS เพิ่ม

## 8. Local, cloud และขอบเขตความปลอดภัย

- Local: [serve_orchard_analysis.py](../../tools/serve_orchard_analysis.py) เปิดเฉพาะ localhost ค่าเริ่มต้น `local_snapshot`; ถ้าเลือก `ORCHARD_DATA_SOURCE=supabase` จะอ่านสดตามเส้นทางส่วนตัวที่ตั้งค่าไว้ ไม่ fallback เป็น snapshot แล้วอ้างว่าข้อมูลสด เส้นทางหน้า `/home`/`map` ฯลฯ ที่ยังไม่ตั้ง private configuration เปิด static UI ได้เหมือน URL ของ launcher ไม่ได้ทำให้ API ส่วนตัวเปิดโดยไม่ login
- Local private API: ใช้ Flask auth เดิมผ่านตัว server ในเครื่อง การใช้ Supabase จริงต้องมี configuration และบัญชีฝั่งเซิร์ฟเวอร์ ประวัติผลผลิตไม่ย้ายไปเก็บแบบ fallback ใน browser
- Cloud: [serve_orchard_cloud.py](../../tools/serve_orchard_cloud.py) ใช้ Supabase, login/session, CSRF, owner checks และข้อจำกัด static files เดิม ไม่ให้ client ส่ง device/owner มายึดสิทธิ์ข้อมูลคนอื่น
- Credentials/device key/location config อยู่ฝั่ง server หรือไฟล์ ignored ไม่อยู่ใน bundle/เอกสารนี้ API identity ใช้ workspace/project fingerprints แทนการส่ง path/URL configuration จริงของเครื่อง
- `/api/project` บอก source/capabilities สำหรับ UI; boolean ว่าตั้งค่าไว้ไม่ใช่การรับรองว่าต่อฐานข้อมูลสำเร็จ ต้องดู response/เวลาวัดจริงอีกครั้ง

## 9. ถ้าจะทำโมเดลโรคในอนาคต

ต้องเก็บ outcome ที่มีวันเริ่มอาการ วันยืนยัน รหัสสวน/ต้น วิธีตรวจ ผู้ยืนยัน และกรณีไม่พบโรค → จับคู่ sensor/อากาศที่รู้ได้จริงก่อนเวลาทำนาย → แบ่งชุดตามเวลาและสวน ป้องกัน leakage → เทียบ baseline/โมเดลบนชุดประเมินเดียวกัน → ประเมิน recall/precision/calibration และยืนยันคำแนะนำกับผู้เชี่ยวชาญ

นี่เป็น **งานที่ยังไม่ implement เป็น production pipeline** GAP ช่วยเรื่องตำแหน่งและความละเอียดเชิงพื้นที่ แต่ไม่ได้ให้ labels โรคหรือรับประกันความแม่นดีขึ้นกี่เปอร์เซ็นต์ LLM อาจช่วยสรุปหลักฐานที่อ้างอิงได้ ไม่ใช่ตัวสร้าง ground truth

## จุดตรวจเมื่อตามหาข้อมูลผิดปกติ

1. ดู source/วันที่/สถานะก่อน: วัดจริง, พยากรณ์, snapshot หรือสถิติย้อนหลัง?
2. ตรวจ request ที่ browser เรียกและ response code — 401/403 เป็นเรื่องสิทธิ์, 503 อาจยังขาด configuration, ค่า `null` ไม่ใช่ศูนย์
3. เทียบ device/บัญชีฝั่ง server โดยไม่คัดลอก key มาในแชต ตรวจว่า A/B ไม่ได้ถูกใช้แทนจุดเซนเซอร์
4. ตรวจ quality flags/หน่วย/เวลาที่ sensor และ ingest ใช้ แล้วค่อยตรวจ aggregation/model ไม่ซ่อนข้อมูลขาดด้วยตัวเลขจำลอง
5. ตรวจ hashes/provenance และไฟล์ optional ที่ต้องมีสำหรับงานวิจัย ดู [คู่มือทดสอบ](../../tests/README_TH.md) ไม่แก้ seals ให้ตรงข้อมูลที่เปลี่ยนไป

เอกสารนี้อธิบายโค้ด ไม่สั่ง migrate, upload พิกัด, deploy firmware, ลบข้อมูล, train หรือแก้สิทธิ์ให้อัตโนมัติ
