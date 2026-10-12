# Phase 10F — Evidence-based Geometry Acceptance Policy

2026-10-12 · Tha Mai, AMPHOE_IDN 2203 · Internal Research Only · **Public HOLD**

## นโยบายและขอบเขตการรับรอง

ใช้การอนุมัติ Phase 10F เปลี่ยน Acceptance Contract จาก Phase 10D: Primary Invariants เป็นตัวตัดสิน ส่วน Two-stage Union ที่ละเมิด Area Upper Bound เกินเกณฑ์เดิม 0.1 ไร่บันทึกเป็น Kernel/Operation Diagnostic Warning ไม่เป็น Veto อัตโนมัติ นี่เป็นการเปลี่ยน Policy ที่อนุมัติ ไม่ใช่การอ้างว่า GEOS ถูกแก้แล้ว หรือผ่าน Independent Kernel Verification

Algorithm: `directed_partition_holes_onepass_upper_bound_warning_v2` · Shapely 2.1.2 / GEOS 3.13.1 · Floating Precision grid 0.0 · QC Tolerance **0.1 ไร่เดิม**

Primary Checks:

1. Stored WKT/Geometry Hash, CRS, Validity, Source Lineage, Unique Keys และ Referential Integrity
2. Containment แบบ Directed Area Residuals ทั้ง Original Pieces และ Aggregates เทียบ G ไม่ตัดสินด้วย exact Boolean covers เพียงตัวเดียว
3. Disjointness: Pairwise Soil/Uncovered Overlap เพิ่มจาก Sum-versus-union เดิม และ Covered–Uncovered Overlap
4. Directed Missing `G−C` เทียบ Persisted M สองทิศ ไม่มีส่วนขาดหรือเกินที่ไม่ถูกบันทึก
5. Original Hole Preservation เทียบ Original Pieces, C, M และ One-pass ไม่ใช้เพียง Hole Count
6. One-pass Original Partition: Missing/Outside, Area Upper/Lower Bounds และ Input Containment
7. Parent Inside/Remaining/Assigned-other/Unassigned, Global Pure/Mixed Overlap และ Soil Composition/SC/W/Uncovered Denominator Reconciliation

Primary Check ที่ผิดเกินเกณฑ์ให้ FAILED; Operation Error ให้ INCONCLUSIVE; ความขัดแย้ง Two-stage ที่ไม่มีหลักฐานละเมิด Upper Bound ยังคง INCONCLUSIVE ทุก Fragment ใช้กฎเดียวกัน ไม่มี Exception ตาม ID และ Warning ไม่สามารถ Override Primary Failure

## ผลตรวจครบชุด

| รายการ | Pass | Failed | Inconclusive |
|---|---:|---:|---:|
| Pure Fragments | 1,504 | 0 | 0 |
| Parent Partitions | 3,025 | 0 | 0 |

Parent Partitions = 2,858 Parents + 167 Nonempty Remaining Partitions รวม 4,529 Partition Reports, **90,691 Primary Checks**, Failed Primary Checks = 0 ค่าสูงสุดของ Absolute Area Residual = **2.0954757928848267×10⁻¹⁰ ไร่** (One-pass Area Reconciliation) Global Pure/Mixed Double Counting และ Pure–Mixed Overlap ผ่าน

Golden Fixture ใช้ G + Soil Cuts 11 + Uncovered Pieces 10 จาก Phase 10C เดิม Primary Checks ผ่าน แต่ยังบันทึกคำเตือนหนึ่งรายการ:

- Fragment `cti_2568_25042_2203_0`
- Operation `C.union(M)`, GEOS 3.13.1
- Area Upper-bound Excess **14.277753561016057 ไร่**
- พื้นที่เติมรูเดิม **14.277753561022969 ไร่**
- Warning: `kernel_operation_upper_bound_violation`

ไม่ลบหลักฐานจาก Phase 10C–10E ไม่ปรับ Geometry เพื่อหลีกเลี่ยงปัญหา Original Warning/Conflicts/Hole Measurements อยู่ใน QC Report รุ่นใหม่ การทดสอบ Golden ใช้ Label ทั่วไปเพื่อพิสูจน์ว่า Policy ไม่ผูกกับ Fragment ID

## Mutation และ Regression Tests

Review Contract Tests 16/16 ผ่าน รวม Missing Piece, Overlapping Soil, Hole Filling, Outside Geometry, Duplicate Fragment และ Mixed-use Soil Contamination; เพิ่มกรณี Warning + Primary Failure ต้อง FAILED, Unexplained Binary Contradiction ต้อง INCONCLUSIVE และ Primary Operation Error ต้อง INCONCLUSIVE

