# Phase 11B — Chanthaburi District Yield Source Verification & Extraction

12 ตุลาคม 2026 · Internal Versioned Dataset · **Accepted Transcription Only / Public HOLD**

## 1. ผลตรวจ Source และ Acceptance

ดาวน์โหลดเฉพาะ [PDF ที่อนุมัติจากกรมส่งเสริมการเกษตร](https://edoae.doae.go.th/wp-content/uploads/2025/10/3.-%E0%B8%99%E0%B8%B2%E0%B8%A2%E0%B8%A8%E0%B8%A4%E0%B8%87%E0%B8%84%E0%B8%B2%E0%B8%A3-%E0%B8%A3%E0%B8%B1%E0%B8%81%E0%B8%A3%E0%B9%88%E0%B8%A7%E0%B8%A1.pdf) URL เดิม, Domain `edoae.doae.go.th`, HTTP 200, Content-Type `application/pdf`, Redirect 0 ครั้ง; ขนาด 1,088,812 bytes, PDF 16 หน้า Parse แบบ strict ได้ ไม่เข้ารหัส ตรวจ PDF signature/EOF และ SHA256:

`84d4cc284f65f77ccf5c4a42ae7df6ab21f730cee6913b9fdc13ce8af21394ab`

ตรวจภาพต้นฉบับหน้า 1, 3 และ 5 พร้อมข้อความ ไม่ใช้ OCR เป็นหลักฐานเพียงอย่างเดียว **ตารางที่ 2 อยู่ PDF physical page 5 (1-based)** ไม่มีเลขหน้าพิมพ์ที่ยืนยัน จึงเก็บ printed_page_number=null หัวเรื่องในเนื้อหา: ทุเรียน เนื้อที่ยืนต้น เนื้อที่ให้ผล ผลผลิต ผลผลิตต่อไร่ รายอำเภอ ปี 2566–2567 ภาพตารางมีหัวรวม “ภาคตะวันออก” แต่แถวจังหวัดคือจันทบุรีและสิบอำเภอจันทบุรี เก็บสองข้อความตามต้นฉบับ ไม่ขยาย Coverage ไปจังหวัดอื่น

เอกสารวิจัยชื่อ “แนวทางการประยุกต์ใช้ข้อมูลทะเบียนเกษตรกรในการประเมินสถานการณ์ไม้ผลของเจ้าหน้าที่สำนักงานเกษตรอำเภอในพื้นที่จังหวัดจันทบุรี” ผู้เขียน นายศฤงคาร รักร่วม สำนักงานเกษตรจังหวัดจันทบุรี Source Attribution ใต้ตาราง: **สำนักงานเศรษฐกิจการเกษตรที่ 6, 2567** เป็น Secondary Research Document บน DOAE Domain ไม่ใช่การเข้าถึง Original OAE6 Statistical Vintage โดยตรง

## 2. Dataset และ QC

**10 อำเภอ × 2 ปี = 20 แถว**, Numeric Measurements 80 ค่า ไม่มี Missing/อ่านไม่ชัดในตารางที่ตรวจ ไม่มี Duplicate District-Year/ค่าติดลบ Every Measurement มี PDF Hash, Page, Table, District Row Name/Ordinal, Year/Metric Column Anchor และ Printed Value ใน Field Lineage

| อำเภอท่าใหม่ (ตัวอย่าง) | ยืนต้น ไร่ | ให้ผล ไร่ | Production ตัน | Reported Yield กก./ไร่ |
|---|---:|---:|---:|---:|
| 2566 / 2023 | 105,816 | 77,130 | 171,229 | 2,220 |
| 2567 / 2024 | 109,116 | 80,690 | 130,314 | 1,615 |

ตรวจ `production_tonnes × 1000 / bearing_area_rai` ครบ 20 แถว สอดคล้องกับความละเอียดเลขจำนวนเต็มที่พิมพ์ไว้ ใช้ Rounding Intervals ของ Production ±0.5 ตัน, Bearing ±0.5 ไร่, Reported Yield ±0.5 กก./ไร่ ไม่เพิ่ม Tolerance แบบเดาและไม่แก้ตัวเลข Residual ระหว่าง Reported กับค่าหารสูงสุด **0.2749054224 กก./ไร่** เก็บค่าหารเพื่อ QC แยก ไม่เขียนทับ Yield จากต้นฉบับ ไม่รวม Yield โดยบวกหรือเฉลี่ยแบบไม่ถ่วงตัวหาร

Crosswalk ครบ **2201–2210**: เมืองจันทบุรี, ขลุง, ท่าใหม่, โป่งน้ำร้อน, มะขาม, แหลมสิงห์, สอยดาว, แก่งหางแมว, นายายอาม, เขาคิชฌกูฏ ชื่อทั้งสิบตรงหลังตัด Prefix `อ.` จาก Local Admin DBF เท่านั้น **Verified Normalized Exact 10, Ambiguous 0** หลาย DBF Records ของอำเภอเดียวไม่ทำให้เกิด Target ซ้ำ รหัสไม่ได้อยู่ใน PDF จึงบันทึก Lineage ไป DBF/Record/Hash แยกจาก Table Values การตรวจนี้ไม่ยืนยัน Historical Boundary Effective Date และไม่ได้ Join Geometry

## 3. Reconciliation กับ OAE Workbook เดิม

Reference: `C:/project/research_data/external/oae_2026-09-17/durian_province.xlsx`, sheet `durian` SHA256:
`6a3ae44026b5ef8037a8bb091852281d890168a8d795c9c44d5cde9a48613d4c`

| ปี BE | Measure | PDF Province / District Sum* | OAE | PDF−OAE | Absolute Difference | Absolute % ของ OAE |
|---|---|---:|---:|---:|---:|---:|
| 2566 | ยืนต้น ไร่ | 413,046 | 420,420 | −7,374 | 7,374 | 1.7540% |
| 2567 | ยืนต้น ไร่ | 439,552 | 447,356 | −7,804 | 7,804 | 1.7445% |
| 2566 | ให้ผล ไร่ | 273,648 | 273,648 | 0 | 0 | 0% |
| 2567 | ให้ผล ไร่ | 295,273 | 295,273 | 0 | 0 | 0% |
| 2566 | Production ตัน | 538,461 | 538,461 | 0 | 0 | 0% |
| 2567 | Production ตัน | 448,692 | 448,692 | 0 | 0 | 0% |
| 2566 | Reported Yield กก./ไร่ | 1,968 | 1,968 | 0 | 0 | 0% |
| 2567 | Reported Yield กก./ไร่ | 1,520 | 1,520 | 0 | 0 | 0% |

*ผลรวมสิบอำเภอตรงกับแถวจังหวัด PDF ทุก Additive Measure ทั้งสองปี Yield เป็นแถวจังหวัดที่พิมพ์ไว้ ไม่ใช่ผลบวก Yield อำเภอ ค่าหารจาก Province Production/Bearing = 1,967.7140 / 1,519.5836 กก./ไร่ สอดคล้องกับ Reported Integer Yield

OAE Cell Anchors เก็บทั้งแปดค่า (G536/G537, G1643/G1644, G2750/G2751, G3857/G3858) พร้อม `data_date` 2026-07-14 **ไม่ตีความว่าเป็น Publication Date** การต่างของพื้นที่ยืนต้นอาจมาจาก Edition/Revision/นิยาม/Transcription ที่ต้นทาง แต่ยังแยกสาเหตุไม่ได้ ผลรวมตรงภายใน PDF จึงไม่พบหลักฐานว่าความต่างเกิดจากการถอดรายอำเภอในรอบนี้ ไม่ Scale/แก้ PDF หรือ OAE และไม่สรุปว่า OAE ปรับย้อนหลังแล้วแน่นอน

## 4. Missingness / Vintage / Quality

| ประเด็น | สถานะและหลักฐาน |
|---|---|
| Year Labels | ยืนยันว่าพิมพ์ 2566/2567; CE = BE−543 เท่านั้น |
| Crop / Harvest / Calendar Year | **Unverified**; ตารางไม่ได้ให้นิยาม ต้องขอ Original OAE6 Definitions |
| Preliminary / Forecast / Final / Revised | **Unverified**; “ข้อมูลเอกภาพ” ไม่พิสูจน์ Final Actual |
| Publication Date | **Unverified / null**; ห้ามใช้ URL เดือน 2025/10 เป็นวันที่เผยแพร่ |
| HTTP Last-Modified | 2025-10-20 02:15:58 GMT; เป็น Server Metadata ไม่ใช่หลักฐานวันเผยแพร่ตาราง |
| PDF Creation/ModDate | 2024-10-06 17:20:18 +07:00; เป็น File Metadata ไม่พิสูจน์ว่าเผยแพร่/ไม่เคยแก้ |
| Retrieval Time | 2026-10-12T05:18:17.003909+00:00; บันทึกแยก ไม่ใช้แทน Publication Time |
| Study Period | หน้า 3: กรกฎาคม–สิงหาคม 2567 เป็นช่วงวิจัยเจ้าหน้าที่ ไม่ใช่ Vintage/Harvest Period ของตาราง; วันที่ตัดยอดทะเบียน 30 เม.ย. 2567 เป็นบริบทชุดอื่น |
| Historical Availability | ไม่ยืนยันว่ารุ่นนี้มีจริง ณ Issue Date ใด; ไม่รับรอง PIT |
| Missing Numeric Values | 0/80; Parser/Tests รองรับ null โดยไม่เติมศูนย์ |
| Cultivar / Orchard / Management | ตารางไม่ให้ข้อมูลเพียงพอสำหรับควบคุมปัจจัยเหล่านี้ |
| License / Public Release | ยังไม่ยืนยันสิทธิ์นำ Derived Dataset เผยแพร่; **HOLD** |

Acceptance = **การถอดค่าตามต้นฉบับเท่านั้น** ไม่รับรอง Final Actual, Vintage, Spatial Join หรือ Forecast Readiness ทุก Row ตั้ง `training_eligible=false` เพื่อไม่เข้าสู่ Pipeline อัตโนมัติ

## 5. Artifacts และ Tests

Final Dataset: `C:/project/research_data/internal_research/chanthaburi_district_yield/phase11b_20261012_v2/`

- `district_year.json` + `dataset_preview.html`/`.png`: 20 แถวพร้อม Metadata/Quality Flags
- `province_rows.json`, `reconciliation.json`, `oae_reference_anchors.json`: Province Rows และ QC Differences/Cell Anchors
- `source.pdf`, `download_verification.json`, `source_manifest.json`, `input_manifest.json`: Source/Evidence/Versions/Hashes
- `source_page-05.png`, `context_page-01.png`, `context_page-03.png`: ภาพที่ใช้ตรวจ
- `data_dictionary.json`, `field_lineage.json`, `district_crosswalk.json`, `quality_report.json`: Units/Missingness/Lineage/QC
- `protected_verification.json`, `output_manifest.json`: Protected Check และ Immutable Seal

v1 เป็น Working Extraction เก็บไว้ไม่เขียนทับ Final v2 ใช้ PDF Bytes เดิม ไม่มีดาวน์โหลดซ้ำหรือแหล่งอื่น และแก้คำกำกับ OAE เป็น `local_reference_vintage_history_unverified` เพื่อไม่ให้ชื่อสถานะสื่อว่าพิสูจน์ Revision History แล้ว

เพิ่มเฉพาะ `C:/project/tools/extract_chanthaburi_district_yield.py`, `C:/project/tests/test_chanthaburi_district_yield_extraction.py`, รายงานนี้ และ Internal Artifacts ใหม่ สคริปต์เป็น Offline Manual-transcription Exporter ที่ผูกกับ Source PDF Hash ไม่อ้างเป็น Generic OCR Extractor

Focused Tests **9/9 ผ่าน**: Known Source Cells/Anchors, Units, Negative Values, Missing Preservation, Missing Coverage, Duplicate, Yield Rounding/Zero Bearing, Crosswalk Ambiguity, Reconciliation/No Scaling และ Vintage/Field Lineage

Protected Baseline **1,241 ไฟล์คงเดิมทั้งหมด**, Production SHA256:
`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

ตรวจ Seals Phase 10F/10G เดิมคงเดิม ไม่แก้ Dataset/GIS/Review/Production/API/Frontend ไม่มี GIS Overlay, Soil/Weather Join, Training, Scenario, External Upload หรือค้นแหล่งเพิ่มเติม ไม่รัน Repository Suite ซ้ำในรอบ Source Extraction ที่เพิ่มเฉพาะสคริปต์ใหม่

## 6. เพียงพอต่อ Soil–Climate–Yield หรือไม่

**เป็นจุดเริ่มต้นที่ใช้ตรวจความพร้อม/ออกแบบงานได้ แต่ยังไม่พอสำหรับข้อสรุป Soil–Climate–Yield ที่เสถียร** 20 District-years มีเพียง 10 พื้นที่และ 2 ปี ไม่ใช่ 20 Observations อิสระ; Soil Snapshot คงที่และ Weather Exposure รายอำเภอยังไม่พร้อม จังหวัดนี้มี Soil Pilot ที่ผ่านเฉพาะท่าใหม่ และข้อมูลพันธุ์/การจัดการยังขาด

เสนอหาเพิ่ม **อย่างน้อยอีก 3 ปีให้รวม 5 ปี** เป็นเป้าหมายรวบรวมระยะแรก; ถ้าตั้งใจศึกษา Panel/Soil×Climate ควรมุ่งหา **อีก 8 ปีให้รวม 10 ปี** พร้อมชุดนิยามและ Original Source Versions ที่เทียบกันได้ ตัวเลขเหล่านี้เป็นเป้าหมายเชิงปฏิบัติ ไม่ใช่คำรับรอง Power/Significance; ต้องประเมิน Effective Sample Size, Unique Weather Exposures, Serial/Spatial Dependence และ Missingness ภายหลัง

ก่อนขยาย GIS อีก 9 อำเภอ ควรขออนุมัติการตรวจ Original OAE6 Table Metadata/Year Basis/Finality และปีเพิ่มเติมก่อน ข้อมูลแค่สองปีอาจใช้ Descriptive Comparison หลังอนุมัติ Join และ QC ใหม่ แต่ห้ามตีความเป็น Causal Impact หรือพยากรณ์สวนรายเจ้าของ

ใช้ PDF Skill บังคับตรวจภาพต้นฉบับ, Spreadsheets Read-only สำหรับ OAE และ Ponytail จำกัดเป็น Exporter/Focused Tests แยก **หยุดรออนุมัติก่อน Join GIS หรือขยายการค้นหา; Public HOLD คงเดิม**
