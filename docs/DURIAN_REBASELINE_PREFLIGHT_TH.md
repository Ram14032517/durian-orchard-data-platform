# Phase 2 — Exploratory Rebaseline: Preflight หยุดก่อน Training

ตรวจวันที่ 10 ตุลาคม 2026 (Asia/Bangkok)
สถานะ: ยังไม่เริ่ม Rebaseline Training เนื่องจาก Repository test suite ไม่ผ่านทั้งหมด
ไม่ได้เปลี่ยน Features, Search Space, Calendar, Validation, Production, API หรือ Frontend
งานนี้เพิ่มเฉพาะรายงานฉบับนี้; ไม่แก้ test เพื่อให้ผ่านโดยไม่ได้รับอนุมัติ

## ผล Tests

| ชุด | ผ่าน | ไม่ผ่าน | เกี่ยวข้องกับ Rebaseline |
|---|---:|---:|---|
| Python unittest ทั้ง repository | 208 | 0 | รวม 41 tests ของ Phase 1 ครบ |
| JavaScript node --test ทั้ง repository | 29 | 1 | ข้อที่ไม่ผ่านอยู่ใน orchard physiology ไม่ใช่ ML pipeline |
| JavaScript physiology รันยืนยันเฉพาะไฟล์ | 3 | 1 | เป็นข้อเดิม ไม่ใช่ failure ใหม่เพิ่มอีกข้อ |

Python ใช้ `.build/national-analysis-venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -p 'test_*.py' -v`
JavaScript ใช้ `node --test tests/*.js` และยืนยันด้วย `node --test tests/test_orchard_physiology.js`
Python suite มีการ fit กับ fixtures ตาม tests เดิม แต่ไม่ได้เรียก Rebaseline training experiment

Failure: `tests/test_orchard_physiology.js:11` ใน
`dry scenario crosses RAW and reduces ET; mass balance and bounds`
assert.equal(result.taw_mm, 200) ได้ค่าจริง 199.99999999999997
สูตรที่อ่านใน tools/orchard_physiology.js คือ 1000 * (fc-wp) * root เมื่อ fc=.3, wp=.1, root=1
ความต่างประมาณ 2.84e-14 สอดคล้องกับ floating-point representation และ assertion แบบ exact equality
ไฟล์ test และ physiology ไม่ถูกแก้ในงานนี้ และไม่อยู่ใน dependency ของ Rebaseline
ไม่ยืนยันว่าข้อนี้เคยผ่านในอดีต เพราะ Phase 1 ไม่ได้รันทั้ง repository
แม้ไม่ใช่ failure ของ ML ก็ไม่ถือว่าเงื่อนไข "ผ่านทั้งหมด" สำเร็จ และไม่ข้ามเอง

## การตรวจ ML ที่ผ่าน

ตรวจ prepare() กับข้อมูลจริงใน memory ปิด fit_predict ด้วย mock ที่ raise หากถูกเรียก:
36 Outer/Inner contexts, 80 predictor rows, 640 feature lineage records, 45,531 availability checks
ตรวจ cutoff ของ Observed weather และ Climatology จากวันที่ใช้จริง, Lag จาก source ปีก่อน,
Training labels ณ shared fit cutoff ของแต่ละ fold และ Inner Selection labels ณ Outer selection cutoff
ผ่านใน Exploratory policy เท่านั้น: revised version/publication vintage ที่ยังพิสูจน์ไม่ได้คง warnings/unverified
ไม่มีข้อมูลอากาศที่ใช้จริงเกิน cutoff ตามตัวตรวจ และไม่มี Outer target ส่งเข้า feature builder/training ของ fold เดียวกัน
ไม่ใช่ PIT certification หรือหลักฐานว่าข้อมูลย้อนหลังถูกเผยแพร่ทันจริง

Input SHA256:
- production_annual.csv: c5eed63bddcb777afcbf4bb04e9f25cccdbf08d758636136a96730c884655b73
- harvest_monthly.csv: a1a04a1bcd4e37d1640a76a3fb733221563fcb5b00a43f6ce2046760bff7f739
- weather_daily.csv: 28dfcab00a24086735a7a8b596a19c52334a5025a7c3abb0297ff2a663d21054
- availability_manifest.json: 4d6e3b77d0f2561a5ce3dbb14ca322a21a03e7e4005d0153314c80b5cbbde827

