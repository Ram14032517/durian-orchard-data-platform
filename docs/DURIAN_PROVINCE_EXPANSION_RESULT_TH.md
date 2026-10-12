# Phase 6B — Province Expansion Exploratory Results

วันที่ 11 ตุลาคม 2026 — รัน Training **หนึ่งรอบ**; ไม่เปลี่ยน Production/API/Frontend และไม่รับรอง Historical PIT

## ข้อสรุป

เพิ่มข้อมูลฝึกจาก 5 เป็น 10 จังหวัด **ยังไม่ช่วย MAE บน 45 Evaluation Keys เดิม** ภายใต้ Protocol นี้. With Weather แย่ลง 6.97 กก./ไร่ (3.40%) และ No Weather แย่ลง 23.13 กก./ไร่ (11.15%). ไม่เลือกจังหวัดใหม่ ไม่แก้ Features/Grid และไม่ฝึกซ้ำหลังเห็นคะแนน.

## Primary Evaluation — 5 จังหวัดเดิม × 2017–2025

ทุกแขนใช้ 45 Keys เดียวกัน; หน่วย MAE/RMSE/Bias เป็น กก./ไร่; Bias = predicted − actual.

| แขน | Training cohort | Weather | MAE | RMSE | Bias |
|---|---:|---|---:|---:|---:|
| A | 5 | ไม่มี | 207.45 | 267.01 | −60.92 |
| B | 5 | 7 Features รวม VPD | 204.85 | 266.47 | −59.53 |
| C | 10 | ไม่มี | 230.58 | 280.92 | −59.21 |
| D | 10 | 7 Features รวม VPD | 211.82 | 270.11 | −64.91 |

Paired gain = absolute error ของ cohort 5 − cohort 10; บวกหมายถึงเพิ่มจังหวัดแล้วดีขึ้น.

| เปรียบเทียบ | Mean gain | Median gain | ชนะ/เสมอ/แพ้ |
|---|---:|---:|---|
| A − C: No Weather | −23.13 | −24.75 | 17 / 0 / 28 |
| B − D: With Weather | −6.97 | −17.35 | 16 / 0 / 29 |

### รายจังหวัด: With Weather

| จังหวัด | B: 5 จังหวัด | D: 10 จังหวัด | Gain B − D |
|---|---:|---:|---:|
| จันทบุรี | 297.10 | 343.39 | −46.28 |
| ศรีสะเกษ | 175.28 | 172.94 | +2.33 |
| อุตรดิตถ์ | 125.06 | 143.11 | −18.05 |
| สุราษฎร์ธานี | 176.22 | 175.18 | +1.04 |
| ชุมพร | 250.61 | 224.48 | +26.13 |

### รายปี: With Weather

| ปี | B | D | Gain B − D |
|---|---:|---:|---:|
| 2017 | 325.16 | 322.25 | +2.90 |
| 2018 | 205.02 | 140.73 | +64.28 |
| 2019 | 321.92 | 357.49 | −35.57 |
| 2020 | 254.72 | 223.72 | +31.00 |
| 2021 | 112.91 | 136.26 | −23.34 |
| 2022 | 213.57 | 288.73 | −75.15 |
| 2023 | 72.90 | 104.07 | −31.17 |
| 2024 | 214.27 | 213.36 | +0.92 |
| 2025 | 123.21 | 119.78 | +3.43 |

D ชนะค่าเฉลี่ยรายปี 5/9 ปี แต่ชนะรายกรณีเพียง 16/45; จึงไม่ใช่ผลดีที่สม่ำเสมอทั่วพื้นที่. No Weather ชนะค่าเฉลี่ยรายปี 3/9 ปี; ข้อมูลทั้งสี่แขนรวม MAE/RMSE/Bias รายปีและจังหวัดเก็บครบใน CSV ไม่ตัดกรณีที่แย่ลง.

## Secondary Evaluation — 5 จังหวัดใหม่ × 2017–2025

ประเมิน C/D แยก 45 Keys ใหม่. ไม่ทำนาย A/B ด้วย province indicator เป็นศูนย์สำหรับจังหวัดที่ไม่อยู่ใน cohort: unknown province ต้องถูกปฏิเสธ. ดังนั้น **ไม่มี matched 5→10 comparison สำหรับ Secondary** และห้ามเทียบ MAE กลุ่มใหม่กับ Primary เพื่ออ้างว่าขยายจังหวัดแล้วแม่นขึ้น.

