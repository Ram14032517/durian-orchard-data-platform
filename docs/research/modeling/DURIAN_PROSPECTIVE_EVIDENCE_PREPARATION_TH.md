# Phase 8B — Prospective Forecast Evidence Preparation

12 ตุลาคม 2026 — Offline / Synthetic only; ไม่มี Training, Live API หรือ Forecast จริงปี 2027
อ่าน `DURIAN_FORECAST_READINESS_TH.md` และ `ridge_vpd_prediction_contract.json` ก่อนพัฒนา
ไม่พบ root AGENTS.md; ใช้ Ponytail เพิ่มส่วนแยกด้วย Python standard library ไม่แก้ Pipeline/Callers เดิม

## ขอบเขตและไฟล์ใหม่

- `tools/durian_model/prospective_evidence.py`: Offline Source Registry, As-of preflight, Append-only SQLite ledger และ Actual revisions
- `tools/durian_model/prospective_freeze_requests.json`: Candidate/Baseline requests สถานะ Pending ไม่มี Model ที่เลือก
- `tests/test_prospective_evidence.py`: ข้อมูลและไฟล์สังเคราะห์ใน TemporaryDirectory เท่านั้น
- รายงานนี้; Snapshot/Logs อยู่ `.build/rebaseline-backups/phase8b/` ไม่รวม Secret contents

ไม่มี CLI หรือทางออก Forecast จริง และไม่ Import Estimator, Network client, Production API หรือ Feature builder
`SyntheticLedger` บันทึก `simulation=true` ทุก Record; Forecast ใช้ Kind `simulated_forecast` ไม่ใช่ Forecast ที่ออกจริง
Prediction ใน Tests เป็นค่าคงที่สังเคราะห์ ไม่ได้คำนวณจากโมเดล ไม่มี Ledger จริง/Forecast outputs คงค้างหลัง Tests

## Ledger และ Provenance

ใช้ SQLite transactional INSERT; Unique Record ID; ทุก Record ผูก Previous hash และ SHA256 ของ Canonical payload
Triggers ปฏิเสธ UPDATE/DELETE; Duplicate ID ไม่เขียนทับ; `verify()` ตรวจลำดับ/Hash chain และรองรับ External head checkpoint
`verify_provenance()` ตรวจ Source/Evidence bytes และ Artifact/Input provenance ของ Forecast ที่บันทึกไว้อีกครั้ง
Hash chain ไม่ใช่ WORM storage: ผู้มีสิทธิ์แก้ Database/ลบทั้งไฟล์ยังทำลายประวัติได้ ต้องเก็บ Independent head checkpoint/Backup ภายนอกก่อนใช้งานจริง
Hash ไม่ Authenticate ความจริงของ Publication evidence; ผู้ตรวจต้องรับรองว่าเอกสารผูก Bytes/Version/เวลาที่ระบุจริง

| Record kind | เนื้อหา |
|---|---|
| source | OAE/POWER, Version, Publication/Retrieval times แยกกัน, Valid period, Status, Data path/SHA256, Evidence path/SHA256/URL และ Vintage binding, Revision parent |
| simulated_forecast | Forecast ID, จังหวัด/ปี, Issue, Model version, Freeze request, Config/Code/Model hashes, Input record IDs, Preflight, Prediction หน่วย กก./ไร่ |
| no_forecast_issued | Request/Input references เดิม พร้อมเหตุผล; Prediction เป็น null ไม่ใช่ศูนย์ |
| actual | Forecast reference, Source reference, Actual value, Recorded time, First-release/Revised และ Revision parent |

