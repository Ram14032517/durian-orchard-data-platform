# Phase 7B — Level vs YoY Delta Target

วันที่ 12 ตุลาคม 2026 (ไทย); Run `phase7b_20261011T170140373940Z`
Exploratory เท่านั้น ไม่ใช่ Historical PIT Certified ไม่มีการเปลี่ยน Production/API/Frontend

## ข้อสรุปและการหยุด

**Inner Gate ไม่ผ่าน หยุดพัฒนา Delta หลังรอบนี้ ไม่จูน ไม่รันซ้ำ และไม่ Fit/Evaluate Outer**
Delta ลด Bias รวม แต่ MAE/RMSE และ Tail Errors แย่ลง ไม่ได้ผ่านเกณฑ์ความแม่นและความเสถียรที่ล็อกไว้

| Inner Metric (กก./ไร่) | Level | Signed Delta |
|---|---:|---:|
| MAE | 206.28 | 208.29 |
| RMSE | 262.57 | 274.34 |
| Bias (ทำนาย−จริง) | -54.91 | +16.46 |
| P90 Absolute Error | 420.10 | 442.89 |
| Maximum Absolute Error | 680.95 | 758.64 |

MAE improvement = -0.97% (แย่ลง 2.01 กก./ไร่) ไม่ถึง +5%; RMSE แย่ลง 11.77
ศรีสะเกษและอุตรดิตถ์แย่เกิน 10% จึงไม่ผ่านทุกเงื่อนไขหลัก ไม่ใช้ Outer เลือก Target Transform

## Protocol และหน่วยการประเมิน

Training ใช้ 10 จังหวัดชุด Phase 6B D, Weather 7 + Lag Yield + Year + Province Indicators เดิม
คง Fixed-calendar/Lead 60/Outer Schedule 2017–2025/Inner 3 ปีก่อน Outer/Shared Fit Cutoff/Grid Depth 2–3/Seed 42
CatBoost 400 Iterations, RMSE, Ordered, lr .03, l2 10, thread 1; เลือก Depth แยกด้วย Inner Final-yield MAE; Depth 2 ชนะ Exact Tie
Signed Delta = Current Yield − Lag Yield; Reconstruction = Lag Yield + Predicted Delta
ห้าม Clamp Delta ก่อน Reconstruction; Final Yield ติดลบปรับเป็นศูนย์ทั้งสองแขนเหมือนกัน
บันทึก Raw Target, Raw Reconstruction และ Clipping Flag; Selected Inner ไม่มี Clipping ทั้งสองแขน
ใช้ Experimental Signed Fitter แยก ไม่แก้ Shared Helper ที่ Clamp Prediction เดิม

Inner Selection/Gate ใช้จังหวัดเดิม 5 จังหวัดเท่านั้น ตาม Phase 6B
27 Inner Contexts × 5 = 135 แถว/แขน; 55 จังหวัด–ปีไม่ซ้ำ (2014–2024) และนับซ้ำอีก 80 แถว
Depth เลือกบน Inner ชุดเดียวกับที่ประเมิน Gate จึงมี Selection Optimism ไม่ใช่ Independent Confirmation
Outer Schedule ใช้กำหนด Inner Contexts แต่ตัวเลขรายงานนี้ไม่ใช่ Outer Evaluation แม้ปีบางปีตรงกับ Outer ในงานก่อน

## ผล Inner รายจังหวัด

| จังหวัด | MAE Level | MAE Delta | Delta MAE เปลี่ยน | Gate ไม่แย่เกิน 10% |
|---|---:|---:|---:|---|
| จันทบุรี | 314.49 | 280.67 | -10.76% | ผ่าน |
| ศรีสะเกษ | 157.39 | 179.30 | 13.92% | ไม่ผ่าน |
| อุตรดิตถ์ | 152.26 | 214.98 | 41.20% | ไม่ผ่าน |
| สุราษฎร์ธานี | 174.18 | 153.52 | -11.86% | ผ่าน |
| ชุมพร | 233.10 | 213.00 | -8.62% | ผ่าน |

## ผล Inner รายปี

คู่ตัวเลขเรียง Level / Delta หน่วย กก./ไร่; n นับ Context ซ้ำตาม Protocol ไม่ใช่จำนวนจังหวัด–ปีอิสระ

| ปี Validation | n | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| 2014 | 5 | 151.61 / 99.34 | 178.26 / 105.42 | -144.46 / -1.08 |
| 2015 | 10 | 41.53 / 138.09 | 42.45 / 152.67 | 3.48 / 138.09 |
| 2016 | 15 | 223.12 / 215.35 | 233.06 / 228.09 | 147.97 / 176.15 |
| 2017 | 15 | 322.25 / 432.71 | 359.29 / 492.96 | -201.42 / -296.63 |
| 2018 | 15 | 140.73 / 101.90 | 168.66 / 128.67 | -140.73 / 46.84 |
| 2019 | 15 | 352.93 / 410.90 | 391.78 / 439.75 | -159.43 / -76.55 |
| 2020 | 15 | 229.23 / 135.96 | 275.87 / 165.07 | -23.38 / 67.84 |
| 2021 | 15 | 131.51 / 88.35 | 169.46 / 95.12 | -126.85 / -10.13 |
| 2022 | 15 | 238.04 / 225.40 | 327.55 / 285.16 | -15.71 / 49.33 |
| 2023 | 10 | 104.07 / 104.80 | 121.90 / 134.23 | 0.05 / 45.83 |
| 2024 | 5 | 213.36 / 207.08 | 253.02 / 265.67 | 213.36 / 207.08 |

