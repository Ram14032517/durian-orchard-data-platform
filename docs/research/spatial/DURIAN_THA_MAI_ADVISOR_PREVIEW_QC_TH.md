# Phase 10G — Tha Mai Advisor Research Preview / Display QC

2026-10-12 · Internal Only · **Public HOLD** · ใช้ Phase 10F Internal Accepted Release Proposal / Policy v2

## ส่งมอบ

Final Folder: `C:/project/research_data/internal_research/tha_mai_spatial/phase10g_20261012_advisor_preview_v2/`

- `map_preview.png`: แผนที่สามแผง ขอบเขต/Pure A403, หน่วยแผนที่ดินภายใน Pure, Pure เทียบ Mixed-use ที่แยกออก
- `soil_composition_summary.html` และ `.json`: ตารางเต็ม 43 แถว รหัส/ชื่อจาก Source/พื้นที่/เปอร์เซ็นต์ พร้อมค่าทศนิยมต้นฉบับและ Lineage ใน JSON
- `advisor_brief.pdf` และ `.html`: Research Brief ภาษาไทยสองหน้า
- `display_qc.json`, `protected_verification.json`, `output_manifest.json`: Evidence/Hashes

ร่าง v1 คงไว้ ไม่เขียนทับและไม่ใช้ส่งมอบ เพราะตรวจภาพพบ Legend เบียด Footnote แก้เฉพาะ Layout ใน v2 ไม่เปลี่ยนค่าข้อมูล แผนที่แยกมีความละเอียด 3,240 × 1,980 px; ภาพใน PDF เป็น Overview ให้ใช้ PNG เต็มขนาดเมื่ออ่านหน่วยแผนที่

## Source / QC Policy / Warning

ตรวจ Seal ของ Phase 10F Evidence และ Release Proposal ผ่าน ทุก Source File Hash ตรง Manifest และ Dataset SHA256:
`48bdbce32528719effbdea646db162e382a193c28972fd53054808d37223bb2a`

Policy `directed_partition_holes_onepass_upper_bound_warning_v2`: Primary ผ่าน 1,504 Pure Fragments / 3,025 Parent Partitions ไม่มีแก้ Policy ในงานนี้

คงคำเตือน GEOS 3.13.1 Two-stage `C.union(M)` ของ `cti_2568_25042_2203_0`: Area Upper-bound Excess **14.277753561016057 ไร่** และเติมรูเดิมประมาณ 14.2778 ไร่ ตาม Phase 10F ไม่ถือการทำแผนที่เป็นการแก้ Kernel หรือ Independent Engine Certification

## ตัวเลขที่ใช้แสดงผล

| รายการ | พื้นที่ (ไร่) | บทบาท |
|---|---:|---|
| Pure A403 | 107,268.204315689 | ตัวหารเปอร์เซ็นต์ทุก Soil Row |
| Mixed-use excluded | 26,242.638122551 | แสดงแยก ไม่เข้าสู่ตัวหารหรือ Soil Sum |
| SC | 1,609.430313151 | อยู่ใน Pure Denominator / แสดงแยกจาก Other |
| W | 1.236564712 | อยู่ใน Pure Denominator / แสดงแยกจาก Other |
| Uncovered | 3.375539335×10⁻⁹ | อยู่ใน Pure Denominator; มี Geometry แม้ปัดเศษภาพเป็น 0 |

ชื่อหน่วยอ่านจาก Raw Soil **DBF attributes เท่านั้น** (`soilseries` → `soilserien`), ไม่มีอ่าน Soil Geometry มาทำ Overlay ชื่อทุก Source Unit 42 รหัสพบใน Source; Uncovered ไม่ใช่ Source Soil Unit จึงไม่มีชื่อจาก Source ไม่เดาความอุดมสมบูรณ์หรือขยายความหมายรหัส

Top 6 = Knk, Ti, Kkl, Tim, Te, Kc; Other = Ordinary Units ที่เหลือ 34 รหัส แสดงรวมเฉพาะสี/Legend ไม่เปลี่ยนตารางเต็มหรือ Dataset SC/W/Uncovered ไม่อยู่ใน Other จำนวน Category บนภาพ 10 กลุ่ม