การเพิ่ม Source version สร้าง ID ใหม่; Revised source ไม่ทำให้ Source เดิมเปลี่ยนและไม่ถูกเลือกแทนโดยอัตโนมัติ
Actual ต้องตรงจังหวัด/ปี/ค่าผลผลิตใน Hashed JSON source extract; Valid period ต้องตรง Target year และเผยแพร่ก่อนเวลา Recorded
First-release กับ Revised แยก Record; Revised ต้องอ้าง Actual/Source เดิมและมี Publication time ใหม่ที่ช้ากว่า
ยังไม่มี Raw OAE→JSON extraction integration; หากทำภายหลังต้องผูก Raw bytes/Conversion code/Extract hashes เพิ่ม ห้ามอ้าง JSON ที่คนกรอกเองเป็นหลักฐานทางการ

## As-of fail-closed

Calendar ตรึงเฉพาะห้าจังหวัดเดิม, Target 2027, Lead 60 วัน:
จันทบุรี 31 ม.ค., ศรีสะเกษ 2 มี.ค., อุตรดิตถ์ 2 เม.ย., สุราษฎร์ธานี/ชุมพร 2 พ.ค. เวลา 00:00 +07:00
Shared fit cutoff = 31 ม.ค. 2027 เวลา 00:00 ไทย; Training/Selection labels และ Training features ใช้ Cutoff นี้
Lag/Weather/Climatology ของการออกพยากรณ์ใช้ Issue ของจังหวัดนั้น; ไม่เปลี่ยน Calendar ตาม Outcomes

Preflight ตรวจ:

- Request/Calendar/Province ต้องตรง; Issue ต้องตรงเวลา ไม่ย้อนหลังหรือออกช้าแล้วอ้างว่าเป็น Lead-60 เดิม
- Request ต้องเป็น Synthetic approval และมี Model/Config/Code artifact hashes ครบ; Pending request ไม่ผ่าน
- Required inputs ต้องครบ/ไม่มีส่วนเกิน และ Feature lineage ต้องอ้าง Dependency IDs ชุดเดียวกัน
- Roles รับเฉพาะ Training label, Selection label, Training feature, Lag yield, Weather, Climatology; Evaluation target ห้ามเป็น Input
- Source ต้อง `verified_available`; Missing Publication/Evidence, unverified, unavailable และ not_applicable สำหรับ External source ไม่ผ่าน
- Evidence metadata ต้องผูก Data hash/Version/Publication time ตรงกับ Source; Data/Evidence files ต้อง SHA ตรง
- Publication ≤ Retrieval ≤ Cutoff; มี Data ที่ยังไม่ได้ Capture ณ Cutoff ถือว่าไม่พร้อมสำหรับ Prospective issuance
- Valid end ของ Observed/Reanalysis/Climatology dependency ต้องไม่เกิน Cutoff; Version/Provider/Valid period ต้องตรง Freeze request
- Dates ต้องมี Timezone ชัดเจน ไม่เดาเวลาจาก Date-only, Filename, mtime หรือ Retrieval date

Missing/ผิดเงื่อนไขจะบันทึก `no_forecast_issued` พร้อมเหตุผลแรกที่ตรวจพบและเก็บ Request เดิม ไม่ Drop กรณีออกจาก Coverage
ทะเบียนเก็บ Source ที่ยัง unverified ได้เพื่อแสดงช่องว่าง แต่ไม่ยกระดับให้ Forecast ผ่าน
ไม่มี Historical vintage substitution, Future filling, Automatic source update หรือ Candidate selection
Preflight นี้ตรวจไฟล์และ Contract ของ Evidence ที่ได้รับ ไม่ตรวจความแท้เอกสารจากเครือข่าย และไม่รัน Feature builder เพื่อพิสูจน์ค่าที่คำนวณ
Feature lineage/Required roles ของ Candidate จริงยังต้องกรอกและตรวจจาก Builder จริงใน Freeze approval ไม่ถือว่า Synthetic fixture ที่ใช้ Lag ตัวเดียวเป็น ML Feature contract ครบชุด

## Freeze requests ที่ต้องอนุมัติแยก

