# หาโค้ดที่ต้องใช้ — ไม่ต้องรันทุกไฟล์

## โค้ดโมเดลผลผลิตตามขั้น 0-6

เปิด [durian_model/README_TH.md](durian_model/README_TH.md) สำหรับไฟล์ Python แยกทุกขั้นที่รันใน VS Code ได้ ตั้งแต่ตรวจข้อมูล แบ่งปี สร้าง VPD เทรน Ridge ตรวจ coefficients ประเมินผล และ demo prediction ย้อนหลัง ผลอยู่ใน `research_data/five_province_history/training/ridge_vpd_*` ไม่เปลี่ยนข้อมูลดิบหรือ benchmark เดิม

ใช้งานปกติผ่าน Run Task ตาม [ลำดับเริ่มต้น](../00_START_HERE_TH.md) โค้ดหน้าเว็บอยู่ใน [web/](../web/README_TH.md), ตัวสร้าง Notebook อยู่ใน [notebooks/](notebooks/README_TH.md), งานดูแล configuration อยู่ใน [maintenance/](maintenance/README_TH.md) ส่วนสคริปต์วิเคราะห์และ API คงอยู่ที่นี่

| กลุ่ม | ไฟล์สำคัญ | หน้าที่ |
| --- | --- | --- |
| เปิด/อ่าน | `open_orchard_report.py`, `serve_orchard_analysis.py`, `read_monthly_report.py` | เปิดแผนที่, API/cache อากาศ, อ่านรายงาน ไม่ได้เทรน |
| หน้ารวม | `../web/templates/unified_orchard_map.html`, `../web/assets/`, `build_unified_orchard_map.py` | แก้ template/components แล้ว build เพื่อสร้างหน้าที่ใช้จริง |
| ทดลองดิน–ผลผลิตรายอำเภอ | `../web/assets/js/orchard_soil_exploration.js` | ส่วนในหน้ารวม อ่านทะเบียนหลักฐานและคำบรรยายดิน ไม่สร้าง target รายชุดดิน; CSV ทดลองถูกสร้างนอก training |
| หน้ารอบก่อน | `../web/templates/`, `build_five_province_history.py`, `build_priority_province_map.py` | รายงานเฉพาะหัวข้อ ไม่ใช่ entry point ล่าสุด |
| Notebook | `notebooks/build_*_notebook.py` | สร้าง Notebook รันจาก root ด้วย `python -m tools.notebooks.<ชื่อโมดูล>` |
| เตรียมข้อมูล | `prepare_monthly_training.py`, `prepare_five_province_history.py`, `prepare_national_comparison.py`, `prepare_regional_orchards.py` | สร้างข้อมูลวิเคราะห์ ไม่ต้องรันเพื่อดูแผนที่ |
| ภัยพิบัติ ปภ. 5 จังหวัด | `prepare_ddpm_disasters.py` | กรองสถิติหมู่บ้านและข่าวรายจังหวัด ตรวจวันเกิดเหตุจากทะเบียนที่ทบทวนแล้ว และคำนวณช่วงที่อาจทับระยะผล ไม่รวมเข้า training อัตโนมัติ |
| NDVI ดาวเทียม | `fetch_modis_ndvi.py` | ดาวน์โหลด MOD13Q1 ฟรีจาก NASA ORNL เก็บ raw ใน cache และ CSV หลังกรอง QA; จุดอ้างอิงไม่ใช่สวนหรือค่าเฉลี่ยจังหวัด |
| โมเดลภูมิภาค | `train_monthly_production.py`, `analyze_annual_yield_windows.py`, `compare_annual_yield_features.py`, `compare_harvest_stage_yield.py` | ทดลองโมเดลและ rolling หลายปี เขียนผลใน training ไม่ใช่ข้อสรุปสาเหตุ |
| แพคไฟล์ | `package_training_bundle.py` | สร้าง ZIP ถ้าไม่มี รักษา ZIP เดิม ไม่แก้ CSV |
| ข้อมูลสวน | `export_training_data.py`, `clean_stale_weather.py`, `analyze_live_soil_drydown.py` | export, flag ค้าง, ตรวจดิน อ่านพารามิเตอร์/output ก่อนรัน |
| ดึง/ตรวจแหล่ง | `fetch_orchard_weather.py`, `fetch_regional_ldd.py`, `inspect_regional_ldd.py`, `audit_regional_readiness.py` | อาจดาวน์โหลด ไม่จำเป็นทุกครั้งที่เปิดงาน |
| Secrets | `maintenance/` | งานแยกด้าน config ส่วนตัว อ่านก่อนรัน ไม่ใช่ขั้นตอนเปิดแผนที่ |