Dependencies ที่ตรวจพบ: numpy 2.3.5, pandas 3.0.1, scikit-learn 1.9.1, catboost 1.2.10
check_snapshot() และ version guard ผ่าน ไม่พบ missing dependency ของ ML
candidate run_id `20261010T130043888162Z` ตรวจว่า output directory ยังไม่มีอยู่
ไม่ได้สร้าง directory นี้ ไม่ใช่การจอง directory และหากอนุมัติใหม่จะเลือก run_id ใหม่

## ผลโมเดล

| โมเดล | MAE | RMSE | Bias | สถานะ |
|---|---|---|---|---|
| Last-year | — | — | — | ยังไม่รัน Rebaseline |
| Ridge | — | — | — | ยังไม่รัน Rebaseline |
| CatBoost | — | — | — | ยังไม่รัน Rebaseline |

จึงยังไม่มี paired errors, wins/losses หรือความเสถียร hyperparameter selection ของ Protocol นี้
ไม่ใช้ 204.85 จาก Protocol เดิมเติมในตาราง และไม่มี Weather Ablation/Province Expansion

## Production และ Git

Repository ยังมี modified/deleted/untracked จากงานเดิม; ตรวจโดยไม่ reset/checkout/commit
ก่อนและหลัง preflight เปรียบเทียบ hashes 116 ไฟล์ที่ป้องกัน: ไม่พบเปลี่ยน
Production model SHA256 คงเดิม:
`B4B9E0985E6BA5E6EE371D8988CAD5E65DEE031B345EB0CF13A8695F91658680`
เพิ่มรายงานนี้เท่านั้น ไม่มี MAE artifacts ใหม่ ไม่มีการแก้ Production model/pipeline/API/Frontend

## ต้องการคำสั่งก่อนดำเนินการ

ขอให้ผู้ใช้เลือกว่าจะอนุญาตให้ถือ failure นี้เป็น unrelated pre-existing test failure ที่ไม่บล็อก Training
โดยคงไฟล์เดิมและบันทึกข้อจำกัด หรืออนุมัติให้แก้ floating-point assertion ใน test แยกก่อน
ไม่เสนอให้ปัดค่าฟังก์ชัน Production เพื่อเอาใจ test และไม่แก้ไฟล์นอกขอบเขตเอง
จนกว่าจะมีคำสั่งเพิ่มเติม ให้หยุดก่อน implement/run Rebaseline Training

## อัปเดตหลังได้รับอนุมัติแก้ Assertion และเริ่ม Phase 2

ผู้ใช้อนุมัติแก้เฉพาะ floating-point assertions และให้เริ่ม Training ได้เมื่อ tests ผ่านครบ
ตรวจสูตร TAW=1000*(fc-wp)*root และ RAW=p*TAW จาก source ไม่พบสูตรผิดสำหรับ fixture นี้
0.3-0.1 ใน binary64 ได้ 0.19999999999999998; TAW ต่างจาก 200 ประมาณ 2.84e-14 มม.
RAW ต่างจาก 100 ประมาณ 1.42e-14 มม.; Ks วันที่ 21 ได้ 0.9999999999999999
วันแรกใช้น้ำ 5 มม., วันที่ 22 Ks≈0.95 และ mass balance error=0 ตาม fixture

แก้เฉพาะ assert ของ TAW, RAW และ Ks ขอบเขตวันที่ 21 ใน test เดิมเป็น approximate equality:
abs(actual-expected) <= 16*Number.EPSILON*max(1,abs(expected))
Tolerance รองรับ rounding ไม่กี่ ulps จาก subtraction/multiplication/division chain
TAW tolerance≈7.11e-13 มม., RAW≈3.55e-13 มม., Ks≈3.55e-15
ไม่ใช้ tolerance ระดับความไม่แน่นอนทางเกษตร และไม่ปัด/แก้ค่าที่คืนจาก Business Logic
ยังคง assertions เรื่องลด ET, bounds และ mass balance เดิม

หลังแก้ assertion: JavaScript 30/30 และ Python เดิม 208/208 ผ่าน
ตรวจ diff เทียบสำเนาก่อนแก้; tools/orchard_physiology.js และ Production ไม่ถูกแก้
สำเนาอยู่ .build/rebaseline-backups/phase2-assertion/ เฉพาะ test, experimental runner และรายงานนี้

