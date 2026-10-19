# Phase 10C — Tha Mai Geometry Failure Diagnosis

12 ตุลาคม 2026 · Read-only diagnosis · **Phase 10B QC FAILED / Quarantined คงเดิม · Public HOLD**

## ข้อสรุป

พิสูจน์กลไกของความผิดปกติได้ในสภาพแวดล้อมปัจจุบัน: **การ Union แบบสองขั้น C.union(M) เติมรูเดิมของ G ขนาด 14.277753561 ไร่** ทั้งที่ C และ M ต่างไม่มีพื้นที่อยู่ในรูนั้น ไม่ใช่เพียงค่าพื้นที่ปัดเศษผิด เพราะตรวจ Intersection กับพื้นที่รูแล้วพบว่ารูถูกครอบคลุมเกือบเต็มจริง

พบใน **1 จาก 1,504 Pure Fragments** เมื่อใช้การตรวจแบบเดียวกับ Independent Review โดยอ่าน Persisted Artifacts เท่านั้น ไม่มี Operation Error ระหว่างสแกน ไม่มีการโหลด Raw Geometry มาทำ Overlay ใหม่

**ไม่พบหลักฐานว่า Soil Area/Composition ที่ Export ไว้เพิ่มขึ้น 14.2778 ไร่** การสร้าง C จาก Soil Cuts และตารางพื้นที่ยังสอดคล้องกับ G ภายในเศษเชิงตัวเลข ความผิดปกติที่ยืนยันเกิดใน Operation เพิ่มเติมของ Independent Review อย่างไรก็ตามยังไม่รับรอง Dataset หรือเปลี่ยนสถานะ Failed

## Input, Versions และวิธีทำซ้ำ

อ่าน Dataset และตรวจ Seal/Hashes ของ:

- `C:/project/research_data/internal_research/tha_mai_spatial/phase10b_20261012_v1/`
- `C:/project/research_data/internal_research/tha_mai_spatial/phase10b_20261012_failed_validation_v1/`

ตรวจ Dataset SHA256 ตรง Failed Status: `48bdbce32528719effbdea646db162e382a193c28972fd53054808d37223bb2a`

Fragment: `cti_2568_25042_2203_0`; Parent Source Record 25042; G 1 ชิ้น, Soil Cuts 11 ชิ้น, Uncovered Pieces 10 ชิ้น แยก Fixture เฉพาะกรณีนี้โดยเก็บ WKT/Hash/Lineage เดิม ไม่มี Snap/Buffer/Simplify/Drop/เปลี่ยน Precision หรือแก้ Geometry

สภาพแวดล้อม: Python **3.12.14**, Shapely **2.1.2**, GEOS **3.13.1**, Windows 11; EPSG:32647, พื้นที่ m²/1600 เป็นไร่

Minimal Reproducer แยกจาก Exporter:

```powershell
& C:/project/.build/national-analysis-venv/Scripts/python.exe -X utf8 -B C:/project/tools/diagnose_tha_mai_geometry.py --fixture C:/project/research_data/internal_research/tha_mai_spatial/phase10c_20261012_diagnosis_v1/minimal_inputs.json
```

ทดสอบ CLI แล้วเกิด Anomaly เดิม และเรียก diagnose(Fixture) ซ้ำได้ Output Digest เดียวกับ operations.json ทุกครั้งที่ตรวจ ไม่ต้องโหลด Raw SHP, Pipeline หรือทำ Spatial Overlay

## Geometry Diagnostics

| รายการ | G | C = union_all(Soil Cuts) | M = union_all(Uncovered) |
|---|---|---|---|
| Type | Polygon | Polygon | MultiPolygon |
| Validity | Valid Geometry | Valid Geometry | Valid Geometry |
| จำนวน Polygon / Holes | 1 / 2 | 1 / 2 | 10 / 0 |
| จำนวน Coordinates รวมจุดปิด Ring | 70 | 91 | 40 |
| Precision grid size | 0.0 | 0.0 | 0.0 |
| Area ไร่ | 150.2153689297569 | 150.21536892976334 | 7.34361918497406×10⁻¹² |

