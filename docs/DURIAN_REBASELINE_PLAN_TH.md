# Phase 1 — Experimental Rebaseline Pipeline Preparation

วันที่ 10 ตุลาคม 2026 (Asia/Bangkok) งานนี้พัฒนาและตรวจ preparation เท่านั้น
ไม่มีการฝึก estimator, ไม่มีผล MAE ใหม่, ไม่มี A/B/C/D และไม่เปลี่ยน Production/Frontend/API

## ขอบเขตและ Snapshot

ตรวจ Git Status/Diff ก่อนแก้ พบไฟล์ experimental เดิมเป็น untracked จึงตรวจเนื้อหาโดยตรง
ไม่ reset, checkout, delete หรือรวมการเปลี่ยนแปลงเดิมเข้ากับ commit
สำรองแบบ allowlist 8 ไฟล์ก่อนแก้ใน:
`C:/project/.build/rebaseline-backups/25691010T124343592Z/`
ชื่อโฟลเดอร์ปี 2569 เกิดจาก Windows culture; เป็นสำเนาที่สร้างวันที่ 10 ตุลาคม 2026
สำเนาครอบคลุม experiment_issue_date.py, availability_guard.py, availability_manifest.json,
README_TH.md ของโมเดล, tests เดิมทั้งสามไฟล์ และรายงาน Availability Guard
ตรวจข้อความและรูปแบบ credential ก่อนสำรอง; ไม่มี .env, key store, firmware secrets หรือทั้ง repository
ตรวจ SHA256 สำเนาทั้ง 8 ตรงกับต้นฉบับก่อนแก้ ไม่ใช่ snapshot ของทุกไฟล์ใน repo
เก็บ baseline hashes ของ 113 ไฟล์ Production/API/Frontend/helper/artifacts เพื่อเปรียบเทียบหลังงาน

## Protocol ที่ตรึง

- จังหวัด 22 จันทบุรี, 33 ศรีสะเกษ, 53 อุตรดิตถ์, 84 สุราษฎร์ธานี, 86 ชุมพร
- Anchor ตามลำดับ 04-01, 05-01, 06-01, 07-01, 07-01; ไม่จูนฤดูกาลจากผล test
- Lead 60 วัน, อายุผล proxy 140 วัน, main-season proxy 3 เดือน; ไม่ยืนยันว่าเป็นหมอนทองล้วน
- Panel 2010–2025 ต้องครบ 80 จังหวัด–ปี พร้อม lag จากปีก่อน (รวม source 2009)
- Outer 2017–2025; Inner 3 ปีก่อนแต่ละ Outer; train ใช้เฉพาะปีน้อยกว่าปีที่จะ predict
- 9 Outer + 27 Inner contexts; shared fit cutoff เวลา 00:00 +07:00 ของ issue แรกสุดใน 5 จังหวัด
- Training inputs และ Training labels ตรวจที่ cutoff ของ fold นั้น
- Forecast inputs ตรวจที่ issue ของจังหวัดนั้น; Inner labels ที่ใช้ selection ตรวจอีกครั้ง ณ Outer selection cutoff
- Evaluation reference ทราบภายหลังได้ แต่ไม่ส่งเข้า builder, predictors หรือ Training ของ fold เดียวกัน

โมเดลที่เตรียม configuration: Last-year ไม่จูน; Ridge alpha 1/10/100;
CatBoost depth 2/3, l2_leaf_reg 10, learning_rate .03, 400 iterations, Ordered boosting, seed 42
Ridge/CatBoost ใช้ 8 Features เดียวกัน พร้อม design จังหวัดและปีจาก helper เดิม
Last-year ใช้เฉพาะ lag; ไม่ใช้ Outer targets เลือก family, parameter หรือ early stopping
การฝึกและเลือกพารามิเตอร์ยังไม่ implement ใน runner preparation นี้
เมื่ออนุมัติ Training ต้องเพิ่มการเลือกภายใน family ด้วย Inner MAE เท่านั้น และ tie-break ตาม candidate order
2017–2025 เคยตรวจแล้ว ไม่ใช่ independent holdout ใหม่ และ 204.85 ไม่ใช่ Baseline ของปฏิทินใหม่นี้
Inner แรกปี 2014 มี training 20 แถว; ข้อจำกัดข้อมูลเล็กยังคงอยู่

## Lineage จากข้อมูลที่ใช้จริง

`features()` เดิมคง signature และ return 4 items พร้อม coverage schema เดิม
เพิ่ม `features_with_lineage()` ซึ่งใช้ private builder เดียวกัน ไม่คำนวณสูตรใหม่อีกชุด
จับ provenance ตรง array ที่ส่งเข้า stage_feature: observed dates/cells, climatology cells/calendar keys,
วันที่และ SHA256 ค่าที่อ่านจริง, SHA256 raw components, reducer, cohort/window size และค่าฟีเจอร์ที่ออกจริง
VPD แสดง raw columns T2M_MIN/T2M_MAX/RH2M แยกจากค่า derived VPD; normal Feb29 ใช้ Feb28/Mar01 เดิม
Normal dates ติดตามเฉพาะ cells ที่มีส่วนในค่าปกติที่นำมาใช้ ไม่ใช่ max date ของทั้ง weather file
Lag อ่าน annual source จังหวัดเดียวกันปี y-1 โดยตรง บันทึก source key/value digest และตรวจเทียบ panel lag
Feature builder รับเฉพาะ keys ไม่รับ Target, Bearing area หรือ Production

