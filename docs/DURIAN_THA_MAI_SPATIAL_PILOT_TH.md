# Phase 10B — ท่าใหม่ Internal Spatial Soil Pilot

วันที่ 12 ตุลาคม 2026 · AMPHOE_IDN=2203 · **QC FAILED — ไม่ใช่ Accepted Release** · Public HOLD

## ผลตัดสินและเหตุที่หยุด

ทำ Full-resolution Overlay จำกัดท่าใหม่แล้ว แต่ **หยุดก่อนรับรอง Dataset** เมื่อ Independent QC ของ Geometry ที่บันทึกไว้พบความผิดปกติในการ Union Covered กับเศษ Uncovered ของ fragment `cti_2568_25042_2203_0` ห้ามขยายไปอำเภออื่นหรือใช้ข้อมูลนี้วิเคราะห์ต่อจนกว่าจะอนุมัติแก้ปัญหา

Exporter รุ่นแรกตรวจ Arithmetic Reconciliation ผ่านและเขียน `accepted_internal_only` เร็วเกินไป ก่อน Independent Geometry Review ผ่าน **ป้ายดังกล่าวไม่ใช่สถานะสุดท้ายและถูกเพิกถอน** ด้วยบันทึก Append-only:

`C:/project/research_data/internal_research/tha_mai_spatial/phase10b_20261012_failed_validation_v1/STATUS.json`

ไม่แก้/เขียนทับ qc_report หรือ Seal เดิม เพื่อรักษาหลักฐานความล้มเหลว รุ่น `phase10b_20261012_v1` ทั้ง Dataset และ Map เป็น **Quarantined Diagnostic Artifacts เท่านั้น** ไม่มี Accepted Release สุดท้าย

## ขอบเขตและวิธีที่ทำจริง

- Raw LU_CTI_2568, Raw Soil และ Amp/Pro ในเครื่องเท่านั้น ไม่ใช้ display_geometry.json ไม่ดาวน์โหลดหรือเรียก Network Fallback
- ตรวจ Seal Phase 9C/9D, Hash ตาม input_manifest เดิม และ Protected Files; ทุก CRS เป็น EPSG:32647 หน่วยเมตร; พื้นที่ไร่ = m² / 1600
- Amp รหัส 2203 มาจาก source records แบบ 0-based 4 และ 5; ทั้งสอง Valid; Dissolve รวมได้ 391,313.008540 ไร่ ไม่มี Internal/Adjacent Overlap, District Outside Province หรือ Province–Admin Gap ในข้อมูลนี้
- อ่าน Raw LU เพื่อสร้าง Spatial Index; ตรวจ Cohort Pure 8,512 และ Mixed 5,364; ใช้ Index คัด Candidate 2,914 รายการ แล้วตัดเฉพาะส่วนที่สัมพันธ์กับท่าใหม่ ไม่ทำ Soil Overlay ทั้งจังหวัด
- ตัด Parent ด้วยขอบเขตจริง ไม่ใช้ Centroid; เก็บ Parent ID, Source Record, Fragment ID, Full WKT, Geometry Hash, Inside/Remaining/Assigned-other/Unassigned Areas และ Geometry ไม่ Drop ส่วนที่จัดสรรไม่ได้
- ดินใช้ Raw Geometry เต็มและ Spatial Index; เก็บคู่ Fragment–Soil Source Record รวม SC/W; Mixed แยกและ durian_fraction=null ไม่เดาสัดส่วนทุเรียน
- Soil Composition ใช้ Pure A403 ที่ตัดในท่าใหม่ทั้งหมด รวม SC/W/Uncovered เป็นตัวหาร ไม่ใช่ทั้งพื้นที่อำเภอหรือเฉพาะ Covered

พบ Geometry ที่ต้อง make_valid ใน Candidate: Soil 1 และ Land-use 13 รายการ; เหตุผลและ Raw/Repaired Geometry Hash เก็บใน qc_report; การเปลี่ยนพื้นที่แต่ละรายการต่ำกว่า 0.1 ไร่มาก Raw ไม่ถูกแก้ **จำนวนนี้ไม่ใช่การรับรองว่าผ่าน Geometry QC ขั้นสุดท้าย**

## Dataset Preview — ผลเบื้องต้น ห้ามใช้เป็น Accepted Dataset

อยู่ที่ `C:/project/research_data/internal_research/tha_mai_spatial/phase10b_20261012_v1/`

