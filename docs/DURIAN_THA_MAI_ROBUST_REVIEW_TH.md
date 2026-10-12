# Phase 10D — Robust Geometry Review Fix

12 ตุลาคม 2026 · Internal Research · **Acceptance Gate ไม่ผ่าน — QC FAILED / Quarantined คงเดิม · Public HOLD**

## ผลตัดสิน

เพิ่ม Review Algorithm ที่ตรวจด้วยหลาย Invariants และไม่มีการยกเว้น Golden Fragment แล้ว แต่ **ยังไม่สร้าง Accepted Release** เพราะ `cti_2568_25042_2203_0` มีผลของ Geometry Operations ขัดแย้งกันเกินเกณฑ์ 0.1 ไร่ การเปลี่ยนไปใช้ One-pass เพียงอย่างเดียวแล้วประกาศผ่านจะขัดข้อกำหนดข้อ 7 และ Acceptance Gate

| การตรวจครบชุด | Pass | Failed | Inconclusive |
|---|---:|---:|---:|
| Pure Fragments รวม 1,504 | 1,503 | 0 | 1 |
| Parent Partitions รวม 3,025 | 3,025 | 0 | 0 |

Parent Partitions ประกอบด้วย 2,858 Parent และ 167 Remaining ที่ไม่ Empty ตรวจโดยไม่ Drop เศษเล็กหรือ Unassigned Geometry; Mixed Exclusions ตรวจแยกไม่จัดสรรเป็น Pure

## Algorithm ที่เพิ่ม

ชื่อ: `directed_partition_holes_onepass_conflict_guard_v1`

GEOS **3.13.1** / Shapely **2.1.2** คงเดิม Precision Model 0.0 คงเดิม ไม่มี Snap, Buffer, Simplify, Drop Slivers หรือแก้ Geometry

1. ตรวจ CRS, FK/Unique Keys, Geometry Validity, Full-resolution WKT/Hash, Stored Areas, Lineage และ Mixed Exclusions ก่อน Geometry Operations ไม่ถือ Validity เป็นหลักฐานเดียว
2. ตรวจ Soil Cuts และ Uncovered ทั้งคู่ระดับชิ้นและ Aggregate: การนับซ้ำ, Containment ใน G, Covered–Uncovered Disjointness และ Area Reconciliation
3. ตรวจ `G−C` เทียบ M ด้วย Directed Differences สองทิศ: ไม่มี Missing Area ที่ไม่ถูกบันทึก และไม่มี M ที่เกินส่วนขาดจริง
4. Cross-check One-pass Union ของ **Original Soil Cuts + Uncovered Pieces ทุก Pure Fragment 1,504 รายการ** ตรวจ Area Upper/Lower Bounds, Directed Missing/Excess และ Containment ของ Inputs ไม่ใช้ Area Sum หรือ One-pass อย่างเดียว
5. ตรวจรูเดิมทุกวงจาก G: Intersection กับ Original Pieces, C, M และ One-pass ต้องไม่เติมรู ไม่ตรวจแค่จำนวนรู
6. ตรวจ Two-stage Union เทียบ One-pass/G และรูเดิม หากขัดแย้งเกิน 0.1 ไร่ให้ Inconclusive ไม่ซ่อน Operation ที่ผิดและไม่เปลี่ยนสถานะเป็น Pass
7. ตรวจ Parent Inside/Remaining/Assigned-other/Unassigned แบบเดียวกัน รวม Pure/Mixed Global Overlap และ Soil Composition/Denominator/Shares

ทุก Area/Topology Allocation Gate ใช้ **0.1 ไร่เดิม**; ไม่เพิ่ม Threshold เพื่อกลบความต่าง การตรวจ Metadata area_m2 เป็นการตรวจความสอดคล้องเพิ่มเติม ไม่ลดทอน Area Allocation Gates

## Golden Fixture — ไม่มี Waiver

Fixture ใช้จาก Sealed Phase 10C: minimal_inputs.json, G +11 Soil Cuts +10 Uncovered Pieces โดยไม่แก้ Input หรือ Source Record

| หลักฐานสำหรับ Golden Fragment | ไร่ |
|---|---:|
| G | 150.2153689297569 |
| C | 150.21536892976334 |
| M | 7.34361918497406×10⁻¹² |
| One-pass Union | 150.215368929771 |
| Two-stage Union | **164.49312249078673** |
| Two-stage Union เกิน Area Upper Bound | **14.277753561016057** |
| Two-stage Union ครอบคลุมรูเดิม | **14.277753561022969** |

Primary Directed/Containment/Disjointness/Hole/Area Checks ผ่าน แต่ Two-stage Union ผิด Area Bound, มีพื้นที่เกิน One-pass/G และเติมรูเดิม จึงเป็น **Review Inconclusive** ตามกฎทั่วไป ใช้ชื่อ Fragment อะไรก็ไม่สามารถยกเว้นได้ Regression Test ใช้ Label ทั่วไปเพื่อยืนยันว่าไม่มี Special Case

One-pass Checks ผ่านทุก 1,504 Fragment แต่ไม่ได้ยกระดับเป็น Accepted เพราะยังมี Contradiction หนึ่งกรณี การตรวจ Global Double Counting และ Pure–Mixed Overlap ผ่านเช่นกัน