เปลี่ยน Golden Test เฉพาะ Acceptance Status จาก Inconclusive เป็น Pass-with-warning ตาม Policy ที่อนุมัติ ค่าพื้นที่ที่คาดหมายเดิม, Hole Filling Magnitude, Input Hash และ Geometry Immutability Assertions คงเดิม ไม่แก้ Tests เดิมที่ตรวจ Full Persisted Dataset/Denominator/Builder Seal

Repository Python **374/374 ผ่าน** (365.838 วินาที), JavaScript **30/30 ผ่าน**, ไม่มี Skipped/Failed ใน JS ทั้งสอง Suite Return Code 0 Full Persisted Geometry Reconciliation Test เดิมผ่านโดยไม่ได้แก้ Expected Value ของ Test นั้น Gate ผ่านและสร้าง Internal Accepted Release Proposal รุ่นใหม่แล้ว

## ความคงเดิมและ Artifacts

ก่อนแก้ตรวจ Seals ของ Phase 10B/Failed/10C/10D/10E และ Source Hashes ผ่าน สำรองเนื้อหา Review Module/Tests เดิมและ Hash Inventory โดยไม่มี Secrets

Dataset SHA256 เดิม:
`48bdbce32528719effbdea646db162e382a193c28972fd53054808d37223bb2a`

Golden Fixture SHA256:
`8fcb42f34be4ada1fd5d786730a2c765ffc06173d08df87a22f5ef08fb49eaeb`

Production Model SHA256:
`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

แก้เฉพาะ:

- `C:/project/tools/robust_tha_mai_geometry_review.py`: Policy v2, Pairwise Disjointness, Warning Records
- `C:/project/tests/test_robust_tha_mai_geometry_review.py`: Acceptance Contract และ Mutation Tests

เพิ่ม `C:/project/tools/run_tha_mai_acceptance_policy.py`: ตรวจ Seals/Sources/Protected Hashes, Review ครบชุด, รัน Repository Suites และสร้าง Proposal หลัง Gate เท่านั้น ไม่มี Overlay/ดาวน์โหลดข้อมูลภายนอก/Training; Output Paths แบบรุ่นใหม่ ปฏิเสธการเขียนทับ Repository Tests ใช้ Local HTTP Test Servers ตาม Suite เดิม ไม่ใช่การโหลด GIS ใหม่

Evidence: `C:/project/research_data/internal_research/tha_mai_spatial/phase10f_20261012_policy_v1/` รวม Code Before, Authorized Diff, Review/Primary Summary, Tests, Provenance และ Protected Verification

Release Proposal ที่สร้างหลัง Gate ผ่าน: `C:/project/research_data/internal_research/tha_mai_spatial/phase10f_20261012_internal_accepted_proposal_v1/` โดย Dataset/Source Manifest เป็น Byte-identical Copies และแยก Release Metadata/Review Evidence ใหม่ ไม่แก้ Historical Dataset Metadata หรือรุ่น Quarantined เดิม Status = `internal_accepted_proposal`; QC = `accepted_under_phase10f_primary_policy`; Public = `HOLD` พร้อม Warning Count 1 และ Output Manifest ที่ตรวจ Seal ผ่าน

Protected Registry **1,203 ไฟล์**: **1,201 คงเดิม**, เปลี่ยน **2 ไฟล์ตามอนุมัติ** คือ Review Module กับ Tests ของมัน, Unauthorized Changes = 0 Production Model Hash ตรงค่าข้างต้นหลัง Repository Suites ไม่มีเปลี่ยน Exporter, Caller เดิม, Raw GIS, Dataset, Soil Areas/Composition, IDs, Lineage, API หรือ Frontend Hash ของ Review/Runner/Tests และ GEOS/Python Versions อยู่ใน `provenance.json` และ Release Metadata สำรอง Git Status เดิมและ Diff จากไฟล์ก่อนแก้เพื่อแยกจาก Changes เดิมที่มีอยู่

## ข้อจำกัดและการหยุด

เป็นการยอมรับความสอดคล้องของ Persisted Partition ภายใต้ Policy ที่อนุมัติ ไม่รับรองความแม่นตำแหน่งภาคสนาม, Raw Overlay ใหม่, ความถูกต้องระดับเจ้าของสวน หรือ Independent Kernel Robustness ทั้งหมดยังใช้ GEOS เดียวกัน Warning จึงต้องตามไปกับ Release เสมอ

ไม่มีติดตั้ง GEOS, Snap/Buffer/Simplify/Drop Slivers, Overlay ใหม่, ML/Yield Analysis, ขยายอำเภอ หรือ Upload Dataset **Public HOLD คงเดิม** รุ่น Failed/Quarantined เดิมคงเดิมและห้ามนำ Proposal ไปเผยแพร่โดยอัตโนมัติ

ใช้ Ponytail จำกัดการแก้ไว้ที่ Review Policy/Tests และ Runner ของ Release Gate หยุดรอคำสั่งหลังเสนอผลภายใน