| รายการ | จำนวน/พื้นที่เบื้องต้น |
|---|---:|
| Parent Pure A403 ที่มีพื้นที่ตัดท่าใหม่ | 1,466 |
| Parent Mixed-use ที่มีพื้นที่ตัดท่าใหม่ | 1,392 |
| District Fragments Pure / Mixed | 1,504 / 1,407 |
| Soil Intersection Pieces | 5,332 |
| Uncovered Pieces รวมเศษเชิงตัวเลข | 3,642 |
| หน่วยแผนที่ดิน / Uncovered Summary | 42 / 1 |
| Pure A403 ตัวหาร | 107,268.204316 ไร่ |
| Mixed-use แยกออกทั้งหมด | 26,242.638123 ไร่ |
| SC (อยู่ใน Covered และตัวหารแล้ว) | 1,609.430313 ไร่ |
| W (อยู่ใน Covered และตัวหารแล้ว) | 1.236565 ไร่ |
| Uncovered | 3.375539 × 10⁻⁹ ไร่ |

มี Parent ข้ามขอบเขตที่ Remaining >0.1 ไร่ 157 รายการ; ส่วน Unassigned ของ Parents รวม 6.131135 × 10⁻¹¹ ไร่ยังเก็บไว้ ไม่แทนเป็นศูนย์และไม่ Drop Geometry

| รหัสหน่วยแผนที่ดินจาก Raw | พื้นที่ไร่เบื้องต้น | % ของ Pure ทั้งอำเภอ |
|---|---:|---:|
| Knk | 11,226.186 | 10.46553 |
| Ti | 10,406.475 | 9.70136 |
| Kkl | 9,310.699 | 8.67983 |
| Tim | 8,976.486 | 8.36826 |
| Te | 8,388.589 | 7.82020 |
| Kc | 7,566.029 | 7.05337 |

รักษารหัสตามต้นฉบับ ไม่แก้ชื่อหรืออนุมานความอุดมสมบูรณ์จากรหัส ตารางครบอยู่ใน dataset.json/tables/soil_composition

ไฟล์ที่สร้าง: dataset.json (6 ตาราง, Full-resolution native WKT), source_manifest.json, reproducibility.json, protected_before.json/after.json, qc_report.json, dataset_preview.json, map_preview.png และ output_manifest.json ไม่ใช่ GeoJSON RFC7946 และไม่มี Yield/Weather อำเภอ

## QC ที่ผ่านเบื้องต้น และที่ไม่ผ่าน

Tolerance ล็อก 0.1 ไร่ก่อน Overlay ตาม Phase 10A; Share tolerance = 0.1/Pure denominator×100+10⁻⁹ ≈ 0.0000932253 percentage points ไม่เปลี่ยนเกณฑ์

Arithmetic Checks: Parent = Intersection + Remaining; Remaining = Assigned-other + Unassigned; Pure = Covered + Uncovered; Soil Shares รวม Uncovered = 100.00000000000328%; Max Parent residual 1.520675×10⁻¹¹ ไร่ และ Max fragment soil overlap 1.513399×10⁻¹¹ ไร่ อยู่ภายใน tolerance ส่วนทับ Pure/Mixed 4.181134×10⁻⁹ ไร่

**Independent Persisted-Geometry QC ไม่ผ่าน:**

| การคำนวณสำหรับ fragment ที่หยุด | ไร่ |
|---|---:|
| Fragment เดิม G | 150.2153689297569 |
| Union ของ Soil Cuts C | 150.21536892976334 |
| Union ของ Uncovered Pieces M | 7.34361918497406×10⁻¹² |
| G symmetric_difference C | 2.210377339495473×10⁻¹¹ |
| C union M | **164.49312249078673** |
| G symmetric_difference (C union M) | **14.2777535610422** |

G, C, M และ C union M ต่างรายงาน Valid แต่การ Union เพิ่มพื้นที่ผิดสัดส่วน GEOS 3.13.1 จึงมีหลักฐานของ Numerical/Topological Instability ในขั้นรวมเศษ Geometry; **ยังไม่สรุป Root Cause หรือรับรองวิธีซ่อม** ห้ามอ้างว่า Raw ผิด 14.2778 ไร่ หรือสรุปว่า Soil Composition ผิดเท่ากัน เนื่องจากค่าดังกล่าวเกิดใน Operation เพิ่มเติม ไม่ใช่พื้นที่ Raw/ผลรวมตาราง แต่ก็ไม่เพียงพอให้รับรอง Dataset

หยุดการประมวลผลต่อ ไม่ Snap/Buffer/Simplify/Drop slivers ไม่เปลี่ยน Threshold และไม่ปรับ Tests ให้ปกปิด Failed QC การตรวจครั้งนี้แสดงว่า Arithmetic และ is_valid เพียงอย่างเดียวไม่พอ

## Tests และความคงเดิม

