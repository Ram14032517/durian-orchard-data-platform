# หาโค้ดที่ต้องใช้ — ไม่ต้องรันทุกไฟล์

ใช้งานปกติผ่าน Run Task ตาม [ลำดับเริ่มต้น](../00_START_HERE_TH.md) สคริปต์คงเส้นทางเดิมเพื่อรักษา import, builder และลิงก์ที่มีอยู่

| กลุ่ม | ไฟล์สำคัญ | หน้าที่ |
| --- | --- | --- |
| เปิด/อ่าน | `open_orchard_report.py`, `serve_orchard_analysis.py`, `read_monthly_report.py` | เปิดแผนที่, API/cache อากาศ, อ่านรายงาน ไม่ได้เทรน |
| หน้ารวม | `unified_orchard_map.html`, `orchard_monthly_report.js`, `orchard_monthly_report.css`, `build_unified_orchard_map.py` | template/components/builder แก้ต้นทางก่อน build ซึ่งเขียนหน้าที่สร้างใหม่ |
| หน้ารอบก่อน | `five_province_history.html`, `five_province_seasons.html`, `build_five_province_history.py`, `build_priority_province_map.py` | รายงานเฉพาะหัวข้อ ไม่ใช่ entry point ล่าสุด |
| Notebook | `build_monthly_notebook.py`, `build_*_notebook.py` | สร้าง Notebook อาจเขียนไฟล์ใหม่ อ่านก่อนรัน |
| เตรียมข้อมูล | `prepare_monthly_training.py`, `prepare_five_province_history.py`, `prepare_national_comparison.py`, `prepare_regional_orchards.py` | สร้างข้อมูลวิเคราะห์ ไม่ต้องรันเพื่อดูแผนที่ |
| โมเดลภูมิภาค | `train_monthly_production.py`, `analyze_annual_yield_windows.py`, `compare_annual_yield_features.py` | ทดลองโมเดล เขียนผลใน training ไม่ใช่ข้อสรุปสาเหตุ |
| แพคไฟล์ | `package_training_bundle.py` | สร้าง ZIP ถ้าไม่มี รักษา ZIP เดิม ไม่แก้ CSV |
| ข้อมูลสวน | `export_training_data.py`, `clean_stale_weather.py`, `analyze_live_soil_drydown.py` | export, flag ค้าง, ตรวจดิน อ่านพารามิเตอร์/output ก่อนรัน |
| ดึง/ตรวจแหล่ง | `fetch_orchard_weather.py`, `fetch_regional_ldd.py`, `inspect_regional_ldd.py`, `audit_regional_readiness.py` | อาจดาวน์โหลด ไม่จำเป็นทุกครั้งที่เปิดงาน |
| Secrets | `audit_staged_secrets.py`, `sanitize_firmware_secrets.ps1`, `move_gateway_ingest_secrets.ps1` | งานแยกด้าน config ส่วนตัว อ่านก่อนรัน ไม่ใช่ขั้นตอนเปิดแผนที่ |

Tests ปัจจุบันอยู่ใน `tests/`; `tools/test_*.py` เป็นการตรวจหัวข้อเฉพาะรอบก่อน ยังไม่ได้ย้าย import/API โค้ด ติดตั้งด้วย `requirements-national-analysis.txt` ตาม [README](../README.md#start-here)