| แขน | MAE | RMSE | Bias |
|---|---:|---:|---:|
| C: 10 / No Weather | 178.61 | 228.66 | −50.01 |
| D: 10 / With Weather | 171.58 | 217.64 | −34.70 |

| จังหวัดใหม่ | C MAE | D MAE |
|---|---:|---:|
| ระยอง | 319.29 | 247.17 |
| นครราชสีมา | 103.12 | 128.18 |
| ประจวบคีรีขันธ์ | 263.92 | 259.33 |
| นครศรีธรรมราช | 112.85 | 114.88 |
| ระนอง | 93.85 | 108.36 |

Secondary Weather gain C − D = +7.02 กก./ไร่ (3.93%), ชนะ/เสมอ/แพ้ 24/0/21. Depth ไม่ถูกเลือกจาก Secondary labels; คะแนนนี้เป็น diagnostic ของจังหวัดใหม่เท่านั้น.

## Error Analysis และความเสถียร

- Primary With Weather จุดที่แย่ลงจาก expansion มากสุด: จันทบุรี 2022, absolute error เพิ่ม **240.54** กก./ไร่; D ทาย 1,487.24 เทียบจริง 2,194.40 (error −707.16). รองลงมาอุตรดิตถ์ 2019 เพิ่ม 120.05, ศรีสะเกษ 2017 เพิ่ม 107.33, ศรีสะเกษ 2019 เพิ่ม 100.24, สุราษฎร์ธานี 2019 เพิ่ม 83.01.
- Maximum Primary absolute errors: A=716.60 (ชุมพร 2019), B=740.33 (ชุมพร 2019), C=642.55 (ชุมพร 2019), D=707.16 (จันทบุรี 2022). ลด maximum error บางแขนไม่ได้แปลว่า MAE รวมดีขึ้น.
- Maximum Secondary: C=657.24 และ D=565.79 กก./ไร่, ทั้งคู่ระยอง 2017 และทำนายต่ำกว่าจริง.
- ผลสอดคล้องกับความเสี่ยง **negative transfer** ในการรวมจังหวัด แต่ยังไม่พิสูจน์กลไก: pooled relationships, ความต่าง target/ฤดู/proxy และข้อจำกัด depth อาจเกี่ยวข้อง. ไม่อ้างว่าความแล้ง/ดิน/น้ำบาดาลทำให้ผิดพลาด และไม่สรุปเหตุเชิงสาเหตุจาก Ablation.

Depth ที่เลือกตามปี 2017→2025:

| แขน | Depth ตามลำดับปี | Depth 2 / 3 | จำนวนเปลี่ยน Depth |
|---|---|---|---:|
| A | 2,2,2,2,2,3,3,3,3 | 5 / 4 | 1 |
| B | 3,3,3,2,2,2,2,2,2 | 6 / 3 | 1 |
| C | 3,3,3,3,3,2,2,3,3 | 2 / 7 | 2 |
| D | 3,3,3,3,3,2,3,3,3 | 1 / 8 | 2 |

การเพิ่มจังหวัดทำให้เลือก depth 3 บ่อยขึ้น แต่ไม่มีการเพิ่ม grid หรือเลือกจาก Outer Scores. Weather contribution บน Primary คือ A−B=+2.60 และ C−D=+18.76 กก./ไร่; เป็น predictive comparison เท่านั้น ไม่ใช่ causal attribution.

## Protocol, Preflight และ Fit/Cache Audit