- Geometry/Synthetic Regression ใหม่ 16/16 ผ่าน: Dissolve, Crossing, Missing Admin, SC/W/Uncovered, No Double Counting, Holes, Referential Integrity, Lineage, Immutable JSON, Output Namespace และ Overwrite Protection
- Repository Python รอบก่อนเพิ่ม Independent Review Tests: 347/347 ผ่าน (331 เดิม +16 ใหม่)
- Independent Review เพิ่ม 6 Tests: 3 ผ่าน, 1 Error, 2 Failures; Full Geometry Reconciliation พบกรณีข้างต้น อีกสอง Mutation Tests ถูก Fail-fast ด้วย Geometry Failure ก่อนเข้าถึงข้อความ Denominator/Mixed Exclusions ที่คาดไว้ จึง **ไม่อ้างว่า Mutation Assertions สองข้อนั้นผ่าน**
- JavaScript Repository: 30/30 ผ่าน
- Repository Python รอบสุดท้าย: **350/353 ผ่าน; 2 Failures +1 Error** ใน Independent Review Tests เดียวกับที่ระบุข้างต้น ใช้เวลา 185.757 วินาที ไม่มี Failure ใน 331 Tests เดิมหรือ 16 Synthetic Tests ใหม่ ไม่แก้ Expectations เพื่อทำให้ชุดข้อมูลที่ QC Failed ดูผ่าน

Protected Assets เดิม 1,151 ไฟล์ตรวจ SHA256 คงเดิมทั้งหมด; เทียบชุด Phase 9D 1,123 ไฟล์ด้วย; Seal Phase 9C/9D และ Seal Artifact รอบแรกยังตรง ไม่แก้ Raw/Admin, Production Pipeline, API, Frontend, Phase 9C/9D หรือ Artifacts เดิม

Production Model SHA256:
`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

Dataset SHA256 (Quarantined): `48bdbce32528719effbdea646db162e382a193c28972fd53054808d37223bb2a`

Source Manifest SHA256: `0d80570d1f605aaf4bbb5da9b07653d2ab593bbe262693cf0a795d03726412be`

Original Output Manifest SHA256: `da63abe42246326cd9c4107a3daf0e0d1d0d593c173df83ea67f4aa4d66f8222`

## Map Preview และข้อจำกัด

map_preview.png ที่อยู่ในรุ่น Quarantined มี 3 แผงจริง: District/Pure+Parent Remainder, Soil Units, Pure/Mixed ใช้ Geometry เต็มและไม่ใช้ Tile/Network แต่ **เป็น Draft สำหรับตรวจเท่านั้น** Legend 42 หน่วยยังแน่นและสีบางรหัสซ้ำ; การปรับภาพใน Review หยุดก่อนสร้างเพราะ QC Failed

Land-use ปี 2568 ไม่ยืนยัน Historical Footprint หรือสวนรายเจ้าของ; Soil ปีผลิต 2561 ไม่ใช่วันสำรวจ; Admin Effective Date ยังไม่ยืนยัน; LDD Derived/Geometry Publication Rights Pending; Public HOLD ไม่มี Upload ภายนอก ไม่มี ML/Scenario/Yield/District Weather และ Historical PIT ไม่เปลี่ยนสถานะ

## งานที่ต้องขออนุมัติก่อนดำเนินการต่อ

ไฟล์ใหม่ในรอบนี้: tools/build_tha_mai_spatial_pilot.py, tools/review_tha_mai_spatial_pilot.py, tests/test_tha_mai_spatial_pilot.py, tests/test_tha_mai_spatial_review.py และรายงานนี้ พร้อม Internal Artifacts ใน namespace ท่าใหม่ ไม่มีการแก้ไฟล์เดิม Ponytail ใช้จำกัดงานเป็น Exporter/Review/Tests แยก ไม่รื้อ Pipeline ที่มีอยู่

เสนอ **งานเดียว: Geometry Failure Diagnosis & Robustness Fix** เฉพาะกรณีที่พบ ใช้ Geometry ที่บันทึกไว้ ไม่ Overlay จังหวัดใหม่: สร้าง Minimal Reproducer ตรวจประเด็น Hole/Tiny slivers/GEOS Union เทียบ Directed Difference และ Partition Operations โดยไม่เปลี่ยน tolerance; หากจำเป็นต้องเปลี่ยน Precision Model ต้องเสนอผลกระทบพื้นที่ก่อน ไม่ใช้ Snap/Drop โดยพลการ

ต้องเลื่อน Accepted Status ไปหลัง Independent QC และทุก Tests ผ่าน แล้วสร้างรุ่นใหม่แทนรุ่น Quarantined โดยไม่เขียนทับ เมื่อยังไม่ได้อนุมัติ **หยุดที่ Failed Status และไม่ขยายอำเภอ**