G/C Bounds ตรงกัน: (820044.5890744315, 1416710.916745471, 820686.820804418, 1417433.1635176302) เมตร M Bounds อยู่ภายในช่วงดังกล่าว ทุก Input ไม่ Empty

G/C Exterior CW, Holes CCW; M Exterior CW ทั้ง 10 ชิ้น ไม่มีหลักฐานว่าทิศทาง Ring ผิดแบบเห็นได้ตรง ๆ M เป็นสามเหลี่ยมเล็กมากเชิงพื้นที่ (4 Coordinates รวมจุดปิด) ไม่ได้หมายความว่า Bounding Box เล็กเท่ากัน รายละเอียด Area/Bounds/Orientation/Minimum Nonzero Axis Spacing อยู่ใน operations.json

Precision grid 0.0 หมายถึง Floating Precision Model ที่ตรวจจาก Geometry ไม่ใช่หลักฐานความละเอียดของการสำรวจ ใช้ WKT Full Precision เดิม; Coordinate spacing ไม่ใช่ค่าความคลาดเคลื่อนเชิงตำแหน่งของ LDD

## ตาราง Geometry Operations

| Operation บน Input ที่ไม่เปลี่ยน | Area ไร่ | Holes | ผล |
|---|---:|---:|---|
| C.union(M) | 164.49312249078673 | 3 | Union upper bound ผิด |
| M.union(C) | 164.49312249078676 | 3 | เปลี่ยน Operand Order ไม่แก้ปัญหา |
| union_all([C,M]) / [M,C] | 164.4931224907941 | 2 | ยังเติมรูเดิม |
| unary_union([C,M]) | 164.4931224907941 | 2 | เปลี่ยนชื่อ API ไม่แก้ปัญหา |
| union_all(cuts+missing) | 150.215368929771 | 2 | ไม่เกิดพื้นที่เกินในกรณีนี้ |
| union_all(reversed(cuts+missing)) | 150.215368929771 | 2 | กรณีนี้ยังได้ผลสอดคล้อง |
| G.union(M) | 150.2153689297569 | 2 | ไม่เติมรู |
| G.difference(C) | 7.343633617873379×10⁻¹² | 0 | พื้นที่ที่ขาดเล็กมาก |
| C.difference(G) | 1.4760136446412274×10⁻¹¹ | 0 | ส่วนเกินเล็กมาก |
| G.intersection(C) | 150.215368929748 | 2 | สอดคล้องกับ G/C |
| G.symmetric_difference(C) | 2.210377339495473×10⁻¹¹ | 0 | G/C ต่างเพียงเศษเชิงตัวเลข |
| G.symmetric_difference(C.union(M)) | 14.2777535610422 | 0 | Independent Review จึงหยุดถูกต้อง |

ครบ 20 Operations ใน OPERATIONS.md/operations.json รวม Intersection, Difference ทั้งสองทิศและ WKT/WKB Roundtrip

ตรวจ Upper Bound `area(C union M) ≤ area(C)+area(M)` ด้วย Diagnostic Numerical Tolerance `max(10⁻⁶ m², 64×ulp(max input area))` กรณีนี้คือ **10⁻⁶ m² = 6.25×10⁻¹⁰ ไร่** เป็น Roundoff Diagnostic ไม่ใช่การเปลี่ยน QC Contract เดิม 0.1 ไร่ ผลเกิน 14.277753561016052 ไร่ จึงเกินทั้งสองเกณฑ์อย่างชัดเจน

ติดตามรูของ G โดยตรง:

- รูที่ 0: 14.277753561022967 ไร่; C ครอบคลุมเพียง 1.855351×10⁻¹² ไร่, M=0; หลัง C.union(M) ครอบคลุม **14.277753561022969 ไร่**
- รูที่ 1: 1.8613564342515627 ไร่; C/M และผล Union ไม่ครอบคลุมรูนี้

จำนวน Holes ในผล Union เพิ่มเป็น 3 ไม่ได้แปลว่ารูเดิมยังอยู่ครบ จึงต้องตรวจพื้นที่/ตำแหน่งรู ไม่ใช้ Hole Count อย่างเดียว

## Serialization, Construction และ Directed Difference