เพิ่ม Training orchestration เฉพาะ tools/durian_model/experiment_rebaseline.py
ไม่เปลี่ยน candidate grids, features, seeds, calendar หรือ validation ที่ล็อกไว้
คง preparation/default behavior และให้ --train เป็น explicit opt-in สำหรับ Exploratory เท่านั้น
เพิ่ม mocked training tests ใน tests/test_rebaseline.py: selection ภายใน family, poisoning Outer targets,
missing contexts/labels, predictor boundary และ protocol mismatch ก่อน fit
เลือกพารามิเตอร์จาก Inner 3 ปี และ freeze ทุก family choice/outer prediction ก่อนอ่าน Outer labels
Cache ใช้เฉพาะ fit ที่ train inputs/labels และ forecast inputs มี hash ตรงกัน ไม่รวม evaluation targets
เก็บ tuning, choices, fit audit และผล 135 predictions ใน run_id ใหม่แบบ exclusive
config.json เป็น pre-fit snapshot; run_status.json เป็นสถานะจบงานและระบุ training_performed จริง
ตัว runner ตรวจ hashes ของ code/data/manifest/Production ก่อน finalize outputs

ผลการ Training และรายงานสรุปจะเก็บในโฟลเดอร์ run ใหม่ ไม่เติม 204.85 จาก protocol เดิม
ไม่ใช่ PIT Certified และไม่เริ่ม Weather Ablation หรือ Province Expansion

Pre-training gate หลังเพิ่ม orchestration: Python 211/211 ผ่าน (เดิม 208 + mocked training tests ใหม่ 3)
และ JavaScript 30/30 ผ่าน ตรวจ Git Diff/whitespace และ protected hashes 116 ไฟล์ ไม่พบเปลี่ยน
Production SHA256 ตรงค่าที่บันทึกไว้; Business Logic orchard_physiology.js SHA256 คงเดิม
`7AD688FDD85D75FDD54C6D6EED594BEF7C8A9C655F2C94372BA83F2942C0CA99`
คำสั่งเริ่มเมื่อผ่าน gate: `.build/national-analysis-venv/Scripts/python.exe -X utf8 tools/durian_model/experiment_rebaseline.py --train`

## จบ Phase 2 และตรวจหลัง Training

รันใหม่แบบ exclusive: `20261010T131023246729Z` เสร็จ 2026-10-10 13:10:38 UTC
ได้ 45 จังหวัด–ปีต่อโมเดล รวม 135 predictions โดยไม่ตัดตัวอย่าง
Last-year MAE 215.51 / RMSE 269.55; Ridge MAE 212.20 / RMSE 258.03;
CatBoost MAE 204.85 / RMSE 266.47 กก./ไร่ ทั้งหมดคำนวณใหม่ในรอบนี้
CatBoost ชนะ Last-year 27/45 กรณี, 6/9 ปี, 3/5 จังหวัด ไม่ชนะสม่ำเสมอทุกพื้นที่
ยังไม่ปรับ Production และไม่เลือก/เปลี่ยน grid หรือ features หลังเห็น Outer scores

ตรวจ completed_artifact_hashes.json 18 รายการ ตรงทั้งหมด
ตรวจ protected hashes 116 ไฟล์หลัง Training ไม่เปลี่ยน
รัน tests หลังจบอีกครั้ง: JavaScript 30/30 และ Python 211/211 ผ่าน (208 เดิม + 3 ใหม่)
Git diff --check ผ่าน มีเพียงคำเตือน LF/CRLF; changes/untracked เดิมยังคงไว้
Production SHA256:
`B4B9E0985E6BA5E6EE371D8988CAD5E65DEE031B345EB0CF13A8695F91658680`

รายงานคะแนนรายปี/จังหวัด, paired errors, hyperparameter selection และข้อจำกัด:
[DURIAN_REBASELINE_RESULT_TH.md](DURIAN_REBASELINE_RESULT_TH.md)
ผลนี้ Exploratory ไม่รับรอง Historical PIT; ไม่ทำ Weather Ablation/Province Expansion
หยุดรอคำสั่งก่อนเริ่มงานทดลองถัดไป
