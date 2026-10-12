# Phase 5B — ENSO State Ablation (Exploratory)

11 ตุลาคม 2026 — ทำหนึ่ง Training run ตาม Protocol ที่ล็อกไว้ ไม่เปลี่ยน Production

## ข้อสรุป

Observed ENSO State **ไม่ช่วยคะแนนรวมในรอบนี้**: MAE แย่ลง 9.12 กก./ไร่ (4.45%) และ RMSE แย่ลง 5.54 กก./ไร่ แม้ Bias เข้าใกล้ศูนย์ขึ้น ไม่เสนอเปลี่ยน Production หรือเพิ่มฟีเจอร์นี้จากผลนี้ ไม่ได้รันซ้ำ/เปลี่ยน Features/Grid หลังเห็น Outer Scores

| แขน | n | MAE | RMSE | Bias (ทำนาย − จริง) |
|---|---:|---:|---:|---:|
| CatBoost With Weather | 45 | 204.85 | 266.47 | -59.53 |
| Weather + Observed ENSO State | 45 | 213.97 | 272.01 | -47.00 |

ENSO Contribution = MAE(Weather) − MAE(Weather+ENSO) = **-9.1152 กก./ไร่**; median paired gain = -9.79; ชนะ/เสมอ/แพ้ = **18/0/27** (เสมอใช้ atol=1e-9, rtol=0)

## รายจังหวัด

ค่าในตารางเป็น MAE กก./ไร่; Contribution บวกหมายถึง ENSO ช่วยลด error

| จังหวัด | n | Weather | Weather+ENSO | Contribution | ชนะ/เสมอ/แพ้ |
|---|---:|---:|---:|---:|---|
| จันทบุรี | 9 | 297.10 | 301.67 | -4.57 | 3/0/6 |
| ศรีสะเกษ | 9 | 175.28 | 177.19 | -1.91 | 4/0/5 |
| อุตรดิตถ์ | 9 | 125.06 | 124.63 | +0.43 | 4/0/5 |
| สุราษฎร์ธานี | 9 | 176.22 | 206.72 | -30.49 | 2/0/7 |
| ชุมพร | 9 | 250.61 | 259.64 | -9.04 | 5/0/4 |

สุราษฎร์ธานีเป็นกลุ่มที่คะแนนแย่ลงมากที่สุด อุตรดิตถ์ดีขึ้นเพียง 0.43 และชนะเพียง 4/9; ชุมพรชนะ 5/9 แต่ความเสียหายของกรณีที่แพ้ทำให้ MAE รวมจังหวัดแย่ลง ไม่ควรใช้ win count อย่างเดียว

## รายปีและ Depth Selection

| Outer ปี | Weather MAE | ENSO MAE | Contribution | Depth Weather / ENSO |
|---|---:|---:|---:|---|
| 2017 | 325.16 | 319.12 | +6.04 | 3 / 3 |
| 2018 | 205.02 | 208.05 | -3.03 | 3 / 3 |
| 2019 | 321.92 | 323.77 | -1.85 | 3 / 3 |
| 2020 | 254.72 | 286.69 | -31.96 | 2 / 3 |
| 2021 | 112.91 | 120.27 | -7.35 | 2 / 2 |
| 2022 | 213.57 | 229.28 | -15.70 | 2 / 2 |
| 2023 | 72.90 | 99.67 | -26.77 | 2 / 2 |
| 2024 | 214.27 | 204.32 | +9.95 | 2 / 2 |
| 2025 | 123.21 | 134.56 | -11.35 | 2 / 2 |

ดีขึ้นเพียง 2/9 ปี Depth ต่างกันเพียงปี 2020: Weather เลือก depth 2 จำนวน 6 ปี / depth 3 จำนวน 3 ปี; ENSO เลือก depth 2 จำนวน 5 ปี / depth 3 จำนวน 4 ปี แต่ละแขนเปลี่ยน depth เพียงครั้งเดียวตามลำดับปี ไม่เห็นการสลับไปมาบ่อย **ความนิ่งของ Depth ไม่ใช่หลักฐานว่าการเพิ่ม ENSO มีประโยชน์**

## แยก Observed ENSO State ณ Issue Date

| State | n จังหวัด–ปี | Weather MAE | ENSO MAE | Contribution | ชนะ/เสมอ/แพ้ |
|---|---:|---:|---:|---:|---|
| El Niño | 9 | 250.04 | 248.92 | +1.12 | 5/0/4 |
| Neutral | 15 | 204.77 | 216.17 | -11.39 | 7/0/8 |
| La Niña | 21 | 185.55 | 197.42 | -11.87 | 6/0/15 |

กลุ่ม El Niño มี MAE ดีขึ้นเล็กน้อย แต่ RMSE แย่ลงจาก 321.12 เป็น 328.51; ไม่ใช่หลักฐานการช่วยทำนายในสภาพเอลนีโญอย่างสม่ำเสมอ State คือ global bulletin ณวัน issue ของแต่ละจังหวัด ไม่ใช่การจัดทั้งปีเป็น State เดียว

## ข้อผิดพลาดสำคัญ

- ผิดพลาดมากที่สุดทั้งสองแขน: **ชุมพร 2019** ผลจริง 1,759.64; Weather ทำนาย 1,019.30 (ต่ำไป 740.33), ENSO ทำนาย 975.65 (ต่ำไป 783.99 กก./ไร่) การเพิ่ม State ไม่แก้ปัญหา underprediction นี้
- Paired deterioration มากที่สุด: **สุราษฎร์ธานี 2020 (Neutral)** absolute error เพิ่มจาก 366.93 เป็น 491.78 (+124.85); ตามด้วยชุมพร 2017 (+88.37) และอุตรดิตถ์ 2020 (+80.67)
- 2024 ดีขึ้นเฉลี่ย 9.95 แต่ยัง overpredict โดย Bias จาก +213.71 เป็น +197.36; การดีขึ้นปีเดียวไม่หักล้างความเสียหายรวม