G+11 Cuts+10 Uncovered รวม **22 Input Records** มี Geometry Hash ตรงค่าที่ Export ไว้ทั้งหมด และ Persisted WKT Area ตรง Stored area_m2 ทุกแถว (Residual 0) WKT Full-precision และ WKB Roundtrip Hash ตรงทุกแถว

Roundtrip C/M ผ่าน WKT หรือ WKB แล้ว C.union(M) ยังผิดเหมือนเดิม จึงไม่พบว่า WKT Encoding/Decoding ปัจจุบันเป็นสาเหตุของพื้นที่เกิน การ Aggregate Soil Cuts เพื่อสร้าง C เพียงอย่างเดียวไม่เติมรู แต่การนำ C ที่ Aggregate แล้วไป Union M ทำให้เกิด Anomaly แสดงความไวต่อเส้นทาง/การจัดกลุ่ม Operations ใน Floating-point kernel นี้

สำหรับกรณีที่หยุด: `M.difference(G.difference(C))=0` และ `G.difference(C).difference(M)=0` ดังนั้น M ตรงกับ Directed Missing Geometry ตาม Operations ที่ตรวจ ไม่ใช่เศษพื้นที่ 14.2778 ไร่ที่หายไปแล้วควรเติม

## ผลสแกน Fragments และผลกระทบต่อตาราง Export

- Pure Fragments 1,504: Union Upper-bound Failure **1**, Review QC Failure **1**, Operation Exceptions **0**
- Geometry Hash/Stored Area mismatch: **0**
- Max abs(Soil Cuts Sum − C): 1.513399×10⁻¹¹ ไร่
- Max G−C: 1.169061×10⁻¹⁰ ไร่; Max C−G: 1.432980×10⁻¹⁰ ไร่
- Directed Missing กับ Persisted M ต่างกันทั้งสองทิศ: **0** ในทุก Fragment ที่สแกน
- ผลรวมพื้นที่จาก Persisted Soil Cuts เทียบทั้ง Pair Table และ Soil Composition ทุกหน่วย: Maximum Summary Residual **0 ไร่**

หลักฐานจึงชี้ว่าพื้นที่เกินเกิดตอน Review Union ไม่ใช่ใน Soil Area ที่ Export แต่การตรวจนี้ **ไม่ใช่การพิสูจน์ Raw Overlay ใหม่, ความถูกต้องตำแหน่งตามการสำรวจ หรือ Cross-engine Robustness** ตารางยัง Quarantined

## สิ่งที่พิสูจน์ได้ / Hypotheses / Evidence Gaps

**พิสูจน์ได้:** Operation-level Failure ทำให้รูเดิมถูกเติม; คงอยู่หลัง WKT/WKB Roundtrip; กลับ Operand Order ไม่ช่วย; One-pass Union ของชิ้นเดิมไม่เกิด Anomaly ใน Fragment นี้; Soil Composition จาก Persisted Cuts ไม่ได้สะท้อนพื้นที่เกินดังกล่าว

**Hypothesis:** Tiny, เกือบเส้นตรง Uncovered Pieces และตำแหน่งขอบที่ใกล้กันมากกระตุ้น Numerical/Noding/Polygonization Instability ใน GEOS Union เส้นทางนี้ ยังไม่ระบุบรรทัด/อัลกอริทึมภายใน GEOS ว่าเป็น Root Cause และยังไม่ยืนยันว่า GEOS เวอร์ชันอื่นแก้ได้

**Gaps:** ไม่ทดสอบ GEOS อีกเวอร์ชัน/Independent Kernel; ไม่มี Trace ภายใน GEOS; ไม่ทำ Construction จาก Raw ใหม่; One-pass ทางเลือกยังไม่ผ่าน Acceptance Matrix ครบ 1,504 Fragments; ไม่แก้ Failures หรือ Expected Values ของ Phase 10B Tests

## ทางแก้ที่เสนอ — ยังไม่ลงมือ

