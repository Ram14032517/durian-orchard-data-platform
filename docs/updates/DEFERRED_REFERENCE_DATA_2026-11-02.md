# ลดข้อมูลโหลดครั้งแรก

ทำต่อจากการลด re-render/Intl และแคชเซนเซอร์เดิม ใช้โครงสร้าง React/Flask เดิม ไม่เพิ่ม Library ไม่แก้ข้อมูลต้นทาง โมเดล หรือสิทธิ์ Supabase

## การเปลี่ยนแปลง

- `tools/serve_orchard_cloud.py`: แยก `soil_properties` และ `monthly_weather` จาก payload เริ่มต้นตอนให้บริการ HTML โดยไม่เขียนทับข้อมูลในไฟล์ `UNIFIED_MAP.html` อ่านและ parse ครั้งเดียวต่อรุ่นไฟล์ (mtime/size) ผ่าน LRU จำกัดสองรุ่น
- `/api/dashboard-data/map` คืนรายละเอียดชุดดินเดิม และ `/api/dashboard-data/seasons` คืนอากาศรายเดือนเดิม เฉพาะผู้ผ่าน authentication เท่านั้น ทุก API คง private/no-store ไม่รับ path หรือชื่อ field ตามอำเภอใจ
- ครอบคลุมทั้ง clean routes และ URL ไฟล์เดิมผ่าน Flask ไม่รวม HTML แบบ static/file:// ซึ่งยังมี payload เดิมเพื่อให้ Preview เก่าไม่เสีย
- `web/react/src/DeferredData.jsx`: เตรียมข้อมูลก่อน mount หน้าที่เกี่ยวข้อง มี Loading/Error/Retry คงข้อมูลที่โหลดแล้วเมื่อสลับหน้า ไม่เรียกข้อมูลเพิ่มเพราะเปลี่ยนภาษา
- โหลด Leaflet จาก CDN เดิมเฉพาะเปิดแผนที่ครั้งแรก มี timeout 15 วินาทีและลองใหม่ได้ ไม่ทำให้ Home/Yield รอ JavaScript แผนที่
- `web/react/src/main.jsx`: ครอบ Map และ Seasons ด้วยตัวเตรียมข้อมูล รักษา memo, state และเมนูเดิม
- `tools/serve_orchard_analysis.py`: ส่ง API กลุ่มข้อมูลนี้ผ่าน authentication เดิมของ local server
- `tests/test_cloud_dashboard.py`: ตรวจข้อมูลที่เลื่อนโหลดตรงกับต้นฉบับทุกค่า, HTML เริ่มต้นไม่มีสอง array ใหญ่, annual/phenology คงเดิม, URL เก่า/ใหม่เหมือนกัน, ผู้ไม่มีสิทธิ์เข้าไม่ได้, กลุ่มนอก allowlist ถูกปฏิเสธ และ hash ของ source ไม่เปลี่ยนจากการให้บริการ

## ผลตรวจ

ไฟล์ต้นทาง HTML 2,424,335 bytes; HTTP response ใหม่ 220,318 bytes (ลด 90.91%) หลัง gzip response ประมาณ 35,003 bytes เทียบไฟล์ต้นทาง gzip เดิมประมาณ 166 KB ทั้งหมดเป็นการลดขนาด HTML เริ่มต้น ไม่ใช่การลดขนาดข้อมูลทั้งหมดของระบบ JS bundle ยังประมาณ 1.17 MB ก่อนบีบอัด

Browser QA ที่ local port 8877 ใช้บัญชีทดสอบแยก ไม่สร้าง sensor/GAP ปลอม:

- Home และ Yield ไม่เรียก API ชุดดิน/อากาศรายเดือนหรือ Leaflet JS
- เปิดแผนที่แล้ว Leaflet render ได้ เปิด Seasons แล้วแสดงหัวข้อและข้อมูลได้
- การสลับกลับหน้าเดิมโหลดแต่ละกลุ่มเพียงครั้งเดียวในอายุหน้านั้น การ Reload ใหม่โหลดใหม่ตามปกติ
- จำลอง 503 เฉพาะ network response ใน browser ทดสอบ กดลองใหม่แล้วแสดงหน้าได้ ไม่แก้ข้อมูลจริง
- 360/390/768/1440px ไม่พบ horizontal overflow หรือ pageerror
- Focused unit tests: cloud 26, React/language 34; OAE เดิม 8

ผลดิบอยู่ `.build/deferred_qa/results.json` และสคริปต์ `.build/test_deferred_data.cjs` ภายในเครื่อง ไม่มีการ Deploy/Push/Commit หรือยืนยันความเร็วบนมือถือจริง ไม่ลดการตรวจสิทธิ์และคง Public HOLD