Tests ปัจจุบันอยู่ใน `tests/`; `tools/test_*.py` เป็นการตรวจหัวข้อเฉพาะรอบก่อน ยังไม่ได้ย้าย import/API โค้ด ติดตั้งด้วย `requirements-national-analysis.txt` ตาม [README](../README.md#start-here)

เพิ่ม NDVI ในการทดลองเดิมด้วย `python tools/compare_harvest_stage_yield.py --ndvi` หลังดาวน์โหลดสำเร็จ เขียนผลแยกชื่อ `harvest_stage_rolling_ndvi_*` ไม่เขียนทับผลคู่ไม่มี NDVI ดูวิธีและข้อจำกัดใน [คู่มือ training](../research_data/five_province_history/training/README_TH.md)

เพิ่ม VPD proxy จาก Tmin/Tmax/RH รายวันด้วย `python tools/compare_harvest_stage_yield.py --vpd` เขียนผล `harvest_stage_rolling_vpd_*` ถ้าต้องการทดลองเฉพาะข้อมูลปีใหม่เพิ่ม `--train-start-year 2010` จะได้ผลแยก `harvest_stage_rolling_vpd_recent2010_*` ไม่กรองแถวด้วยค่าผลผลิตต่ำ และต้องเทียบช่วงทดสอบเดียวกัน ดูสูตร/คะแนนทุกคู่ในคู่มือ training

รวม NDVI + VPD และจูน CatBoost/Extra Trees/SVR ด้วย `python tools/compare_harvest_stage_yield.py --ndvi --vpd --advanced --train-start-year 2010` ต้องติดตั้ง dependencies ใน `requirements-national-analysis.txt` (เพิ่ม CatBoost) ผลเป็น `harvest_stage_rolling_combined_advanced_recent2010_*` จูนจากอดีตในแต่ละ fold เท่านั้น ไม่ใส่ข้อมูลดิน/ภัยที่ยังจับคู่ไม่ได้

## ปรับหน้าตาด้วย Tailwind

แก้ `web/assets/css/orchard_tailwind.css` (Tailwind `@apply` สำหรับหน้าเดิม) แล้วรันจาก root บน PowerShell:

```powershell
./tools/build_orchard_tailwind.ps1
python tools/build_unified_orchard_map.py
```

สคริปต์แรกดาวน์โหลด CLI ทางการรุ่น 4.3.3 เฉพาะครั้งแรกลง `.build/tailwind/` และตรวจ SHA256 ก่อนรัน ไม่ต้องติดตั้ง npm บนเครื่องนี้ ได้ `web/assets/css/orchard_tailwind.generated.css` ซึ่งต้องเก็บใน Git จากนั้น builder ฝัง CSS ใน HTML คนเปิดรายงานไม่ต้องรัน Tailwind หรือโหลด Tailwind CDN ปิด Preflight เพื่อไม่ reset แผนที่ Leaflet; ระบบพิกัด/อากาศยังอยู่ใน HTML/JS เดิม

## ปรับ Lumen

แก้ `web/assets/js/orchard_lumen.js` แล้ว build จาก root ด้วย `node tools/build_orchard_lumen.mjs` ถ้ายังไม่มีชุด build ให้ติดตั้งใน `.build/lumen` ด้วย `pnpm --dir .build/lumen add --save-exact @santi020k/lumen-elements@4.0.0 esbuild@0.25.12` ไฟล์ bundle ที่ใช้จริงอยู่ใน `research_data/five_province_history/` ตามเดิม
