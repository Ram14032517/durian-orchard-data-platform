# Phase 9D — Four-Province Internal Geospatial Research Dataset

วันที่: 12 ตุลาคม 2026 · Internal Research Only · Public Release: **HOLD**

## ผลและที่เก็บ

สร้างรุ่นใหม่ `C:/project/research_data/internal_research/four_provinces/phase9d_20261012_v1/` จาก Assets ในเครื่องเท่านั้น ทั้ง 4 จังหวัดผ่าน QC Contract เดิมแบบ `pass_with_limitations` ไม่มีจังหวัดหรือปีถูกตัดออก ไม่มีจังหวัด Failed ในรุ่นนี้ ไม่รวมสุราษฎร์ธานี และไม่เผยแพร่/Upload ข้อมูลหรือ Geometry

จันทบุรีตรวจตรงกับ Phase 9C ทุกค่าของ 9 ตารางหลักก่อนเพิ่ม release_id ใหม่ ไม่แก้ Pilot, Exporter Phase 9C หรือ Artifacts เดิม ทั้ง Schema และหน่วยเดิมถูกตรวจเทียบก่อนเขียนไฟล์

## Coverage จริง

| จังหวัด | OAE/Weather CE | Yield พบ / ปีตรวจ | เดือน Weather | จุด / Profiles ไม่ซ้ำ | Pure A403 Polygons | รุ่น Land-use BE (CE) |
|---|---|---:|---:|---:|---:|---|
| จันทบุรี | 2006–2025 | 20/20 | 240/240 | 16 / 11 | 8,512 | 2568 (2025) |
| ชุมพร | 2006–2025 | 20/20 | 240/240 | 17 / 12 | 3,897 | 2564 (2021) |
| ศรีสะเกษ | 2006–2025 | 20/20 | 240/240 | 17 / 7 | 1,234 | 2565 (2022) |
| อุตรดิตถ์ | 2006–2025 | 20/20 | 240/240 | 9 / 7 | 71 | 2563 (2020) |

ทุกจังหวัดตรวจ OAE 4 measures ต่อปี ได้แก่ Yield, Bearing Area, Planted Area และ Production จาก workbook `durian` จริง โดยตรวจ unit/crop_year/commodity/duplicate/value และเก็บ Excel row anchors ไม่มีการสมมติ Coverage หรือเติม Yield ที่หาย กฎสำหรับ Missing ยังคง JSON null / CSV ช่องว่าง พร้อม Flag

มี province_year 80 แถว, weather_profile_year 80, weather_profile_month 960, soil_map_vintage 4, soil_composition 170, mixed_use_exclusions 78, coverage 80, sampling_points 59, response_signatures 59 และ quality_flags 3,610 แถว Lineage 21,994 records และ Source Registry 187 files

## Soil/Area QC แยกจังหวัด

| จังหวัด | Pure A403 ไร่ | SC ไร่ | W ไร่ | Uncovered ไร่ | Mixed excluded ไร่ | QC |
|---|---:|---:|---:|---:|---:|---|
| จันทบุรี | 539,971.790558 | 32,588.748646 | 290.555444 | 8.150769 | 139,426.573408 | Pass with limitations |
| ชุมพร | 86,755.515670 | 26,655.529952 | 22.954137 | 7.594429 | 53,198.222363 | Pass with limitations |
| ศรีสะเกษ | 16,529.896958 | 0 | 0.463093 | 4.881873e-12 | 4,885.699560 | Pass with limitations |
| อุตรดิตถ์ | 2,377.027338 | 2,068.735568 | 0 | −1.304024e-11 | 56,459.771677 | Pass with limitations |

Uncovered ใกล้ศูนย์ของสองจังหวัดหลังเป็น numerical residual จาก Artifacts เดิม เก็บค่าเดิม ไม่ Clamp และไม่ปรับ Threshold อุตรดิตถ์ผ่านเงื่อนไข Phase 9C เดิม `uncovered >= −1e-7` ไม่ได้แปลว่าพื้นที่จริงติดลบ

ตัวหาร Share คือพื้นที่ Pure A403 ทั้งหมด รวม SC, W และ Uncovered แต่ไม่รวม Mixed-use; SC/W เป็น subtotal ที่รวมใน Covered อยู่แล้ว ไม่บวกซ้ำ Mixed-use ไม่ถูกจัดสรรเป็นสัดส่วนทุเรียน ตรวจ Soil sums, covered + uncovered, overlap, polygon counts, inventory และ mixed-area reconciliation รายจังหวัดด้วย tolerance 0.1 ไร่เดิม