พื้นที่ต่างกันในทศนิยมท้ายสุดจากลำดับการรวมเท่านั้น (ระดับประมาณ 10⁻⁹ ไร่) ตัวเลขปัดเศษบนภาพ/Brief ตรงค่าต้นฉบับภายในเกณฑ์เดิม ไม่มีการเพิ่ม QC Tolerance 0.1 ไร่

## Display QC และการตรวจภาพ

- Dataset/Geometry/Lineage เดิมไม่เปลี่ยน; Hash ของทุก Persisted WKT ที่ใช้วาดตรงกับ Record
- Pure Panel 1 และ 3 อย่างละ 1,504 Records; Mixed Panel 3 = 1,407 Records
- Soil Panel ใช้ Soil Intersections + Uncovered ทุก Record ไม่มี Drop Tiny Pieces; พื้นที่รวมตรง Pure Denominator
- ตารางเต็ม 43 แถวคงทุก Field จาก Source Composition; Display Groups รวมกลับได้พื้นที่เดิม ไม่บวก Mixed ซ้ำ
- ขอบเขตอ่านเฉพาะ Tha Mai 2 Records จาก Admin Source ที่ตรวจ Hash แล้ว ใช้ Union สำหรับเส้นขอบแสดงผล ไม่ทำ Raw Land-use/Soil Overlay หรือสร้าง Dataset Geometry ใหม่
- วาด Full-resolution Polygon Paths พร้อม Interior Rings ไม่มี Snap/Buffer/Simplify/Repair
- Map Year 2568, Soil Production Year 2561, EPSG:32647 / WGS 84 UTM Zone 47N, Source Attribution, North Arrow และ Scale Bar 5 km (grid) อยู่ในภาพและ Brief
- Render PDF ด้วย Local Edge/Playwright ไม่มีโหลด Resources ภายนอก ตรวจด้วย pypdf = **2 หน้า** แล้วเรนเดอร์ Poppler PNG ตรวจด้วยตา: ไม่มี Legend/Footnote ซ้อน, ไม่มีข้อความถูกตัด, ภาษาไทยอ่านได้ครบ
- Focused Tests **8/8 ผ่าน**: Preview Tests ใหม่ 3 + Geometry Diagnosis Tests เดิม 5 ไม่รัน Repository Suite ซ้ำ เพราะเพิ่มเฉพาะ Display Tools/Tests ไม่แก้ Production/Review/Acceptance Policy; ผล Repository Phase 10F ยังคงเป็น 374 Python / 30 JS ณ รอบนั้น ไม่อ้างเป็นการรันซ้ำรอบนี้

Protected Baseline รอบ Final v2 **1,231 ไฟล์คงเดิมทั้งหมด**, Unauthorized Changes = 0 รวม Raw GIS, Quarantined/Accepted Proposal, Golden, Review/Exporter/Tests เดิม และ Production ตาม Registry

Production SHA256 คงเดิม:
`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

เพิ่มเฉพาะ `tools/build_tha_mai_advisor_preview.py`, `tools/render_tha_mai_advisor_brief.cjs`, `tests/test_tha_mai_advisor_preview.py`, รายงานนี้ และ Preview Artifacts รุ่นใหม่ ไม่มีแก้ Accepted Proposal/Raw/Production/API/Frontend

## ข้อจำกัดสำหรับหารืออาจารย์

ไม่มี Yield รายอำเภอ, ไม่มี Geometry/พิกัดสวนรายเจ้าของที่ยืนยันแล้ว, Weather รายอำเภอยังไม่พร้อม, Survey/Boundary Effective Dates ไม่ยืนยัน ปี 2568 เป็น Map Footprint ไม่ใช่ Historical Footprint ทุกปี และ Soil Production Year ไม่ใช่วันสำรวจที่ทราบ สิทธิ์เผยแพร่ยัง Pending; ห้าม Publish/Upload Geometry หรือ Preview ภายนอกโดยไม่มีอนุมัติ

การรับรองภายในหมายถึง Persisted Partition ผ่าน Policy v2 ไม่รับรองความแม่นตำแหน่งภาคสนามหรือ Cross-kernel Robustness ไม่มี ML/Yield Analysis, Raw Overlay ใหม่ หรือการขยายอีก 9 อำเภอ

ใช้ Ponytail จำกัดเป็น Display Exporter แยก และ PDF Skill กำหนดให้ Render/Inspect ก่อนส่งมอบ **หยุดรออนุมัติก่อนขยายครบ 10 อำเภอ**
