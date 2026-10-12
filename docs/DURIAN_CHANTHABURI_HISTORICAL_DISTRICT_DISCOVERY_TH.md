# Phase 11C — ข้อมูลผลผลิตทุเรียนรายอำเภอจันทบุรีย้อนหลัง

วันที่ตรวจ 12 ตุลาคม 2569 · Internal Research Only · Public HOLD · Historical PIT ไม่รับรอง

## ผลที่พบจริง

**ยังหา Yield รายอำเภอเพิ่มไม่ได้: 0 ปีใหม่** มีเพียง 2566–2567 เดิมครบ 10 อำเภอ × 2 ปี = 20 แถว รับรองเฉพาะการถอดตาราง ไม่ใช่ Final Actual ทั้งสองปียังไม่ยืนยันนิยามปี วันที่เผยแพร่ และสถานะ Final/Revised ไม่มี Final Actual ที่ยืนยันแล้ว (0 ปี) เป้าหมายรวมอย่างน้อย 5 ปียังไม่ผ่าน

พบไฟล์ CSV ทางการชื่อ “เนื้อที่ยืนต้นทุเรียน” เพิ่ม: 2557–2567 (2014–2024) ครบ 10 อำเภอ × 11 ปี = 110 แถว **มีเฉพาะ Standing Area** ไม่มี Production, Bearing Area หรือ Yield จึงแยกเป็น Candidate/Unverified Records และเก็บสามตัวแปรหลังเป็น null ไม่คำนวณเติม ไม่ถือว่าได้ผลผลิตเพิ่ม 9 ปี

| ปี พ.ศ. (ค.ศ.) | Yield/Production/Bearing ที่ถอดได้ | Standing-only Candidate | สถานะข้อมูลผลผลิต |
|---|---:|---:|---|
| 2557 (2014) | 0/10 | 10/10 | ไม่พบ; มีธงตรวจตำแหน่งแถวพื้นที่ |
| 2558 (2015) | 0/10 | 10/10 | ไม่พบ; มีธงตรวจตำแหน่งแถวพื้นที่ |
| 2559 (2016) | 0/10 | 10/10 | ไม่พบ |
| 2560 (2017) | 0/10 | 10/10 | ไม่พบ |
| 2561 (2018) | 0/10 | 10/10 | ไม่พบ |
| 2562 (2019) | 0/10 | 10/10 | ไม่พบ |
| 2563 (2020) | 0/10 | 10/10 | ไม่พบ |
| 2564 (2021) | 0/10 | 10/10 | ไม่พบ |
| 2565 (2022) | 0/10 | 10/10 | ไม่พบ |
| 2566 (2023) | 10/10 เดิม | 10/10 | ถอดตารางได้; Finality/Year Definition/Vintage Unverified |
| 2567 (2024) | 10/10 เดิม | 10/10 | ถอดตารางได้; Finality/Year Definition/Vintage Unverified |

ตาราง Coverage ระบุเฉพาะช่วงที่ CSV พบจริง ไม่อ้างว่าข้อมูลปีอื่นไม่มีในหน่วยงาน 20 แถวเป็นหน่วยอำเภอ–ปี ไม่ใช่สวน 20 แห่งหรือ 20 ตัวอย่างอิสระ

## Source Discovery และหลักฐาน