## Weather/Sampling/Join QC

- ตรวจ Hash ของ Raw GIS ตาม input_manifest, Archive ตาม source sidecars, POWER cache ตาม response SHA256 และ OAE ตาม Hash ที่ล็อกไว้ ไม่ใช้ Network Fallback
- จุดทุกจุดอ้าง inside_A403 จาก Assets/QC เดิม ตรวจจำนวน, น้ำหนักบวก, ผลรวมน้ำหนัก 1 ภายใน 1e-7 และ stratum area / union area ไม่คำนวณ Polygon Overlay/Containment ใหม่
- ตรวจ Cached POWER request coordinates, period, unit และ LST header; เปรียบเทียบ response signature และค่ารายจุดครบ 14,160 sample-months กับ Derived CSV
- Monthly aggregation ใช้น้ำหนักพื้นที่เดิม ไม่ renormalize เมื่อ strata ขาด; Annual mean ถ่วงจำนวนวัน, Rain mm/day × days แล้วรวมปี ตรวจ 12 เดือนทุกปี รวม Leap Year; tolerance Weather 1e-6 ตามเดิม
- ตรวจ Primary Keys, Province–Year cohort, Weather profile + year, Soil map pair, sampling signatures, Source IDs และ Lineage ทุก row; ไม่ Join OAE จังหวัดหนึ่งกับ Soil จังหวัดอื่น
- Schema/Dictionary/Units/Quality Flags ใช้ Phase 9C เดิม Dictionary เปลี่ยนคำอธิบายรุ่นแผนที่จากจันทบุรีแบบ Hardcoded เป็น source-specific ไม่เปลี่ยนตัวแปรหรือสูตร

## Artifacts และวิธีทำซ้ำ

ในโฟลเดอร์รุ่นใหม่มี `dataset.json`, `schema.json`, `data_dictionary.csv`, ตารางทั้ง 10 ตาราง, `coverage_matrix.csv`, `qc_summary.csv`, `source_manifest.json`, `field_lineage.jsonl`, `qc_report.json`, `QC_REPORT_TH.md`, `PREVIEW_TH.md`, `reproducibility.json`, `protected_verification.json` และ `output_manifest.json`

Reproducibility เก็บ Hash ทุก Input รวม Pilot Seal, Hash Exporter ใหม่และ Phase 9C, Dependencies, Protocol, QC thresholds และ OAE row anchors Seal payload SHA256:

`2d4c5f0a641e58778c4f059d9d6f6333cdc7e4960a72ff59bb6f6b535fdbad6f`

ตรวจแบบไม่ Export:

```powershell
& 'C:/Users/support/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B -m tools.build_four_province_internal_dataset --preflight
```

การ Export ต้องระบุชื่อรุ่นใหม่ภายใต้ `four_provinces` เท่านั้น Path ที่มีอยู่ถูกปฏิเสธ Fail-closed เมื่อ Province, Unit, Join, Hash หรือ Lineage ไม่ผ่าน พร้อมรายชื่อจังหวัด `failed_not_accepted` ไม่สร้าง Accepted Release ที่ลด Cohort เงียบ ๆ `.gitignore` ภายในรุ่นป้องกันการเพิ่ม Dataset ลง Git โดยปกติ ไม่ใช่การรับรองสิทธิ์เผยแพร่

## Tests และ Protected Assets

ก่อน Export: Python Repository Suite 310/310 ผ่าน; JavaScript 30/30 ผ่าน; Expansion Tests ก่อน Export 18/18 ผ่าน

หลัง Export: Python Repository Suite **331/331 ผ่าน** (379.550 วินาที ไม่มี Fail/Skip) รวม Expansion Tests ใหม่ 21 ข้อ; JavaScript **30/30 ผ่าน** ตรวจ CSV/JSON/Schema/Seal, Referential Integrity, Missingness, Chanthaburi Flag equivalence และ Public HOLD ไม่พบ Regression

คำสั่ง Repository Tests:

```powershell
& '.build/national-analysis-venv/Scripts/python.exe' -X utf8 -B -m unittest discover -s tests -p 'test_*.py'
& 'C:/Users/support/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' --test tests/*.js
```