อาจเป็นเพราะ global categorical signal หยาบ/ซ้ำกับ weather และเพิ่ม split alternatives ในข้อมูลขนาดเล็ก รวมถึงมี season/region/management confounding; นี่เป็นสมมติฐาน ไม่ได้พิสูจน์สาเหตุจาก Ablation ไม่อนุมานเรื่องระบบน้ำหรือเหตุภัยแล้งสวนจาก error เพียงอย่างเดียว

## Test ที่แก้และ Cache Audit

แก้เฉพาะ `tests/test_enso_training.py` ไม่แก้ Model Logic, Cache, Features หรือ Protocol:

- 2014–2024 มี unique fits 11 × 4 = 44; ปี 2025 ใช้ 2 Outer winners รวม **46** ไม่ใช่ 48
- 23 keys ต่อแขน; Audit 126 prediction requests = 46 fits + 80 reuses
- ปีสุดท้ายเลือก depth จาก Inner 2022/2023/2024 เท่านั้น มี predictions ครบ 45 evaluation keys ต่อแขน
- Tests ตรวจว่าแต่ละ cache key ผูก fold year/arm/parameters/cutoff/training rows เดียวกัน, record แรกเป็น fit และครั้งต่อมา reuse; ทุกปี Inner มีทั้งสอง depth ครบทุกแขน
- Outer-target poisoning test ไม่เปลี่ยน parameter choices หรือ predictions

Actual Training Fit Audit ยืนยัน counts เดียวกัน: 46 fits, 80 reuses, 126 requests และ depth ทุกปีตรงกับค่าเฉลี่ย Inner MAE ของแขนนั้น การ reuse ระหว่าง Outer contexts ใช้ temporal fold เดียวกันและ inputs/labels/source hashes เดิม ไม่ใช่ reuse ข้าม fold year หรือ feature set

Encoding ใช้ fixed vocabulary El Niño/Neutral/La Niña ที่กำหนดก่อนทดลอง ไม่มี learned encoder parameters และไม่เรียน category vocabulary จาก Outer targets/data; known category ที่ยังไม่พบใน Training มีคอลัมน์เดิม ส่วน Missing/Unknown ถูก fail-fast ไม่เติมจากรายงานอนาคต

## Reproducibility และ Artifacts

Run: `research_data/five_province_history/training/enso_state_preparation_exploratory/phase5b_20261011T132904962005Z/`

- locked protocol hash: `abffd1925cbdc8bdbd0d96e1c8a975d2f42ca0c19900a6820b3b810020f27b70`
- `config.json`, `manifest.json`, `folds.json`: Code/Data/Manifest/Archive Hashes, Seed, Dependencies, Git context และ cutoffs
- `source_snapshot/`: allowlisted .py sources เท่านั้น ไม่มี environment/Secrets
- `enso_lineage.json`: 1,890 consumption records พร้อมเอกสาร/source hashes และ encoded values จริง
- `base_availability.json`: availability warnings ของ OAE/POWER/labels/calendar ที่ยัง unverified; ENSO lineage แยก publication evidence จาก content authentication
- `predictions.csv`, `paired_errors.csv`, `overall.csv`, `by_year.csv`, `by_province.csv`, `by_state.csv`, `contribution.csv`, `choices.csv`, `tuning.csv`, `fit_audit.csv`, worst-case tables
- `training_status.json`: completed training=true, PIT=false, Weather regression gate passed
- `completed_artifact_hashes.json`: ตรวจครบ **105 artifacts** ตรงทั้งหมด

`status.json` ของ preparation stage เป็น training=false ตามเวลาสร้างไฟล์นั้น; สถานะ Training สุดท้ายให้อ่าน `training_status.json` ไม่เขียนทับ artifact เก่า

Weather predictions ใหม่ผ่าน gate เทียบ Phase 3 เดิมครบ 45 keys (atol=1e-10, rtol=1e-12), actual targets และ issue dates ตรงเดิม

## Tests และ Protection

- ก่อน Training: Python **245/245**, JavaScript **30/30** ผ่าน
- หลัง Training: Python **245/245**, JavaScript **30/30** ผ่านทั้งหมด
- Runner ตรวจ protected files **577 ไฟล์** ก่อน/หลัง Training แล้วตรงทั้งหมด
- เทียบสถานะก่อนแก้ Test: เปลี่ยนเพียง Test ที่อนุมัติ; Source/Archive/Model/API/Frontend และ artifacts เดิมตรงเดิม
- Production model SHA256: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

## ขอบเขตการสรุป

45 จังหวัด–ปีมีเพียง 9 Outer years และ ENSO global signal ร่วมกันหลายจังหวัด ไม่ใช่ independent samples 45 ตัวอย่าง; ยังไม่ได้ทำ significance test ที่คำนึงถึง temporal/spatial dependence จึงไม่อ้าง statistical significance หรือ causal effect

Historical archive content/OAE/POWER vintage ยัง unverified และ fixed calendar ไม่ใช่ historical predeclared rule ผลเป็น **Exploratory ไม่ใช่ Historical PIT Certified** ไม่เปลี่ยน Production ไม่เริ่ม Province Expansion/Forecast Probability และหยุดรอคำสั่ง
