# Phase 10E — Independent Geometry Verification (Diagnostic Only)

วันที่ 2026-10-12 · Internal Research Only · **QC FAILED / Quarantined · Public HOLD**

## ข้อสรุป

ทวน Golden Fixture เดิมใน 3 Process แยกได้ผลเหมือนกัน: One-pass Union รักษารูเดิม ส่วน Two-stage Union เติมรู 14.2777535610 ไร่ และละเมิด Area Upper Bound อย่างมีนัยสำคัญ แต่ทั้งสามสำเนาใช้ **Python 3.12.14 / Shapely 2.1.2 / GEOS 3.13.1 และ GEOS DLL Hash ชุดเดียวกัน** จึงเป็น Same-kernel Reproduction ไม่ใช่ Cross-version หรือ Independent-engine Verification

ไม่พบ GEOS ต่างรุ่นหรือ Kernel อิสระในขอบเขตเครื่องมือที่ตรวจ ไม่ติดตั้งหรือดาวน์โหลด Dependencies ไม่เปลี่ยน Environment เดิม ไม่สร้าง Accepted Release และไม่เปลี่ยน Acceptance Policy

## Inputs และ Hash Verification

- Golden Fixture: `C:/project/research_data/internal_research/tha_mai_spatial/phase10c_20261012_diagnosis_v1/minimal_inputs.json`
  SHA256 `8fcb42f34be4ada1fd5d786730a2c765ffc06173d08df87a22f5ef08fb49eaeb`
- Quarantined Dataset: `C:/project/research_data/internal_research/tha_mai_spatial/phase10b_20261012_v1/dataset.json`
  SHA256 `48bdbce32528719effbdea646db162e382a193c28972fd53054808d37223bb2a`
- ตรวจ Seals ของ Phase 10B, Failed Status, Phase 10C และ Phase 10D ผ่าน ใช้ Canonical JSON ตามแต่ละ Manifest (10C แบบ compact; รุ่นอื่นใช้รูปแบบเดิม)
- ใช้ G, Soil Cuts 11 รายการ และ Uncovered Pieces 10 รายการจาก Persisted WKT เดิม ไม่สร้าง Geometry จาก Raw GIS ใหม่ ไม่ Snap/Buffer/Simplify/Drop หรือเปลี่ยน Precision Model

## Installed Environment Inventory

| Process | Interpreter / Package Location | ผล |
|---|---|---|
| National analysis | `C:/project/.build/national-analysis-venv/Scripts/python.exe` | Shapely 2.1.2 / GEOS 3.13.1 |
| Bundled + project packages | Bundled Python และ `C:/project/.build/python` | รุ่นและ DLL Hash เหมือนกัน |
| Bundled + soil packages | Bundled Python และ `C:/project/.build/soil-map-packages` | รุ่นและ DLL Hash เหมือนกัน |

Bundled Interpreter คือ `C:/Users/support/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` ใช้ `-I -B` และเลือก Package Path ใน Process ลูกเท่านั้น ไม่มีการแก้ sys.path/ติดตั้งใน Environment ถาวร

ตรวจ Bundled Python โดยไม่เพิ่ม Package Path และ Portfolio Venv: ไม่พบ Shapely ตรวจไฟล์ภายใต้ `.build` และ Codex Runtime Cache: พบ GEOS DLL เฉพาะสามสำเนาข้างต้น ไม่มี Alternate Version ที่พร้อมใช้ ตรวจ PATH สำหรับ QGIS/OGR/GEOS CLI/Conda/Java/Rscript และ Program Files สำหรับ QGIS/OSGeo/Python/PostgreSQL/ArcGIS: ไม่พบเครื่องมือที่พร้อมใช้ในตำแหน่งเหล่านี้ ตรวจ package.json ใต้ `.build`/Runtime Cache: ไม่พบ JSTS, polygon-clipping, martinez-polygon-clipping, polyclip-ts, clipper-lib หรือ @turf/union

