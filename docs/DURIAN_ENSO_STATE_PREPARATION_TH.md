# Phase 5A — ENSO State Ablation Preparation

วันที่: 11 ตุลาคม 2026 — Exploratory preparation เท่านั้น; โมเดลที่ฝึก = 0

## สิ่งที่เพิ่ม

- `tools/durian_model/experiment_enso_state.py`: โมดูลทดลองแยก ใช้ตัวสร้างข้อมูล/Availability Guard/Feature Lineage เดิม ไม่แก้ callers หรือไฟล์เดิม เปิด ENSO ผ่าน `augment(..., enabled=True)`; เมื่อปิดคืน prepared object เดิมและไม่อ่าน ENSO archive
- `tests/test_enso_state_preparation.py`: Tests ใหม่ 10 ข้อ ไม่ Fit estimator
- รายงานนี้และ preparation artifacts ใน run ใหม่ ไม่เขียนทับ Phase 2/3 หรือ Production

โมดูลมีเฉพาะ `--prepare` ไม่มี `--train` หรือคำสั่ง Fit จึงยังรันการทดลองจริงไม่ได้จนกว่าจะได้รับอนุมัติขั้น Training และเชื่อม execution loop ตามแผนด้านล่าง

## Protocol ที่คงเดิม

5 จังหวัด: จันทบุรี, ศรีสะเกษ, อุตรดิตถ์, สุราษฎร์ธานี, ชุมพร; Fixed-calendar เดิม; Lead 60 วัน; Outer 2017–2025; Inner 3 ปีก่อน Outer; Shared Fit Cutoff เดิม

| แขน | Inputs |
|---|---|
| Weather | จังหวัด + ปี + ผลผลิตปีก่อน + Weather 7 Features รวม VPD เดิม |
| Weather + ENSO State | Inputs เดิม + fixed one-hot El Niño / Neutral / La Niña |

one-hot columns: `enso_el_nino`, `enso_neutral`, `enso_la_nina`; ไม่มีการสร้าง ordinal severity และไม่มี Target-dependent encoding

CatBoost grid depth 2/3, l2_leaf_reg 10, learning_rate .03; iterations 400, RMSE, Ordered boosting, Seed 42, thread_count 1, allow_writing_files=False คงเดิม เลือก depth จาก Inner MAE แยกแขนเท่านั้น; depth 2 ชนะ exact tie ห้ามใช้ Outer Targets เลือกโมเดลหรือ Features

Protocol SHA256: `abffd1925cbdc8bdbd0d96e1c8a975d2f42ca0c19900a6820b3b810020f27b70`

## หลักฐานและ As-of Join

อ่านรายงาน Phase 4B และ `documents.csv`, `availability.csv`, `fold_availability.csv` ใน `phase4b_20261011_noaa_reviewed` ตรวจ edition coverage 80 ฉบับ, จังหวัด–ปี 80 keys และ consumption keys ครบ 1,890 records ไม่ลดตัวอย่างเมื่อขาดข้อมูล

ตรวจ SHA256 ของสำเนาดิบ แล้วเรียก parser เดิมกับ bytes จริงอีกครั้ง เทียบ publication date, issuance evidence, observed state และ observed-state evidence กับ metadata ตรวจว่าเป็นลิงก์ NOAA ที่ archive audit รองรับและ `revised_oni_used=False` ไม่ใช้ ONI ปัจจุบันหรือ Forecast Probability

ในทุก Outer/Inner Fold:

1. Replay weather/lag/training label/selection label availability และ consumed lineage เดิมผ่าน `wa.audit`
2. คำนวณ Issue Date จากกฎเดิม ไม่อ่าน Target เพื่อกำหนดวัน
3. Training inputs ใช้ cutoff ของ fold; forecast inputs ใช้ issue ของจังหวัดนั้น; ENSO effective cutoff = min(row issue, role cutoff)
4. เลือก bulletin ล่าสุดที่ publication day **ก่อน** cutoff อย่างเคร่งครัด; date-only ไม่รับฉบับวันเดียวกัน ไม่อ่านฉบับอนาคตมาชดเชย state ที่หาย; ไม่ fallback ไป bulletin เก่าที่มี state หากฉบับล่าสุดไม่มี state
5. ตรวจ max age 45 วันตาม audit policy เดิม เทียบการเลือกจริงกับ availability และ fold table รวม fit/selection cutoff
6. บันทึก source URL/SHA256/snapshot, evidence, state, actual encoded values และ cutoff ใน lineage แล้วแนบค่าเหล่านั้นลง predictor frame ของ fold จริง

Forecast inputs ของจังหวัดที่ issue หลัง shared fit cutoff ไม่ถูกใช้เป็น Training inputs ของ fold เดียวกัน Labels และ evaluation references ถูกคงไว้แยกจาก predictor frames ไม่มี probability/ONI/Target ใน ENSO Feature whitelist

## Preparation run ที่ผ่านการตรวจ

`research_data/five_province_history/training/enso_state_preparation_exploratory/20261011T131137524518Z/`

- `config.json`: locked protocol, grid/seed, base data/manifest/schedule/code hashes, archive inventory hashes, dependencies และ git context
- `enso_lineage.json`: 1,890 actual consumption records ผูกเอกสารกับค่า one-hot จริง
- `base_lineage.json`, `base_availability.json`, `manifest.json`: dependency checks เดิม
- `folds.json`: 36 fold contexts และ cutoffs
- 72 predictor CSVs: training/forecast frames ของแต่ละ context; Weather arm ต้องใช้ `project` เพื่อตัด ENSO ออก ไม่ส่ง raw expanded frame เข้า estimator
- `status.json`: training_performed=false, pit_certified=false
- `artifact_hashes.json`: inventory ของ artifacts 79 ไฟล์ ไม่รวมตัว inventory เอง