## ความคงเดิมของข้อมูล

Dataset Byte SHA256 ก่อนและหลังตรงกัน:
`48bdbce32528719effbdea646db162e382a193c28972fd53054808d37223bb2a`

Logical Dataset Digest ก่อน–หลังตรง ไม่มีแก้ Soil Areas, Soil Composition, Parent IDs, Fragment IDs, Geometry WKT/Hashes, Source IDs หรือ Lineage ทุก Source File Hash ตรง Source Manifest เดิม และ Sealed Failed/Quarantined/Golden Artifacts ไม่เปลี่ยน

Protected Baseline **1,179 ไฟล์**: **1,178 ไฟล์คงเดิม** และ **1 ไฟล์เปลี่ยนตามอนุมัติ** คือ tools/review_tha_mai_spatial_pilot.py; สำรองเนื้อหา Review เดิมกับ Original Hash ในโฟลเดอร์รอบใหม่ก่อนแก้ Snapshot มี Hash/Code ที่เกี่ยวข้องเท่านั้น ไม่มี Secrets

Production Model SHA256 คงเดิม:
`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

## ไฟล์ที่เปลี่ยนและ Tests

- แก้ `C:/project/tools/review_tha_mai_spatial_pilot.py`: เปลี่ยน verify() ให้ใช้ Robust Review และ Raise ReviewError เมื่อ Failed/Inconclusive; Caller ยัง Fail-closed ไม่เขียน Accepted Artifacts เมื่อไม่ผ่าน
- เพิ่ม `C:/project/tools/robust_tha_mai_geometry_review.py`: Review หลาย Invariants พร้อม Conflict Guard
- เพิ่ม `C:/project/tools/run_tha_mai_robust_review.py`: ตรวจ Hashes/Seals, Source Lineage, Review ครบชุดและสร้างรายงานรอบใหม่แบบไม่เขียนทับ
- เพิ่ม `C:/project/tests/test_robust_tha_mai_geometry_review.py`: 11 Regression Tests รวม Golden Hole Filling, Altered Cut, Overlapping Cuts, Missing Uncovered, Covered/Uncovered Overlap, Outside Geometry, Invalid Geometry, Hole Preservation และ Tiny Pieces ไม่ถูก Drop
- เพิ่มรายงานนี้และ Diagnostic Review Artifacts รุ่นใหม่ ไม่มี Dataset Release ใหม่

**Tests เดิมทุกไฟล์และ Expected Values ไม่ถูกแก้** รวม Missing Mixed Exclusion/Denominator/Geometry Hash Tests; Tests เหล่านี้ถูกตรวจ Structural ก่อนเข้า Geometry Operations แล้ว ไม่ถูกกลบด้วย Golden Failure แบบเดิม

Tests ใหม่เฉพาะ Robust Review **11/11 ผ่าน**; JavaScript Repository **30/30 ผ่าน**; Python Repository **368/369 ผ่าน, 1 Error** (272.728 วินาที) คือ test_full_persisted_geometry_reconciliation เดิมซึ่งยังคาดสถานะ Pass แต่ verify() ปฏิเสธด้วย Review Inconclusive ของ Golden Fragment ไม่เปลี่ยน Expected Value; Mutation Tests เดิมเรื่อง Mixed Exclusions และ Denominator ผ่านแล้ว

Artifacts อยู่ที่ `C:/project/research_data/internal_research/tha_mai_spatial/phase10d_20261012_review_v1/`: summary.json, review_report.json, protected_verification.json, preflight_protected_hashes.json และ review_before.py; รายงานเป็น Internal Evidence ไม่ใช่ Accepted Dataset

## Acceptance Gate และการหยุด

- ไม่แก้ Geometry/Areas/Composition/Lineage: ผ่าน
- Original QC Tolerance/Versions/Protected Inputs: ผ่าน
- Cross-check One-pass ครบ 1,504 และ Parent/FK/Area/Overlap: ผ่าน
- **ไม่มี Unresolved Material Contradiction: ไม่ผ่าน**
- **Tests ทั้ง Repository ต้องผ่าน: ไม่ผ่าน — 1 Error ตาม Gate ที่ยังถูกบล็อก**

จึงคง Phase 10B **QC FAILED / Quarantined** และ **Public HOLD** ไม่มีการเปลี่ยน Raw, Dataset รุ่นเดิม, Production/API/Frontend ไม่มี Training/เพิ่มพื้นที่/Upload

ข้อจำกัด: ยังไม่ได้ตรวจ Independent Kernel/GEOS เวอร์ชันอื่น และไม่รู้ Internal GEOS Root Cause ที่ทำให้เติมรู วิธี Review ใหม่ตรวจจับความขัดแย้งได้ แต่ไม่ได้แก้ Kernel นั้น การรับรองโดยละเว้น Two-stage Failure ต้องมีนโยบาย/หลักฐานใหม่และอนุมัติแยก ไม่ดำเนินการเอง

ใช้ Ponytail จำกัดการแก้เป็น Review Module/Caller และ Tests โดยเก็บ Exporter/Dataset เดิม หยุดรออนุมัติก่อนทำงานต่อหรือขยายพื้นที่
