# Phase 2 — Exploratory Fixed-calendar Rebaseline

รัน `20261010T131023246729Z` เสร็จ 10 ตุลาคม 2026 เวลา 20:10 น. (ไทย)
สถานะ: **Exploratory เท่านั้น ไม่ใช่ Point-in-Time Certified** และไม่เปลี่ยน Production

## Protocol และหลักฐาน

ใช้ 5 จังหวัดเดิม ทดสอบ Outer 2017–2025 จำนวน 45 จังหวัด–ปีต่อโมเดล, Lead 60 วัน
Fixed-calendar, features, candidate grid และ seed 42 คงตาม Phase 1
Inner validation 3 ปีก่อน Outer เลือกเฉพาะภายในแต่ละตระกูล ไม่มี Auto Select ข้ามตระกูล
มี 36 fold contexts, 135 predictions, 162 tuning records, 27 choices และ 189 fit audit records
เรียก helper 69 ครั้ง (57 estimator fits และ Last-year 12 ครั้งที่ไม่ fit), reuse 120 ครั้งโดยตรวจ input hashes
freeze choices และ Outer predictions ก่อนอ่าน Outer evaluation targets

ผลทั้งหมดคำนวณใหม่จากรอบนี้ ไม่ใช้ MAE 204.85 ของ protocol เดิมเป็น baseline
แม้ CatBoost ปัดแล้วได้เลขเท่ากัน ก็ไม่ใช่หลักฐานว่า protocol เก่าและใหม่เทียบตรงกันได้
ไฟล์ [config](../../../research_data/five_province_history/training/rebaseline_exploratory/20261010T131023246729Z/config.json)
เก็บ pre-fit configuration, code/data/manifest hashes, dependencies และ protocol;
[folds](../../../research_data/five_province_history/training/rebaseline_exploratory/20261010T131023246729Z/folds.json)
และ feature_lineage.json เก็บ cutoffs และแหล่งข้อมูลที่ builder ใช้จริง

## คะแนนรวม (กก./ไร่)

| โมเดล | MAE | RMSE | Bias (ทำนาย−จริง) | ชนะ/แพ้ Last-year |
|---|---:|---:|---:|---:|
| Last-year | 215.51 | 269.55 | -44.41 | อ้างอิง |
| Ridge | 212.20 | **258.03** | -27.48 | 17/28 |
| CatBoost | **204.85** | 266.47 | -59.53 | 27/18 |

CatBoost ลด MAE จาก Last-year ของรอบนี้ 10.66 กก./ไร่ (4.95%) แต่ Ridge มี RMSE ต่ำกว่า
จึงยังไม่สรุปว่า CatBoost ดีที่สุดทุกด้าน หรือพร้อมแทน Production

## MAE รายจังหวัด (9 ปีต่อจังหวัด)

| จังหวัด (รหัส) | Last-year | Ridge | CatBoost |
|---|---:|---:|---:|
| จันทบุรี (22) | 262.92 | 290.11 | 297.10 |
| ศรีสะเกษ (33) | 212.94 | 171.49 | 175.28 |
| อุตรดิตถ์ (53) | 175.26 | 128.54 | 125.06 |
| สุราษฎร์ธานี (84) | 186.92 | 214.04 | 176.22 |
| ชุมพร (86) | 239.52 | 256.82 | 250.61 |

CatBoost ชนะค่าเฉลี่ย Last-year 3/5 จังหวัด แต่แย่ลงที่จันทบุรี 34.19 และชุมพร 11.09 กก./ไร่
สุราษฎร์ธานี MAE ดีขึ้น แต่ RMSE 224.95 สูงกว่า Last-year 207.55: ยังมีความเสี่ยงข้อผิดพลาดใหญ่
RMSE/Bias ครบทุกโมเดลอยู่ใน [by_province.csv](../../../research_data/five_province_history/training/rebaseline_exploratory/20261010T131023246729Z/by_province.csv)

## MAE รายปี (5 จังหวัดต่อปี)

| ปี | Last-year | Ridge | CatBoost |
|---|---:|---:|---:|
| 2017 | 401.51 | 284.35 | 325.16 |
| 2018 | 152.13 | 206.69 | 205.02 |
| 2019 | 377.56 | 332.89 | 321.92 |
| 2020 | 136.22 | 241.77 | 254.72 |
| 2021 | 99.06 | 142.23 | 112.91 |
| 2022 | 242.00 | 229.16 | 213.57 |
| 2023 | 137.18 | 96.81 | 72.90 |
| 2024 | 220.84 | 248.91 | 214.27 |
| 2025 | 173.10 | 127.00 | 123.21 |

CatBoost ชนะ 6/9 ปี แต่แพ้ 2018, 2020, 2021; ปี 2020 MAE แย่ลง 118.50 กก./ไร่
Ridge ชนะ 5/9 ปี RMSE/Bias รายปีอยู่ใน [by_year.csv](../../../research_data/five_province_history/training/rebaseline_exploratory/20261010T131023246729Z/by_year.csv)

## Paired errors และเสถียรภาพการเลือกพารามิเตอร์