Templates Candidate/Baseline ยัง `pending_approval`, `selected_model=null`, ไม่อนุญาต Training/Issuance และ `historical_pit_certified=false`
ก่อนใช้งานจริงต้องอนุมัติ Model identity/version/artifact, Config/Code hashes, Feature contract/Required vintages/Lineage, Training cutoff/Label evidence, Planned Issue calendar และ Rule freeze evidence
Baseline ต้องระบุ Last-year rule กับ OAE Vintage ของ Lag ที่มีจริง ไม่ใช้ Revised data อัตโนมัติ
ต้องอนุมัติ Truth policy ที่แยก First-release/Revised และการเก็บ Independent checkpoints/Backups
Production contract เดิมใช้ Observed weather ครบฤดู ไม่ยกมาเป็น Lead-60 Candidate อัตโนมัติ
งานนี้ยังไม่เลือก Candidate จาก Outer 2017–2025 และไม่มีการขอ/บันทึกอนุมัติใช้งานจริงใน Templates
การเชื่อม Live capture หรือเปิด Real issuance ต้องเป็นงานใหม่พร้อมการอนุมัติ; ไม่เพียงเปลี่ยน Flag `simulation`

## Verification

Tests ใหม่ครอบคลุม Forecast/No-Forecast, Duplicate/Immutable records, Hash chain/checkpoint/reopen, Source/Evidence tampering,
Version revisions, Missing evidence/status, Future data/retrieval/publication, Shared fit cutoff, Lineage completeness,
Artifact protection, First-release/Revised actuals, Wrong actual keys, Timezone/Calendar และ Real-issuance lock
Full repository Python discovery จากไฟล์ฉบับสุดท้ายผ่าน **295/295** (279 เดิม + 16 ใหม่), JavaScript **30/30** ไม่มี Failures/Skips
รอบ Full discovery แรกผ่าน 293/293 ก่อนเพิ่ม Tests อีกสองข้อ; รันทั้งชุดใหม่ 295/295 ไม่อ้างผลจากโค้ดฉบับเก่า
ระหว่างพัฒนาพบ New-test failure จาก SQLite transaction หลัง Trigger ปฏิเสธการแก้ Record; แก้เฉพาะโมดูลใหม่ให้ใช้ Autocommit กับ Explicit append transaction แล้วทดสอบซ้ำผ่าน ไม่แก้ Tests/Logic เดิม
หลัง Tests: Protected hashes **778/778**, Phase 7B Sealed artifacts **20/20**, Sealed input hashes **57/57** ตรง
Production SHA256 คงเดิม: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`
Git Status เดิมไม่หายหรือเปลี่ยน เพิ่มเพียงรายงาน/Tests ใหม่; สองไฟล์ใน `tools/durian_model/` อยู่ใต้โฟลเดอร์ Untracked เดิมจึงไม่แสดงเป็นรายการใหม่แยกใน Short status
ตรวจ Hashes ของ Protected files โดยตรง ไม่ใช้ Git Status อย่างเดียวเพื่อยืนยัน Production/Code เดิม
Commands: Python `-m unittest discover -s tests -p 'test_*.py'`; Node `--test` ทั้งหกไฟล์ `tests/test_*.js`
Logs: `.build/rebaseline-backups/phase8b/python_final.log`, `js_tests.log`; Snapshot เดิม `before_task.json`; Verification summary `postflight.json`

ข้อจำกัด: SQLite ป้องกันการแก้ผ่าน Application/SQL triggers ไม่ใช่การป้องกันผู้ดูแลเครื่อง; SHA ไม่ยืนยันวันเผยแพร่หรือความแท้หลักฐาน
Historical PIT/Forecast accuracy ยังไม่รับรอง ไม่มี Candidate จริง/Source registry ที่ยืนยัน OAE/POWER จริงในงานนี้
หยุดรอคำสั่ง ไม่ออก Forecast ไม่ Train ไม่เชื่อม API