## Paired Errors, Tail และ Depth Stability

Paired Gain = |Level Error| − |Delta Error| ใน Outer-context/Validation-year/จังหวัดเดียวกัน
Mean -2.01, Median -12.38 กก./ไร่; Delta ชนะ/เสมอ/แพ้ 60/0/75 จาก 135 แถว (Tie Tolerance 1e-9)
ไม่อ้าง Statistical Significance จาก Contexts ที่ซ้อนกัน

Delta พลาดสูงสุดอุตรดิตถ์ 2017 ในบริบทปี 2018/2019: จริง 923.23 ทำนาย 164.59 ต่ำไป 758.64
นี่คือเหตุการณ์เดียวที่นับซ้ำ ไม่ใช่ความผิดพลาดอิสระสองครั้ง
Level พลาดสูงสุดชุมพร 2019 ในบริบทปี 2020/2021: จริง 1,759.64 ทำนาย 1,078.69 ต่ำไป 680.95
Delta ไม่แก้ Tail Risk แม้ Bias รวมใกล้ศูนย์ การเปลี่ยน Bias ไม่เท่ากับลด Absolute Error

| Outer-context ที่ใช้เลือก | Level Depth | Delta Depth |
|---|---:|---:|
| 2017 | 3 | 3 |
| 2018 | 3 | 3 |
| 2019 | 3 | 3 |
| 2020 | 3 | 2 |
| 2021 | 3 | 2 |
| 2022 | 2 | 2 |
| 2023 | 3 | 2 |
| 2024 | 3 | 2 |
| 2025 | 3 | 3 |

Level Depth 3 แปดบริบท/Depth 2 หนึ่งบริบท; Delta Depth 3 สี่บริบท/Depth 2 ห้าบริบท เปลี่ยนสองครั้งเท่ากัน
Switch Count เท่ากันไม่ได้ยืนยันความแม่นเสถียรเท่ากัน ผลนี้รวม Target Transform และการเลือก Depth แยก ไม่ใช่ผลเมื่อบังคับ Depth เท่ากัน

## Integrity, Availability และไฟล์

Level Inner Choices และ MAE ทำซ้ำ Phase 6B D ผ่าน Numerical Tolerance ที่กำหนดก่อนรัน
Fit Audit 108 Requests = 44 Fresh Fits + 64 Identical-key Reuses; ไม่มี Outer Fits หลัง Gate ล้มเหลว
Cache ผูก Target Arm/Depth/Fold Year/Cutoff/Issue Dates/Actual Training Targets/Inputs/Source/Code/Protocol Hash
Target Pair Lineage 3,555 คู่ / Availability 7,110 Records ตรวจ Current/Prior Yield สำหรับ Training/Selection ทุก Fold
Lag ที่ใช้จริงเทียบ Annual Source; Missing/Future Publication/Source-version Mismatch ต้อง Fail-fast ไม่ลดแถว
Historical OAE/POWER Publication/Vintage ยัง unverified เก็บ Warnings ไม่เปลี่ยน PIT Status

ก่อน Training: Python 279/279 (266 เดิม + 13 ใหม่), JavaScript 30/30 ผ่าน ไม่มี Skipped Tests
หลัง Training: Python 279/279 และ JavaScript 30/30 ผ่านซ้ำ ไม่มี Failures/Skipped Tests
Before-task Protected 775 Entries ตรง; Run Configuration ป้องกัน 778 Entries รวมไฟล์ใหม่ก่อน Fit
Source/Input/Manifest/Code Hashes และ Sealed Run Inventory 18 Entries ตรวจตรงหลัง Training
ตรวจ Hashes ซ้ำหลัง Postflight Tests ตรงทั้งหมด; Git Status เดิมไม่หายหรือเปลี่ยน เพิ่มเฉพาะไฟล์และ Artifact Directory ของงานนี้
Production SHA256: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

เพิ่มเฉพาะ Runner, Tests, Preflight Report และรายงานผล; รักษา Dirty/Untracked เดิม
Logs/Snapshot: `.build/rebaseline-backups/phase7b/`
Artifacts: `research_data/five_province_history/training/delta_target_exploratory/phase7b_20261011T170140373940Z/`
เก็บ Config/Manifest/Folds/Source Snapshot/Hashes/Dependencies/Warnings/Inner Candidate และ Selected Predictions/Choices/Tuning/Target Lineage/Fit Audit/Status
ไม่มี Outer Predictions/Metrics เพราะ Gate ไม่ผ่าน ไม่เขียนทับ Artifacts เดิม

ข้อจำกัด: ข้อมูลรายปีขนาดเล็ก, Revised Labels/Lag, การเลือกและประเมินซ้ำบน Inner และปีเก่าที่เคยใช้พัฒนา
ไม่อ้างสาเหตุ ไม่สรุปว่า Delta ใช้ไม่ได้ทุก Dataset แต่หยุดภายใต้ Protocol นี้และรอคำสั่ง
