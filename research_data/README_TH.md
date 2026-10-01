# ข้อมูลและผลวิเคราะห์ภูมิภาค

เริ่มที่ **five_province_history** สำหรับงานปัจจุบัน ไม่ต้องเปิดทุกโฟลเดอร์

| ลำดับ | ตำแหน่ง | หน้าที่ |
| --- | --- | --- |
| 1 | [five_province_history/README_TH.md](five_province_history/README_TH.md) | รายงาน 5 จังหวัดและที่มา |
| 2 | `five_province_history/UNIFIED_MAP.html` | หน้าปัจจุบัน เปิดผ่าน launcher/server ไม่ใช่ file:// |
| 3 | [training/README_TH.md](five_province_history/training/README_TH.md) | CSV, manifest, split, ผลโมเดล |
| 4 | `five_province_history/exports/` | CSV เปรียบเทียบ A/B ที่บันทึกในเครื่อง |
| 5 | `priority_provinces/` | ขอบเขตและชั้นดินที่หน้าปัจจุบันใช้ ห้ามลบเพื่อเคลียร์ Explorer |
| 6 | `regional_orchards/`, `thailand_comparison/`, `soil_evidence_chanthaburi/` | ผลศึกษาหัวข้อรอบก่อน ไม่ใช่หน้าหลักล่าสุด |
| 7 | `external/`, `five_province_history/evidence/`, `five_province_history/point_weather_cache/` | ข้อมูลดาวน์โหลด หลักฐาน cache บางส่วนอยู่เฉพาะเครื่อง |

ใน training: `monthly_model_panel.csv` คือ panel รายเดือน; `annual_yield_windows_panel.csv` คือ panel window รายปี; metrics/predictions เป็นผลทดลอง ไม่ใช่ข้อมูลดิบฝึกเพิ่มโดยอัตโนมัติ

อากาศ NASA POWER เป็นข้อมูลกริด ผลผลิตเป็นรายจังหวัด ไม่ใช่การวัดรายต้น ขอบเขตดินไม่ได้ยืนยันสวนหรือความอุดมสมบูรณ์จริง อ่าน provenance/ข้อจำกัดก่อน join หรือส่งต่อ

รายละเอียด CSV สวนที่เคยคัดมาที่ราก research_data และ XLSX ต้นทางในรอบแรกยังอ่านได้ใน [คู่มือเดิมรอบ 17 ก.ย.](../docs/archive/RESEARCH_DATA_OVERVIEW_2026-09-17_TH.md) เก็บไว้เป็นประวัติ ไม่ใช่รายการข้อมูลล่าสุด