นี่เป็น Inventory ในตำแหน่งที่ตรวจ ไม่ใช่คำรับรองว่าไม่มี Kernel อื่นที่ใดเลยบนเครื่อง Dependency Chain ที่ทดสอบจริงคือ **Python → Shapely → GEOS C API → GEOS** การใช้ชื่อ Environment ต่างกันไม่ทำให้หลักฐานเป็นอิสระ

## Minimal Reproducer Results

| การตรวจ | One-pass Original Cuts + Uncovered | Two-stage C.union(M) |
|---|---:|---:|
| Area (ไร่) | 150.215368929771 | 164.49312249078673 |
| Symmetric Difference กับ G (ไร่) | 1.7623250637×10⁻¹¹ | 14.2777535610422 |
| พื้นที่นอก G (ไร่) | 1.6240765399×10⁻¹¹ | 14.2777535610366 |
| พื้นที่ G ที่ขาด (ไร่) | 1.3824719147×10⁻¹² | 5.6368588963×10⁻¹² |
| พื้นที่เติมรูเดิมรูที่ 0 (ไร่) | 1.8553514280×10⁻¹² | 14.2777535610230 |
| พื้นที่เติมรูเดิมรูที่ 1 (ไร่) | 0 | 0 |
| G.covers(result) / result.covers(G) | false / false | false / false |

G Area = 150.2153689297569 ไร่; C = 150.21536892976334; M = 7.34361918497406×10⁻¹² ไร่ One-pass/Two-stage และ Operation Matrix 20 รายการตรงกันทุก Process ทั้ง WKT/WKB Roundtrip และ Stored Geometry Hashes ตรงกัน เก็บ Validity, Hole Counts, Orientation, Coordinate Count, Bounds และ Precision Model ใน JSON ราย Process

Boolean Containment ของ One-pass ไม่ผ่านแบบ exact แม้ Directed Difference เล็กมาก จึงต้องอ่านคู่กับ Area Residuals ไม่ใช้ Boolean หรือ Hole Count เพียงตัวเดียวรับรองผล QC Tolerance เดิม **0.1 ไร่คงเดิม**; Self-check ใช้ 10⁻⁸ ไร่เฉพาะตรวจการเกิดซ้ำของตัวเลข Hole Filling ไม่ใช่เพิ่ม QC Tolerance

## Root-cause Confidence และ Evidence Gaps

**ยืนยันได้:** Operation Path ให้ผลขัดแย้งบน Input เดียวกัน Two-stage เพิ่มพื้นที่รูซึ่ง C และ M ไม่ได้ครอบคลุม และเกิน Area(C)+Area(M) ประมาณ 14.2778 ไร่ ไม่ใช่แค่ความต่างระดับ Roundoff ของผล Area การเปลี่ยน Process/Package Copy ไม่แก้ปัญหา และไม่พบความต่างจาก Serialization/Stored Hash ใน Fixture นี้

**ยังเป็นสมมติฐาน:** พิกัดเกือบซ้อน/ชิ้นพื้นที่เล็กอาจกระตุ้น Numeric Robustness ใน Noding/Polygonization แต่ไม่ได้พิสูจน์ตำแหน่งภายใน GEOS ไม่อาจระบุว่า GEOS รุ่นใดแก้แล้ว หรือว่าเป็นปัญหาเฉพาะรุ่น 3.13.1

**ยังสรุปไม่ได้:** Data Geometry ไม่มี Defect ทั้งหมด หรือ Kernel อิสระจะให้ One-pass ถูกต้อง เพราะทุก Operation ที่ทดสอบยังใช้ GEOS เดียวกัน is_valid เป็นหลักฐานประกอบ ไม่ใช่ Independent Validation ไม่มีการอ่าน Raw/ทำ Overlay ใหม่หรือ Recertify ทุก Fragment ในรอบนี้

## Acceptance Policy ที่เสนอ (ยังไม่ใช้)