ตรวจทุก artifact hash แล้วตรง; ENSO records แบ่งเป็น El Niño 553 / La Niña 655 / Neutral 682 เป็นจำนวนการใช้งานซ้ำใน folds **ไม่ใช่ตัวอย่างอิสระ 1,890 ตัวอย่าง**

## ความเท่าเดิมเมื่อปิด ENSO

- ไม่แก้ Weather Pipeline, design, fitter, candidates หรือ callers เดิม
- Off switch คืน object เดิม; projection ของแขน Weather เรียก `wa.project` เดิม
- Tests ตรวจ DataFrame และ design matrix แบบ exact equality ในทุก fold พร้อม prediction-boundary stub (ไม่ฝึก estimator)
- ตรวจ CSV Inputs จริงครบ 1,890 consumed rows หลังตัด ENSO: ตรงกับ Phase 2 saved predictor matrix แบบ exact equality และผ่าน Phase 2 consistency preflight
- Hash ของ Predictions/Artifacts เดิมไม่เปลี่ยน ดังนั้นไม่มีการสร้างหรือเปลี่ยน MAE 204.85 ในรอบนี้

**ไม่ได้ฝึก CatBoost ซ้ำเพื่อยืนยัน numerical predictions ใหม่** เพราะผู้ใช้ห้าม Training: หลักประกันในรอบนี้คือเส้นทางเดิมไม่ถูกแก้ + Inputs/design เดิมตรงกัน + saved prediction artifacts เดิม hash ตรง เมื่ออนุมัติ Training ต้องเพิ่ม regression gate ตรวจ Weather-arm predictions เทียบ Phase 3 ก่อนตีความผล ENSO

## Tests และ Regression

ก่อนแก้: Python 232/232, JS 30/30 ผ่าน (232 รวม ENSO archive tests 7 ข้อจาก Phase 4B)

หลังแก้: Python 242/242, JS 30/30 ผ่าน; Tests ใหม่ 10 ข้อครอบคลุม cutoff/future/same-day rejection, evidence/value lineage, disabled identity/design, target poisoning, cache arm/grid/archive separation, missing archive/dependency coverage, metadata/bytes tampering, no future fill, artifact collision/path/hash checks, frozen protocol

Cache key แยกตาม protocol, archive hashes, arm, features, parameters, fit cutoff, provincial issue dates และ actual training/forecast consumption; ไม่มีการโหลด prediction cache เก่ามาแทนการประเมินแขนใหม่ Tests ตรวจ key reproducibility แบบ deterministic

พบข้อผิดพลาดใน implementation ใหม่ระหว่างตรวจ artifact: inventory รวม Hash ของไฟล์ inventory เอง แก้ให้ตัดตัวเองออกและเพิ่ม Test ตรวจ inventory ครบ รอบแรก `20261011T130913116545Z` เก็บไว้เป็น diagnostic เท่านั้น **ห้ามใช้เป็นรอบอ้างอิง** ไม่แก้หรือเขียนทับรอบแรก แล้วสร้างรอบอ้างอิงใหม่ข้างต้น ไม่มีคะแนนโมเดลเกี่ยวข้อง

## Protected Files

ตรวจ hashes ก่อน/หลัง **645 ไฟล์เดิมตรงทั้งหมด** รวม Production/API/Frontend, Experimental Pipeline เดิม, ผล Phase 2/3, archive raw sources/tables และเอกสารเดิม การเปลี่ยนแปลงใน dirty repository ที่มีอยู่ก่อนถูกเก็บไว้ ไม่ stage/reset/delete

Production model SHA256:

`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

## ข้อจำกัดและขั้นถัดไป — รออนุมัติ

- Publication evidence ยืนยันวันออก bulletin ไม่ยืนยันว่า archived content ไม่เคยแก้ย้อนหลัง สำเนาอ่านในปี 2026; content_authentication ยัง unverified ทุก record
- ข้อจำกัด historical OAE/POWER vintages และ fixed calendar ที่สร้างในปี 2026 คงเดิม ทั้งงานยัง Exploratory ไม่ PIT Certified
- Audit parser ถูก replay ไม่ใช่การรับรอง state extraction อย่างอิสระจากผู้เชี่ยวชาญ; ไม่ตีความ ENSO state ว่าอธิบายผลผลิตเชิงสาเหตุหรือบอกอากาศสวนเฉพาะจุด
- 45 Outer keys เคยใช้พัฒนาแล้ว ไม่ใช่ untouched final holdout
- หลังอนุมัติ ให้เชื่อมสองแขนเข้าลูป Inner-only selection เดิม ตรวจ lineage/config/source hashes ก่อน fit และตรวจ Weather arm เทียบ saved Phase 3 predictions หากผิดให้หยุด จากนั้นรายงาน MAE/RMSE/Bias/paired errors/ชนะ–เสมอ–แพ้/รายปี–จังหวัด/parameter choices โดยไม่เปลี่ยน Feature/Grid/Calendar หลังเห็น Outer scores

หยุดก่อน Training ไม่มีการทดลอง ENSO Ablation หรือ Province Expansion ในงานนี้