1. Phase 11B: PDF กรมส่งเสริมการเกษตร หน้า PDF จริง 5 ตาราง 2 อ้างสำนักงานเศรษฐกิจการเกษตรที่ 6 ปี 2567 ตรวจ Sealed Manifest และเปิดภาพหน้าตารางเดิมอีกครั้ง ไม่ดาวน์โหลดหรือแก้ Dataset เดิม
2. [บัญชีข้อมูลจันทบุรี — เนื้อที่ยืนต้นทุเรียน](https://chanthaburi.gdcatalog.go.th/dataset/dataset_10_07): CKAN Package ระบุระดับอำเภอและแหล่งทะเบียนเกษตรกร ดาวน์โหลด CSV สาธารณะบนโดเมนทางการหนึ่งไฟล์ UTF-8 BOM, text/csv, SHA256 `f24a9f0d62c01086eb8526316eae161a69ad625cacf8420238b35f60469dda0c` หน่วยทุกแถวเป็นไร่ การระบุเจ้าของ/ทะเบียนใน Catalog ไม่พิสูจน์ว่านิยามประชากรตรงกับ OAE
3. Catalog ผลผลิตรวม `dataset_10_06` และผลผลิตเฉลี่ย `dataset_10_05` ระบุระดับจังหวัด จึงไม่ดาวน์โหลดมาทำ District Targets CKAN Query ได้ 21 Packages แต่ไม่ใช่ 21 ชุดผลผลิตรายอำเภอ
4. เปิดหน้า OAE6, สำนักงานเกษตรจังหวัด และเมนูสถิติ DOAE ภาคตะวันออก พร้อมค้นเอกสารสถานการณ์/สถิติแบบจำกัด ไม่พบตารางรายอำเภอเพิ่มที่ตรวจรับได้ ลิงก์สถิติเก่าของเกษตรจังหวัดดึงไม่สำเร็จ ไม่สรุปว่าเป็น HTTP 404 หรือข้อมูลไม่มี
5. ลิงก์ `data%2066-1.pdf` เปิดไปเป็น HTML ปัจจุบัน ไม่ใช่ PDF เก่าตามข้อความในดัชนีค้นหา เมนู DOAE อีกลิงก์มีปี URL ต่างจากหัวเอกสารและเป็นระดับจังหวัด จึงไม่สกัดเป็นผลผลิตรายอำเภอ
6. PDF ที่ค้นพบจาก OPSMOAC และเอกสาร Dashboard OAE เป็น Candidate ที่ยังไม่ยืนยัน Coverage จันทบุรีรายอำเภอ บางการดึง Timeout; ไม่ใช้ Search Snippet เป็นหลักฐานรับรองตัวเลข ไม่ดาวน์โหลดเอกสารอื่นจำนวนมาก ไม่ตาม PowerBI ภายนอก ไม่เข้าระบบสมาชิกและไม่ติดต่อเจ้าหน้าที่

รายละเอียด URL, ระดับหลักฐาน, เหตุผลคัดออก และ Metadata อยู่ใน `source_discovery_inventory.json`/`official_web_checks.json`; หน้าค้นเว็บที่ไม่ได้เก็บไฟล์ต้นฉบับมี SHA256 เป็น unavailable โดยนัย ไม่แสร้งว่ามี Archived Content ที่ตรวจซ้ำได้ ส่วน JSON Metadata ที่บันทึกไว้มี Hash ใน Manifest

## QC, ความขัดแย้ง และ OAE Reconciliation

- Crosswalk 2201–2210 ใช้ชื่อที่ตรวจ Exact/Normalized ใน Phase 11B และ Local Admin DBF เดิม ไม่ทำ Geometry Join; วันที่มีผลของขอบเขตยังไม่ยืนยัน
- ไม่มี District–Year–Source Version ซ้ำ และไม่รวม Source Versions เข้าด้วยกันเงียบ ๆ ไม่มีค่าติดลบ/ไม่จำกัด Units/ปีแปลง พ.ศ.→ค.ศ. ตรวจครบ Null แยกจากศูนย์
- Production/Bearing/Yield เดิม 20 แถวผ่านช่วงความคลาดเคลื่อนจากการปัดเศษจำนวนเต็มเดิม Ratio เป็น Derived QC เท่านั้น ไม่แทน Yield ต้นทาง ห้าม Sum Yield อำเภอเพื่อหา Yield จังหวัด
- ผลรวม Production/Bearing และ Yield จังหวัดปี 2566–2567 ตรง OAE Workbook เดิม แต่ Standing Area ของ PDF ต่างจาก OAE ตามรายงาน 11B

| ปี | ขลุง: PDF (ไร่) | ขลุง: Catalog (ไร่) | Catalog − PDF | รวม Catalog | รวม OAE |
|---|---:|---:|---:|---:|---:|
| 2566 | 80,294 | 87,668 | +7,374 | 420,420 | 420,420 |
| 2567 | 83,316 | 91,120 | +7,804 | 447,356 | 447,356 |

อีก 18 District–Year ของ Standing ตรงกัน ส่วนต่างสองแถวอธิบายส่วนต่างยอดรวมจังหวัดเดิมได้ แต่ **ไม่พิสูจน์ว่าฉบับใดผิดหรือเป็น Revision** อาจต่าง Vintage/ประชากร/การถอดต้นฉบับ ต้องถามเจ้าของข้อมูล เก็บทั้งสองไว้ตามเดิม

ปี 2557–2558 CSV ท่าใหม่ 1,667/1,583 ไร่ เทียบแหลมสิงห์ 66,224/66,653 ไร่; ปี 2559 เป็นท่าใหม่ 68,330/แหลมสิงห์ 1,594 เป็นสัญญาณให้ตรวจตำแหน่งแถวหรือนิยาม ไม่ใช่หลักฐานว่าต้องสลับค่า ห้ามแก้/Swap รายอำเภอโดยเดา

ผลรวม Standing Candidate กับ OAE ต่างประมาณ −9.01% ถึง −20.69% ช่วง 2557–2563; ปี 2564 ตรง, 2565 ต่าง −6,479 ไร่ (−1.71%), 2566–2567 ตรง เก็บ Absolute และ Percent Differences ครบ 11 ปี พร้อม Sheet/Cell Anchors ใน `oae_reconciliation.json` ไม่มี Scaling หรือบังคับตรง ความเปลี่ยนแปลงสอดคล้องกับความเป็นไปได้ของต่างนิยาม/รุ่นข้อมูล แต่ยังไม่พิสูจน์สาเหตุ

## Vintage, Lineage และสิทธิ์

Publication/Revision Date ของค่าตารางยังเป็น null ทั้งสองแหล่ง ปีบนคอลัมน์ไม่ยืนยันว่าเป็นปีเพาะปลูก/เก็บเกี่ยว/ปฏิทิน Catalog metadata_created 2023-09-07 และ metadata_modified 2025-06-25 เป็นวันที่ Metadata ไม่ใช่วันเผยแพร่ค่าของทุกปี; OAE data_date 2026-07-14, เวลา Download, PDF CreationDate และ URL เดือน ห้ามแทน Publication Evidence

Source Version ใช้ SHA256 ของ Bytes ที่เก็บจริง ไม่อ้างเป็นเลข Edition ทางการ Numeric/Key/Status Fields ผูก Source SHA, URL และ PDF Page/Table/Row หรือ CSV Record/Column; รหัสอำเภอผูก Crosswalk เดิม การแปลงปีและ Missing/Unverified มี Method แยก Source Manifest เก็บ Hash OAE, Crosswalk, Phase11B Seal และ Code ไว้

Catalog แสดง License Label “Open Data Common” แต่ Scope/เงื่อนไขสิทธิ์ต้นฉบับและการเผยแพร่ Derived Dataset ยังไม่รับรอง คง Internal Only / Public HOLD ไม่ Upload Geometry/Data และไม่รับรอง Historical PIT

## Data Gaps และงานที่เสนอ

ควรขอข้อมูลจาก **สำนักงานเศรษฐกิจการเกษตรที่ 6 เป็นลำดับแรก** เพราะเป็นผู้ถูกอ้างในตาราง 11B แล้วตรวจร่วมกับสำนักงานเกษตรจังหวัด/กรมส่งเสริมการเกษตร ขอเพิ่มอย่างน้อย 3 ปีที่ไม่ซ้ำ 2566–2567 เพื่อให้ครบ 5 ปี; เสนอขอ 2557–2568 เท่าที่มีจริงเพื่อประเมินเป้าหมาย 10 ปี โดยยังไม่ส่งคำขอ

ขอ Production/Bearing/Yield ที่รายงานจริง นิยามปี ชนิด Final/Forecast/Revised รุ่นเดิม/วันเผยแพร่ หน่วย รหัสอำเภอ และ Scope พื้นที่/พันธุ์ โดยเฉพาะความต่างขลุงและแถว Standing 2557–2558 ร่างคำขออยู่ใน Namespace นี้

ตอนนี้ทำได้เพียง Descriptive Comparison ของผลผลิต 2 ปีเดิมและ Source Consistency ไม่ควรเริ่ม Soil–Climate–Yield Inference: สองปีไม่เพียงพอแยกความต่างดินกับการจัดการ/อากาศ; ดินมีเพียงท่าใหม่ที่ผ่าน Internal QC และ Weather District ยังไม่พร้อม A403 ปี 2568 ไม่ใช่สวนรายเจ้าของหรือ Historical Footprint ทุกปี จึงยังไม่ทำ Join หรือ Overlay เพิ่ม

หากได้หลายปีจริง งานถัดไปเสนอ Coverage/นิยามปีที่เทียบกันได้ก่อน แล้ว Pre-register Descriptive Trends/Panel Feasibility พร้อมข้อจำกัด Spatial/Temporal Dependence; จำนวน 5 หรือ 10 ปีไม่เป็นหลักประกัน Statistical Power ห้ามใช้ผลเดิมเลือก Model หรืออ้าง Causal Impact

## ส่งมอบและ Protection

Namespace ใหม่: `C:/project/research_data/internal_research/chanthaburi_district_yield/phase11c_20261012_v1/`

- `verified_district_year.json`: 20 แถวที่สืบทอด 11B ไม่ใช่ Discovery ใหม่/Final Actual
- `candidate_unverified_records.json`: 110 Standing-only Records, Targets null
- `coverage_matrix.json`, `oae_reconciliation.json`, `cross_source_comparison.json`
- `source_discovery_inventory.json`, `source_manifest.json`, `field_lineage.json`, `data_dictionary.json`, `qc_report.json`
- `DATA_REQUEST_DRAFT_TH.md`, `protected_verification.json`, `output_manifest.json`

Focused Python Tests ใหม่ 11 ข้อ + Phase11B เดิม 9 ข้อ = **20/20 ผ่าน** ตรวจ Protected Assets ก่อน/หลัง **1,267 ไฟล์ไม่มี Hash เปลี่ยน** Production SHA256 `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680` ตรงเดิม ไม่แก้ Phase9–11B, Raw GIS, API/Frontend ไม่ฝึก ML ไม่ทำ Scenario หรือ Join

ใช้ PDF Skill ตรวจภาพต้นฉบับเดิม, Spreadsheets Skill อ่าน CSV/Workbook โดยไม่เขียนทับ และ Ponytail แยก Offline Audit ขนาดเล็กพร้อม Focused Tests ไม่แตะ Pipeline เดิม ไม่รัน Repository-wide Suites/GIS อีกครั้งเพราะงานนี้เพิ่มเพียง Audit แยก; Coverage ของแหล่งที่ดึงไม่สำเร็จยังเป็น Evidence Gap ไม่อ้างค้นครบทุกระบบ

**หยุดรออนุมัติ** ก่อนติดต่อหน่วยงาน/ขยายค้น/เชื่อม GIS หรือวิเคราะห์ Soil–Climate–Yield