กำหนด paired gain = |error Last-year| − |error โมเดล|; ค่าบวกหมายถึงดีขึ้นในจังหวัด–ปีเดียวกัน
CatBoost: gain เฉลี่ย 10.66, มัธยฐาน 29.60, ชนะ 27/45 (60%)
Ridge: gain เฉลี่ย 3.31, มัธยฐาน -32.74, ชนะ 17/45 (37.8%)
ค่าเฉลี่ย Ridge จึงดีขึ้นแม้แพ้ในกรณีส่วนใหญ่ ไม่ควรรายงาน MAE รวมเพียงอย่างเดียว
ไม่ได้ทำ significance test หรืออ้างความเชื่อมั่นทางสถิติจากคะแนนนี้

Ridge เลือก alpha 1/10/100 จำนวน 1/5/3 ปี และเปลี่ยนค่า 5 ครั้งใน 8 รอยต่อปี
ลำดับ 2017–2025: 10,100,100,10,10,1,10,10,100
CatBoost เลือก depth 3 ใน 2017–2019 และ depth 2 ใน 2020–2025 เปลี่ยนครั้งเดียว
ค่าที่เหลือคงเดิม (iterations 400, learning_rate 0.03, l2_leaf_reg 10, Ordered)
Inner MAE margin ของ depth ที่ชนะอยู่ประมาณ 3.36–14.16 กก./ไร่
Ridge ปี 2023 margin เพียง 0.28 กก./ไร่: บาง choice มีความเปราะบาง แม้ไม่มี Outer tuning
รายละเอียด: choices.csv, tuning.csv และ paired_errors.csv ในโฟลเดอร์รัน

## ข้อผิดพลาดและขอบเขตการอธิบาย

- ชุมพร 2019: จริง 1,759.64, CatBoost 1,019.30 (ต่ำไป 740.33), Ridge ต่ำไป 754.94 กก./ไร่
  ทั้งสองโมเดลจับการเพิ่มผลผลิตครั้งใหญ่ไม่ทัน; ไม่ใช่หลักฐานว่าภัยแล้งหรือน้ำใต้ดินเป็นสาเหตุ
- ชุมพร 2020: CatBoost ต่ำไป 447.99 เทียบ Last-year ต่ำไป 150.98; เป็น paired loss ใหญ่ 297.01
- จันทบุรี 2017 และ 2022: CatBoost ต่ำไป 497.78 และ 466.62 ตามลำดับ สะท้อนปัญหารายจังหวัดที่ MAE รวมกลบไว้
- ปี 2024 CatBoost bias +213.71 แต่ปี 2019 bias -210.86: ความผิดพลาดต่างทิศทาง ห้ามบังคับ climate penalty จาก residual อย่างเดียว

อาจเกี่ยวกับข้อมูลขนาดเล็ก การเปลี่ยนแปลงการจัดการสวน หรืออากาศอ้างอิงระดับจังหวัดที่ไม่แทนสวนทั้งหมด
แต่ยังไม่มีหลักฐานแยกสาเหตุเหล่านี้; ไม่ได้ทำ ablation ในรอบนี้
ช่วงฝึก earliest Inner มีเพียง 20 แถว ความไม่แน่นอนในการเลือกพารามิเตอร์ยังสูง

## Checks และข้อจำกัดที่ยังเหลือ

JavaScript 30/30 ผ่าน; Python 211/211 ผ่าน (208 เดิม + 3 mocked training tests ใหม่)
แก้ floating-point assertions ไม่แก้สูตร Business Logic; มีสำเนาก่อนแก้แบบ allowlist ไม่รวม secrets
ตรวจ artifact hashes 18 รายการและ protected hashes 116 ไฟล์หลัง Training ไม่พบเปลี่ยน
Production SHA256 คงเดิม:
`B4B9E0985E6BA5E6EE371D8988CAD5E65DEE031B345EB0CF13A8695F91658680`
Git มี changes/untracked เดิมจำนวนมาก ไม่ reset/ลบ/commit; ตรวจ diff และ whitespace แล้ว

Guard ตรวจ observed weather, climatology, lag yield, training/selection labels และ cutoffs ทุก Outer/Inner
รวมทั้ง whitelist และ source lineage; อย่างไรก็ตาม tests ผ่านไม่ใช่หลักฐานว่า Historical PIT ผ่าน
OAE/POWER ยังขาด historical publication/vintage evidence; labels/lag ที่ปรับปรุงภายหลังยังมี revised-data risk
Fixed-calendar เป็นกฎทดลองกำหนดในปี 2026 ไม่ใช่หลักฐานการออกพยากรณ์จริงในอดีต
อากาศอนาคตใช้ climatology ไม่ใช่ historical forecast; POWER เป็นข้อมูลฉบับปัจจุบันที่อาจปรับย้อนหลัง
OAE เป็นผลผลิตทุเรียนรวมพันธุ์/ฤดู ไม่ใช่หมอนทองล้วนหรือผลผลิตสวนรายแปลง
ปี Outer เคยถูกตรวจในการพัฒนาก่อนแล้ว จึงไม่ใช่ชุดยืนยันใหม่ที่ไม่เคยเห็น

คง Production/API/Frontend เดิม ไม่ทำ Weather Ablation หรือ Province Expansion
หยุดหลังรอบนี้ รอคำสั่งถัดไป ไม่ปรับ features/grid/protocol ตามคะแนน Outer
