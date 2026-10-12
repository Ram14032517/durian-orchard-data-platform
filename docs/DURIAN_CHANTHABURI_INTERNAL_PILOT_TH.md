# Phase 9C — Chanthaburi Internal Research Dataset Pilot

วันที่: 12 ตุลาคม 2026

สถานะ: **Internal pilot สร้างสำเร็จ / QC ผ่านพร้อมข้อจำกัด / Public release HOLD**

## Deliverables

รุ่นใหม่: `C:/project/research_data/internal_research/chanthaburi_pilot/phase9c_20261012_v1/`

| ไฟล์ | สิ่งที่ส่งมอบ |
|---|---|
| schema.json / dataset.json | Schema, keys, foreign-key description และข้อมูลแบบ typed JSON; missing เป็น null |
| province_year.csv | 20 แถว: Yield OAE จังหวัดเชื่อมกับ weather spatial profile; ไม่ใช่ yield สวน |
| weather_profile_year.csv / weather_profile_month.csv | 20 province-years / 240 province-months |
| coverage.csv | Coverage และสถานะ OAE ทีละปี 2006–2025 |
| soil_map_vintage.csv / soil_composition.csv | คู่รุ่นแผนที่ 1 รุ่น / หน่วยแผนที่ดิน 76 แถว ไม่ขยายดินเป็นข้อมูลสำรวจรายปี |
| mixed_use_exclusions.csv | 30 รหัสผสม แยกพื้นที่ทั้งหมด ไม่เดาสัดส่วนทุเรียน |
| sampling_points.csv / response_signatures.csv | จุดเดิม 16 จุด และ profile hashes; เฉพาะใช้ภายใน |
| data_dictionary.csv | Field, type, unit, source, calculation, missing values และ flags |
| source_manifest.json / field_lineage.jsonl | Inputs 61 ไฟล์พร้อม SHA256 และ lineage ของทุกแถว รวม OAE sheet/row/item |
| quality_flags.csv | 999 flag records; เป็น metadata ข้อจำกัด ไม่ใช่ observations ใหม่ |
| PREVIEW_TH.md / QC_REPORT_TH.md / qc_report.json | Preview สำหรับตรวจในโครงการและ QC แบบอ่านง่าย/เครื่องอ่านได้ |
| reproducibility.json / protected_verification.json / output_manifest.json | Code/input hashes, dependencies, protocol, protected hashes และ output seal |

Directory มี `.gitignore` ป้องกันการนำ assets ภายในไป commit โดยไม่ตั้งใจ ไม่มีการ push/upload/deploy ไม่เพิ่มรายงานนี้หรือ dataset ลงเว็บไซต์ Production

## Preflight และ Coverage จริง

อ่าน Phase 9B, manifests, derived artifacts และ OAE Workbook `durian` โดยตรง ตรวจทุกปี ไม่อาศัยข้อความว่าข้อมูลครบเพียงอย่างเดียว

- Weather: 2006–2025 ครบ 20 ปี; 12 เดือนต่อปี; raw cached sample-months ที่ตรวจ 16 × 20 × 12 = 3,840
- OAE: Yield, bearing area, planted area, production มีครบ 4 measures ทุกปี 2006–2025; Yearly coverage 20/20 ไม่มี Yield missing ใน pilot จริง
- OAE Yield หน่วย **กิโลกรัมต่อไร่** ตรงต้นฉบับ; ใช้ค่าที่รายงาน ไม่แทนด้วยผลผลิตรวมหารพื้นที่หรือแปลงเป็นผลผลิตรายสวน
- `data_date` = 2026-07-14 เป็น source metadata ไม่ใช่หลักฐาน publication date ของข้อมูลที่รู้ในปีอดีต
- OAE ค่าทั้ง 20 ปีและอากาศตรงกับ derived panel เดิม ไม่มี coverage/unit/lineage conflict ที่ทำให้ต้องหยุด
- Raw GIS hashes 7 entries + raw archives 2 ไฟล์ตรงหลักฐานเดิม; cached POWER 16 responses ตรง sidecar hashes
- ใช้ soil overlay, polygon audits, sampling และ weather outputs เดิม ไม่ rerun overlay หรือสร้าง polygon ใหม่

Full coverage table และ yearly values อยู่ `coverage.csv` กับ `PREVIEW_TH.md` รวมทุกปี ไม่ตัดปีที่ดูยากออก โปรแกรมและ tests รองรับ missing Yield เป็น null โดยคง weather years ครบ หาก source กับ derived artifact ขัดกันจะ fail ก่อน export

## QC Results

| Check | ผล |
|---|---|
| Source hashes / duplicate keys / schema grains | ผ่าน |
| Sampling weights | รวม 1 ภายใน tolerance 1e-7; ตรวจสัมพันธ์กับ stratum area/union area |
| Cached response → sample-month values | ตรง derived artifact ทุก parameter/key; ตรวจหน่วยและ request coordinates |
| Sample-month → province-month | ผ่าน weighted aggregation และ coverage; ไม่เติมหรือ renormalize เมื่อ stratum ขาด |
| Province-month → annual | ผ่าน day-weighted means; rain mm/day × days รวมรายปี; ไม่ใช้ month13 |
| Weather response signatures | 16 จุดให้ 11 profile hashes ไม่ซ้ำ; ไม่อ้าง 16 independent stations |
| Soil area / covered / uncovered / overlap | ผ่าน tolerance 0.1 ไร่ตาม Phase 9B |
| SC/W/uncovered denominator และ mixed exclusions | ผ่าน; ไม่มีการลบ SC/W หรือ renormalize shares |