Observed dates ต้องไม่เกิน row issue-7 และ use cutoff; climatology ต้องอยู่ y-10 ถึง y-1
และไม่เกิน cutoff เช่นเดียวกัน Version/role/records หายหรือ feature/date/จังหวัด/ปีไม่ครบต้องหยุด
ไม่มีการลด sample, zero fill หรือ fallback โมเดลเมื่อติดตั้ง dependency ไม่ครบ
Normal coverage ยังคงกฎเดิมอย่างน้อย 8 observations/calendar day จาก 10 ปีก่อน
วันที่เผยแพร่ที่ไม่ทราบไม่ถูกเดาและไม่ใช้วันที่ download แทน
Availability Guard ยังคงยอมให้ Revised/unverified ใน Exploratory พร้อม warnings ไม่เปลี่ยนเป็น verified

## Configuration และ Artifact isolation

Runner ไม่มี --train; ค่าเริ่มต้นแสดง help ส่วน --prepare ทำ input/fold audit เท่านั้น
Artifacts อยู่ `training/rebaseline_exploratory/<run_id>/` สร้างแบบ exclusive
ตรวจ root/run id, path traversal/symlink และ collision ก่อนเขียน ไม่แตะ issue_date_* หรือ ridge_vpd_*
root ทางเลือกอนุญาตเฉพาะ temporary test roots และห้ามตั้งเป็น Production training root
เก็บ config, manifest snapshot, code/data/manifest/schedule hashes, seed, package versions, Python version,
Git HEAD/dirty status, fold cutoffs/membership counts/label digests, predictors, feature lineage,
availability warnings และ artifact hashes; ตรวจ input/code/manifest เปลี่ยนระหว่าง preparation แล้วหยุด
Hash ระบุเนื้อหาแต่ไม่แทนการเก็บ official historical vintage หรือ Git commit ของ untracked source
เมื่อรันจริงในอนาคตต้องรักษา code/data ที่ตรง hashes เพื่อ reproduce

เตรียมตัวสรุปผลจาก predictions (ยังไม่ใช้ผลจริง) บังคับ 135 predictions: 3 โมเดล × 45 keys เดียวกัน
ตรวจ evaluation references ตรงกัน มี MAE/RMSE/Bias/Median AE/n รายรวม/ปี/จังหวัด
มี paired error, wins/ties/losses รายแถว จำนวนปี/จังหวัดที่ชนะด้วย aggregate MAE และ worst signed errors
สาเหตุเชิงพื้นที่/ชีววิทยายังต้องมีหลักฐาน ไม่อนุมานจาก residual อย่างเดียว

## การตรวจในงานนี้

Tests เดิม 23 ข้อ และ Rebaseline ใหม่ 18 ข้อ ผ่าน รวม 41 ข้อ (ไม่มี estimator fit)
ตรวจ preparation กับข้อมูลจริงใน memory: 36 contexts, 80 predictor rows, 640 lineage records,
45,531 availability checks; ปิด fit_predict ด้วย mock ที่ raise หากถูกเรียก
ไม่เขียน preparation artifacts ลง production/experimental output ระหว่าง diagnostic นี้
Artifact tests เขียนข้อมูลสังเคราะห์เฉพาะ temporary directory แล้ว cleanup โดย test fixture

Regression ที่ตรวจ: legacy return schema/value, future-weather poisoning, actual rain reconstruction,
source hashes, climatology dates, incomplete data/lineage/records, lag source, shared cutoffs ทุก context,
การแก้ Outer target ปี 2017 และ 2025 ไม่เปลี่ยน predictors/train labels ของ fold ปีนั้น,
artifact collision/traversal และ report key completeness
Test แรกใช้ RH=999 ในข้อมูล future และถูก VPD input validation ปฏิเสธอย่างถูกต้อง
ปรับ fixture ให้เป็นอากาศที่ valid แต่ต่างจากเดิมมาก แล้ว future invariance test ผ่าน
ไม่ได้ผ่อน validation เพื่อให้ผ่าน

## Production และขอบเขตความเชื่อถือ

Production model SHA256 ก่อนและหลัง:
`B4B9E0985E6BA5E6EE371D8988CAD5E65DEE031B345EB0CF13A8695F91658680`
ตรวจ baseline hashes ครบ 113 ไฟล์หลังงาน: ไม่พบไฟล์เปลี่ยนในชุดที่ป้องกัน
ตรวจ AST signatures ของ functions เดิมใน experiment_issue_date.py เทียบ Snapshot: ตรงทั้งหมด
การตรวจ tests/preparation ยืนยัน implementation boundaries ไม่ยืนยัน historical PIT
OAE/POWER exact publication vintages ยัง unverified; Fixed-calendar สร้างปี 2026 ไม่ใช่กฎที่พิสูจน์ว่าใช้ใน 2017
POWER revised meteorology/reanalysis ไม่ใช่ archived operational forecast; future features ใช้ climatology
lag 7 วันเป็นสมมติฐาน latency ไม่ใช่ publication evidence
หนึ่ง weather reference point/จังหวัด และผลผลิตทุกพันธุ์รวมทั้งนอกฤดู ยังไม่ใช่ orchard-level Monthong forecast
ยังไม่ตรวจ Tests ทั้ง repository หรือ retrain/เปลี่ยน MAE; หยุดรออนุมัติ Training แยกต่างหาก