ตรวจก่อน/หลัง Export และหลัง Repository Tests: Protected inventory 1,123 files ไม่มีการเปลี่ยน รวม 1,120 files จาก Snapshot เริ่มงานและเพิ่มการป้องกัน Exporter/Test/Report Phase 9C อีก 3 files Raw Archives, Derived Inputs และ Pilot คงเดิม Seal 23 files (ไม่รวมตัว Manifest เอง) ตรวจ Hash ผ่าน และไม่มีไฟล์แทรกในรุ่น Dataset

Production Model SHA256:

`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

Git Status ก่อนงานมีการเปลี่ยนแปลงเดิมอยู่มาก รักษาไว้ ไม่ Revert/Commit/Push ไฟล์ที่สร้างในงานนี้เท่านั้นคือ:

- `C:/project/tools/build_four_province_internal_dataset.py`
- `C:/project/tests/test_four_province_internal_dataset.py`
- `C:/project/docs/DURIAN_FOUR_PROVINCE_INTERNAL_DATASET_TH.md`
- โฟลเดอร์ Dataset รุ่นใหม่ที่แยกจาก Artifacts เดิม

ไม่มีการแก้ Production/API/Frontend หรือฝึก/จูน ML ใหม่ การเรียก Model ใน Repository Tests เป็นการทดสอบ Contracts เดิม ไม่ใช่การทดลอง ML รอบใหม่

## Research Limitations สำหรับปรึกษาอาจารย์

| จังหวัด | ข้อจำกัดเฉพาะ |
|---|---|
| จันทบุรี | Footprint ปี 2025 ใช้ย้อนหลัง 19 ปี; 16 จุดมีเพียง 11 response profiles ไม่ใช่ 16 สถานีอิสระ |
| ชุมพร | Footprint ปี 2021 ใช้กับ Weather ก่อนแผนที่ 15 ปี; SC ประมาณ 30.72% ของ Pure A403 และ Mixed excluded ประมาณ 38.01% ของพื้นที่ Pure + Mixed |
| ศรีสะเกษ | Footprint ปี 2022 ใช้ย้อนหลัง 16 ปี; 17 จุดมี 7 profiles แสดง spatial smoothing; พื้นที่ W ซ้อน A403 ต้องคงเป็น Flag ไม่ตีความเป็นดินสวนที่ยืนยัน |
| อุตรดิตถ์ | Footprint ปี 2020 ใช้ย้อนหลัง 14 ปี; Pure เพียง 71 Polygon, SC ประมาณ 87.03%; Mixed ประมาณ 95.96% ของ Pure + Mixed ซึ่งถูกแยกออกทั้งหมด จึงไม่เหมารวมว่า Pure sample แทนสวนทั้งหมด |

ทั้ง 4 จังหวัด: Soil ปีผลิต 2561 ไม่ใช่วันสำรวจ; Survey Date ยัง Unverified; ใช้ Fixed Retrospective Footprint ไม่ใช่ Historical Orchard Footprint รายปี; ไม่มี Yield รายสวนหรือ Geometry ขอบเขตสวนรายเจ้าของที่ยืนยัน; OAE ระดับจังหวัดไม่ใช่ Yield ของ A403 หรือของชุดดินใด; ขนาดพื้นที่ LDD ต่างจาก OAE ห้าม Rescale โดยสมมติว่าแทนกันได้

Publication Dates/Historical Vintages ของ OAE และ POWER ยังไม่ยืนยัน Revised reference ใช้วิจัยย้อนหลังเท่านั้น ไม่รับรอง Historical PIT หรือความสัมพันธ์เชิงสาเหตุ Cached POWER LST ยังมีข้อจำกัด Documentation Review; จุดตัวอย่างอาจแชร์ Coarse Grid

สิทธิ์ Derived Redistribution ของ LDD/OAE ยัง Pending ตามหลักฐาน Phase 9B ในเครื่อง ไม่ค้นใหม่หรือถือว่า NASA Open Access เคลียร์สิทธิ์ LDD; ใช้ภายในตามขอบเขตที่อนุมัติเท่านั้น Public Status คง HOLD และต้องอนุมัติแยกก่อนเผยแพร่ ขยายงาน หรือใช้ ML

จบงานนี้ให้หยุดรอคำสั่ง ไม่เริ่ม Training หรือขยายจังหวัดเพิ่ม