- Fixed-calendar/Lead 60/Outer 2017–2025/Inner 3 ปี/Shared Fit Cutoff/seed 42/grid 2/3/400 iterations และพารามิเตอร์อื่นเดิม; ไม่ใช้ ENSO
- Province encoding เป็น locked cohort indicators + year + ordered features: A/B/C/D มี 7/14/12/19 columns; ไม่ fit encoder ด้วย test rows และ reject unknown provinces
- ตรวจ Phase 6A sealed artifacts, source/code/manifest versions และ replay 130,887 consumption checks ครบ 72 contexts ก่อนฝึก. Input/Lag/Training/Selection labels ตรวจตาม role cutoff; Vintage ที่ยังไม่พิสูจน์เป็น warnings ไม่แปลงเป็น verified
- A/B fresh predictions ทำซ้ำ Phase 3 ได้ครบ 45 Keys, actual targets และ issue dates ตรงกัน (prediction tolerance atol=1e−10, rtol=1e−12). Gate ผ่านก่อนเริ่ม C/D; reference predictions ใช้เฉพาะตรวจ parity ไม่เป็น training/selection inputs
- Inner objective ใช้ 5 จังหวัดเดิมเท่านั้น. ทั้ง 36 choices ตรวจตรงกับ inner results; freezes choices/predictions ก่อนอ่าน outer evaluation labels
- Fit requests 252 ครั้ง: **92 actual fits + 160 cache reuses**, แขนละ 23 fits/40 reuses. Same fold-year/input/cutoff/depth reuse ข้าม nested contexts ได้เฉพาะ identity เดียวกัน; ไม่มี reuse ข้าม arm/cohort/features/depth/fold-year/source/cutoff
- 23 fits/แขน = depth 2/3 สำหรับปี 2014–2024 จำนวน 22 fits + selected depth ของปี 2025 อีก 1 fit. ไม่ฝึก depth ที่ไม่ได้เลือกของ Outer ปีสุดท้ายโดยไม่จำเป็น
- Predictions ครบ **270 แถว**: Primary 180 + Secondary 90, ไม่ drop keys/จังหวัด

## Tests และ Protection

- ก่อน Training: Python **266/266**, JS **30/30** ผ่าน
- หลัง Training: Python **266/266**, JS **30/30** ผ่าน
- เพิ่ม Model Tests 9 ข้อ: encoding/weather isolation, unknown province, prediction completeness, inner-only choices, outer-target mutation independence, secondary selection-label isolation, cache identity, missing/corrupt folds/cutoffs และ reference prediction gate
- Before-task protected hashes **747/747** ไม่เปลี่ยน; runner protected hashes **749/749** ไม่เปลี่ยน รวม source/tests ใหม่ที่ล็อกก่อนฝึก; protected Production/API/Frontend/Phase 6A และ artifacts เก่าไม่เปลี่ยน
- Production SHA256: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`
- ไม่มี Regression/Protocol mismatch และไม่แก้ Model Logic/Features/Grid หลังเห็น Outer Scores

## Artifacts และข้อจำกัด

Run: `research_data/five_province_history/training/province_expansion_exploratory/phase6b_20261011T140737783448Z/`

`config.json`, `manifest.json`, `folds.json`, `source_snapshot/`, `predictions.csv`, `overall.csv`, `by_year.csv`, `by_province.csv`, `paired_errors.csv`, `paired_gains.csv`, `paired_by_year.csv`, `paired_by_province.csv`, `choices.csv`, `tuning.csv`, `fit_audit.csv`, `worst_errors.csv`, `supplemental_summary.json`, `status.json` และ hash inventories. Config บันทึก Input/Code/Manifest-related hashes, Dependencies, protocol และ protected files; supplemental summary บันทึก Availability Warnings พร้อม path/SHA256 ของ evidence เดิม ไม่เขียนทับ Artifacts.

ไฟล์โค้ดใหม่เฉพาะ `tools/durian_model/experiment_province_expansion_training.py` และ `tests/test_province_expansion_training.py`; baseline hash snapshot อยู่ที่ `research_data/phase6b_before_protected_20261011.json` (hashes เท่านั้น ไม่มี Secrets).

62 source dependencies ยัง `unverified`; มี 130,347 consumptions ที่ขาด version-specific publication evidence. OAE revised targets/lag, POWER current retrieval, assumed 7-day lag และ calendar rule สร้างปี 2026 ทำให้ **Historical PIT ยังไม่รับรอง**. Climatology ไม่ใช่ archived weather forecast; target เป็นทุเรียนรวมพันธุ์และ weather เป็น provincial-point proxy.

45 Keys มีเพียง 9 ปีและจังหวัดสัมพันธ์กัน; Outer years ถูกตรวจในหลาย Phases แล้ว ไม่ใช่ untouched confirmatory holdout. ไม่ทดสอบหรืออ้าง statistical significance และไม่อ้าง causal effect. Primary/Secondary ห้ามรวมเฉลี่ยเพื่อกลบผลที่แย่ลงบนจังหวัดเดิม.

**คง Production เดิม เก็บผลลบไว้ และหยุดรอคำสั่งก่อน Phase ถัดไป.**