1. **แก้ Independent Review ให้ตรวจ Partition ด้วย Directed Differences + Containment/Disjointness/Area Invariants** โดยไม่พึ่งการ Re-union C+M ที่ทำให้ผิด พร้อม Cross-check One-pass Union ของชิ้นเดิมทุก Fragment และติดตามรูเดิมอย่างชัดเจน เก็บชิ้น Uncovered ทุกชิ้น ไม่ Drop/Snap เปลี่ยน Accepted Status ให้เกิดหลัง Final Review เท่านั้น ผลต่อ Area: ไม่แก้ Pair/Composition/Raw; Topology: เปลี่ยนวิธีตรวจไม่ใช่ Geometry; Reproducibility: Versioned Code/Checks ใหม่และ Golden Regression Fixture กรณีนี้ ต้องผ่าน Contract เดิมจึงพิจารณารุ่นใหม่ได้
2. **ทดสอบ Kernel/GEOS อีกเวอร์ชันในสภาพแวดล้อมแยกก่อนพิจารณาเปลี่ยน Dependency** ด้วย Fixture และ Persisted Partition ชุดเดิม ไม่ใช้ Buffer/Snap/Precision Reduction ผลต่อ Area/Topology: อาจมีผลต่างเชิงตัวเลขหรือ Construction จึงต้องตรวจ Area, Holes, Containment และ Hash Differences ไม่คาดเดาว่าหาย; Reproducibility: Pin Python/Shapely/GEOS และเก็บผล A/B เวอร์ชัน ห้าม Upgrade Production หรือเขียนทับ Dataset เดิม

ทั้งสองทางต้องขออนุมัติก่อน Fix ไม่มีการเปลี่ยน Tolerance หรือปรับ Test Expectations เพื่อทำให้กรณีผิดผ่าน

## ไฟล์, Tests และ Protected Hashes

ไฟล์ใหม่: `C:/project/tools/diagnose_tha_mai_geometry.py`, `C:/project/tests/test_tha_mai_geometry_diagnosis.py`, รายงานนี้ และ Diagnostic Artifacts ที่:

`C:/project/research_data/internal_research/tha_mai_spatial/phase10c_20261012_diagnosis_v1/`

Artifacts: minimal_inputs.json, operations.json, OPERATIONS.md, fragment_scan.json, protected_hashes.json, reproducibility.json, output_manifest.json พร้อม Seal ทุกไฟล์ Input Fixture เป็น Internal Geometry ห้ามเผยแพร่

**Seal Canonicalization ของ Phase 10C:** Sorted UTF-8 Compact JSON (`separators=(",",":")`) ตาม digest() ในสคริปต์ใหม่ ตรวจด้วยวิธีนี้ผ่าน Hash ทุกไฟล์ ไม่ใช้ verify_seal() รุ่น Phase 9C/9D ซึ่งใช้ JSON มี Spaces และจะได้ Payload Digest คนละค่า ความต่างนี้ไม่ใช่ Source/Artifact Hash เปลี่ยน; ควรเก็บ/ระบุ Algorithm ชัดเมื่อทำเครื่องมือ Seal กลางในงานภายหลัง โดยยังไม่แก้ของเดิม

Tests ใหม่ 5/5 ผ่าน: Synthetic Partition, Upper-bound Violation, Hole/Orientation, Empty Geometry และ Operation Error Recording; Minimal CLI Reproducer ผ่านและ Output ซ้ำตรงกัน ไม่รัน Repository-wide ซ้ำในงาน Diagnosis นี้ และ **ไม่อ้างว่า 3 Failures/Errors เดิมของ Phase 10B หายแล้ว**

Protected Files **1,169 ไฟล์คงเดิม** รวม Raw, Phase 9C/9D, Sealed Quarantined/Failed Artifacts, Exporter/Review/Tests เดิม และ Production Source/Model ไม่มีแก้ Dataset, API, Frontend, Raw Geometry หรือ Tests เดิม

Production SHA256: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

Phase 10C Manifest SHA256: `94a7cecff5a873c4653ec46a236d6498b01f3dc1fe0dcdcfd4674bcf00353ea9`

ใช้ Ponytail จำกัดเป็น Diagnostic Script กับ Tests ใหม่ ไม่รื้อ Exporter ไม่มี Training, Accepted Release หรือการเผยแพร่ข้อมูล **หยุดรออนุมัติก่อน Fix**