1. **คง Fail-closed จนมี Independent Evidence:** เก็บ Inconclusive เมื่อมี Material Contradiction ตามกฎเดิม ขออนุมัติ Environment แยกที่ใช้ GEOS คนละรุ่น และถ้าเป็นไปได้ Kernel ที่ไม่เรียก GEOS ตรวจ Fixture เดิมพร้อม Hashes/Differences/Holes/Area Bounds ค่าใช้จ่ายหลักคือจัด Environment และ Adapter; ประเมินเบื้องต้น GEOS อีกชุดประมาณ 0.5–1 วันทำงาน ส่วน Kernel ต่างตระกูลประมาณ 1–2 วัน ไม่รวมความล่าช้าจาก Dependency Compatibility เป็นประมาณการ ไม่ใช่ผล Benchmark
2. **กำหนด Canonical Partition Review เมื่อพิสูจน์ Operation Path ได้แล้ว:** ใช้ Original Pieces One-pass + Directed Differences/Containment Residuals + Pairwise Disjointness + Area Bounds + Original-hole Preservation เป็น Acceptance Invariants ทั่วไป Two-stage ที่พิสูจน์เป็นปัญหา Kernel ให้คงเป็น Diagnostic Warning พร้อม Version/Path Evidence ไม่ยกเว้นตาม Fragment ID หาก Primary Invariants ขัดแย้งกันให้ Inconclusive เสมอ **ยังไม่พร้อมใช้ทางเลือกนี้** จนมีหลักฐานอิสระและการอนุมัติ Policy/Test Contract แยกต่างหาก

ก่อนสร้าง Accepted Release ต้องยืนยัน Kernel/Version ต่างกันจริง, Input Coordinates/Hashes เดิม, ไม่มี Repair/Precision Change, ตรวจ Golden และ Synthetic Negative Fixtures, ตรวจครบ 1,504 Pure Fragments ภายใต้ Policy ที่อนุมัติ, ผ่าน Area/Topology/Lineage เดิมและ Repository Tests ทั้งหมด ต้องเก็บรุ่น Failed เดิมและ Public HOLD โดยไม่มีการเปลี่ยน Dataset Composition/IDs/Geometry

## Artifacts, Tests และ Protection

เพิ่มเฉพาะ `C:/project/tools/verify_tha_mai_geometry_environment.py`, รายงานนี้ และ Evidence Folder รุ่นใหม่:
`C:/project/research_data/internal_research/tha_mai_spatial/phase10e_20261012_verification_v1/`

ใน Folder มีผลแต่ละ Process, `comparison.json`, Inventory, Preflight/Final Protected Verification และ Output Manifest พร้อม Code/Fixture/Interpreter/DLL SHA256 ตัว Reproducer ปฏิเสธการเขียนทับผลเดิม ใช้ Subprocess แยก ไม่มี Network หรือ Import ที่ติดตั้ง Dependencies

Diagnostic Self-checks ผ่าน; Tests เดิมที่เกี่ยวข้อง **16/16 ผ่าน** (`test_tha_mai_geometry_diagnosis`, `test_robust_tha_mai_geometry_review`) ไม่แก้ Tests/Expected Values ใด ไม่รัน Repository Suite ซ้ำเพราะไม่ได้แก้ Caller/Logic เดิม และ Phase 10D มี Known Blocker: Full Persisted Geometry Test ยังต้องการ Pass แต่ Review ให้ Inconclusive ข้อผิดพลาดนี้ไม่ได้หายไปจากผล 16 Tests

Protected Baseline **1,192 ไฟล์คงเดิมทั้งหมด** รวม Raw GIS, Quarantined/Golden/Phase 10D Artifacts, Exporter, Review, Tests เดิม, Production/API/Frontend ตาม Registry เดิม Production Model SHA256:
`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

ใช้ Ponytail จำกัดงานเป็น Reproducer แยกและ Assert-based Self-check ไม่แก้ Pipeline เดิม ข้ามการติดตั้ง/Full Overlay/Training/Accepted Release ความเสี่ยงที่เหลือคือ **Independent Kernel Verification ยังทำไม่ได้จาก Dependencies ที่มี** หยุดรออนุมัติก่อนติดตั้ง Environment ใหม่ เปลี่ยน Policy หรือสร้าง Release