พื้นที่ pure A403 539,971.790558 ไร่; covered 539,963.639789 ไร่; uncovered 8.150769 ไร่ (0.00150948%)

SC 32,588.748646 ไร่ และ W 290.555444 ไร่อยู่ใน covered แล้ว ไม่บวกซ้ำ Mixed-use 139,426.573408 ไร่ (5,364 polygons) ไม่เข้าตัวหาร pure A403 จำนวน pure polygons 8,512 ตรง scope

Soil composition sum + uncovered share ≈ 100% ภายใน tolerance ที่แปลงจากพื้นที่ ไม่ปรับค่ารายแถวเพื่อบังคับให้ได้ 100% แบบไร้ uncovered

## Automated Tests และ Protection

เพิ่ม `C:/project/tests/test_chanthaburi_internal_pilot.py` และตัวสร้างแยก `C:/project/tools/build_chanthaburi_internal_pilot.py` ไม่มีการแก้ caller หรือ code เดิม

Tests ใหม่ **15/15 ผ่านทั้งก่อนและหลัง export**:

- Real yearly coverage, sampling, SC/W/uncovered และ signatures
- Missing Yield/null โดยไม่ลด weather years, OAE duplicate/unit conflicts
- Missing stratum ไม่ renormalize, incomplete months และ rainfall/solar units
- Duplicate keys/nonfinite values, source-resolvable row lineage
- Missing publication evidence ไม่เดา, cache tamper/missing archive fail-closed
- Input mutation หยุดก่อนเขียน, output boundary/overwrite protection
- Schema/JSON/CSV roundtrip, dictionary และ output hash seal

Tests preflight และ test export ปิด socket เพื่อป้องกัน network; ไม่มี fetch/download ใน exporter ตัวนี้ ไม่ได้รัน repository-wide suite หรือ containment tests ที่เปิด geometry หลายจังหวัดใหม่ เพราะไม่มีการแก้ executable files เดิมและงานจำกัด pilot จังหวัดเดียว

ตรวจ input hashes ทั้ง 61 อีกครั้งหลัง export; ตรวจ hashes ของ outputs ใน seal 21 ไฟล์ (ไม่รวม output_manifest ที่ seal ตัวเองไม่ได้) และ manifest payload hash ผ่าน

Protected inventory **960 ไฟล์ Before = After = Final** รวม raw/derived GIS, weather, OAE และ Production/Protected paths ที่มีจริงใน registry เดิม เก็บเฉพาะ hashes ไม่สำรอง Secrets

Production model SHA256 คงเดิม:

`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

Git status เทียบก่อนงาน: เพิ่มเฉพาะ exporter, tests และรายงานนี้; การเปลี่ยนแปลงเดิมของผู้ใช้ไม่ถูกแก้/ลบ Pilot outputs อยู่ใน versioned internal directory ที่ ignore ไว้

## License และข้อจำกัดที่ยังเหลือ

ใช้หลักฐานสิทธิ์ที่เก็บใน Phase 9B และ SOURCE.md ในเครื่อง ไม่ refresh หรือดาวน์โหลด metadata ใหม่ ผู้ใช้อนุมัติ scope local internal noncommercial research; **ไม่ใช่การรับรองทางกฎหมายว่าทุก derived use/share ได้รับอนุญาตแล้ว**

LDD Catalog ระบุ NC-ND; resource/file-specific redistribution grant และ license version ยัง pending OAE ระบุ Other/Attribution Non-Commercial โดย version ยังไม่ยืนยัน POWER open-access/citation guidance ไม่ล้างข้อจำกัดของ footprint LDD ดังนั้น dataset/points/geometry ห้ามเผยแพร่หรือส่งออกนอกขอบเขตโครงการโดยอัตโนมัติ Preview สำหรับตรวจภายใน ไม่ใช่ public-release approval

- Footprint ปี 2568 (2025) ใช้กับ weather ทุกปี; 19/20 ปี weather ก่อนปี map label ไม่ใช่ geometry สวนจริงที่ยืนยันย้อนหลัง
- Soil ปีผลิต 2561 ไม่ใช่วันสำรวจ; survey date = null/unverified
- OAE revised-reference และ publication vintages ไม่พิสูจน์; **Historical PIT ไม่รับรอง**
- Monthly POWER ตาม cached header เป็น LST; documentation discrepancy ยังเป็น review flag ไม่ปรับเวลาเอง
- Reuse overlay QC เดิม ไม่ independent recheck geometry containment; aggregate soil lineage ถึง derived soil row + raw map pair/code เท่านั้น ไม่มี individual soil–crop intersection fragments เก็บไว้เพื่อพิสูจน์ใหม่โดยไม่ rerun
- ไม่มี Yield รายสวน ไม่มี causal inference ไม่มีการฝึก ML หรือเพิ่ม Features ให้ Production

หยุดรออนุมัติหลัง pilot นี้ ไม่ขยายอีกสามจังหวัด ไม่เผยแพร่ ไม่ดำเนินงาน ML ต่อ
