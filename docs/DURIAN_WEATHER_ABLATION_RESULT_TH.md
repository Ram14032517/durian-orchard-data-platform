# Phase 3 — Exploratory Weather Ablation

วันที่ 11 ตุลาคม 2026; รันครั้งเดียว `20261011T122324056845Z` เสร็จ 19:24 น. (ไทย)
**ผลสำรวจย้อนหลัง ไม่ใช่ Point-in-Time Certified ไม่ใช่ผลเชิงสาเหตุ และไม่เปลี่ยน Production**

## สรุป

การเพิ่ม Weather 7 ตัวรวม VPD ลด MAE จาก CatBoost No Weather เพียง **2.60 กก./ไร่ (1.25%)**
RMSE ลด 0.54 กก./ไร่ ชนะรายแถว 27/45 แต่ชนะค่าเฉลี่ยรายปีเพียง 4/9 ปี และรายจังหวัด 3/5
ผลประโยชน์ยังไม่สม่ำเสมอ: จันทบุรีดีขึ้นเมื่อเทียบ No Weather แต่ยังแพ้ Last-year;
ชุมพรแย่ลงทั้งเมื่อเทียบ No Weather และ Last-year จึงไม่เสนอแทนโมเดล Production

| แขนทดลอง | MAE | RMSE | Bias (ทำนาย−จริง) | Median AE | ชนะ/เสมอ/แพ้ Last-year |
|---|---:|---:|---:|---:|---:|
| A Last-year | 215.51 | 269.55 | -44.41 | 179.94 | อ้างอิง |
| B CatBoost No Weather | 207.45 | 267.01 | -60.92 | 169.20 | 22/0/23 |
| C CatBoost With Weather | 204.85 | 266.47 | -59.53 | 183.69 | 27/0/18 |

ทุกคะแนนหน่วย กก./ไร่ คำนวณใหม่จาก 45 จังหวัด–ปีเดียวกันต่อแขน ไม่คัดคะแนนเดิม
C และ A fresh predictions ตรง Phase 2 ภายใน numerical tolerance ที่กำหนดก่อนรัน
แม้ C มี MAE ต่ำสุด แต่ median absolute error สูงกว่า B; ห้ามกล่าวว่าดีขึ้นทุกตัวชี้วัด

## MAE รายจังหวัด

Weather gain = MAE B − MAE C; บวกหมายถึงชุด C ดีกว่า B

| จังหวัด | A Last-year | B No Weather | C With Weather | Weather gain | C ชนะ/เสมอ/แพ้ B |
|---|---:|---:|---:|---:|---:|
| จันทบุรี (22) | 262.92 | 309.74 | 297.10 | +12.63 | 5/0/4 |
| ศรีสะเกษ (33) | 212.94 | 185.59 | 175.28 | +10.31 | 5/0/4 |
| อุตรดิตถ์ (53) | 175.26 | 154.09 | 125.06 | +29.03 | 8/0/1 |
| สุราษฎร์ธานี (84) | 186.92 | 155.78 | 176.22 | -20.44 | 5/0/4 |
| ชุมพร (86) | 239.52 | 232.06 | 250.61 | -18.54 | 4/0/5 |

จันทบุรี C ดีขึ้นจาก B 4.08% แต่ MAE ยังสูงกว่า A 34.19 กก./ไร่ และ bias -205.10
ชุมพร C แย่ลงจาก B 7.99%, RMSE เพิ่ม 16.67 และ bias ติดลบมากขึ้นจาก -66.52 เป็น -104.27
สุราษฎร์ธานีแม้ C ชนะรายแถว 5/9 แต่แพ้ค่าเฉลี่ยเพราะมีบางข้อผิดพลาดใหญ่; bias เพิ่มจาก +105.40 เป็น +139.29
ศรีสะเกษ MAE ลด แต่ RMSE เพิ่ม 7.15 เช่นกัน; รายละเอียด RMSE/Bias ทุกจังหวัดอยู่ by_province.csv

## MAE รายปี

| ปี | A Last-year | B No Weather | C With Weather | Weather gain |
|---|---:|---:|---:|---:|
| 2017 | 401.51 | 317.48 | 325.16 | -7.67 |
| 2018 | 152.13 | 178.31 | 205.02 | -26.71 |
| 2019 | 377.56 | 319.77 | 321.92 | -2.15 |
| 2020 | 136.22 | 262.37 | 254.72 | +7.65 |
| 2021 | 99.06 | 104.51 | 112.91 | -8.41 |
| 2022 | 242.00 | 259.73 | 213.57 | +46.15 |
| 2023 | 137.18 | 74.81 | 72.90 | +1.91 |
| 2024 | 220.84 | 228.31 | 214.27 | +14.04 |
| 2025 | 173.10 | 121.77 | 123.21 | -1.44 |

Weather ช่วย MAE ปี 2020/2022/2023/2024 แต่ RMSE ดีขึ้นเพียง 2017/2022/2024 (3/9 ปี)
ปี 2023 MAE ลด 1.91 แต่ RMSE เพิ่ม 24.06; การอ่านแค่ MAE จะไม่เห็นความผิดพลาดปลายหาง
ทั้ง B/C ยังแพ้ A ในปี 2018/2020/2021; RMSE/Bias รายปีอยู่ by_year.csv

## Paired errors และการเลือก Depth

กำหนด paired weather gain = |error B| − |error C| ในจังหวัด–ปีเดียวกัน
เฉลี่ย +2.597247, มัธยฐาน +11.156573 กก./ไร่; ชนะ/เสมอ/แพ้ 27/0/18 (tie tolerance 1e-9)
ประโยชน์สูงสุดศรีสะเกษ 2020 +164.03 แต่เสียมากสุดสุราษฎร์ธานี 2017 -234.97
ไม่ทดสอบ/อ้าง statistical significance จาก 45 แถวที่มีความสัมพันธ์ตามจังหวัดและปี

| ปี Outer | B depth | C depth |
|---|---:|---:|
| 2017–2019 | 2 | 3 |
| 2020–2021 | 2 | 2 |
| 2022–2025 | 3 | 2 |

B เลือก depth 2 ห้าปี/depth 3 สี่ปี; C เลือก depth 3 สามปี/depth 2 หกปี
แต่ละแขนเปลี่ยน depth ครั้งเดียว ต่างกัน 7/9 ปี; B Inner winner margin 0.50–3.75 กก./ไร่
C margin 3.36–14.16; B บาง choice เปราะบาง ไม่ได้อ้าง stability จาก switch count อย่างเดียว
การทดลองนี้วัด predictive contribution ของ weather-enabled pipeline ที่จูนแยก ไม่ใช่ effect ของ weather
เมื่อบังคับ depth เท่ากัน และไม่ได้ทดลองแยก VPD จาก weather อีกหกตัว

## กรณีผิดพลาดมากและข้อจำกัดการอธิบาย

- ชุมพร 2019 จริง 1,759.64: A ต่ำไป 708.20, B ต่ำไป 716.60, C ต่ำไป 740.33 กก./ไร่
  ทั้งสามยังจับการเพิ่มผลผลิตครั้งใหญ่นี้ไม่ทัน Weather ไม่แก้ปัญหานี้
- ชุมพร 2020: B ต่ำไป 236.11 แต่ C ต่ำไป 447.99 ทำให้ paired error แย่ลง 211.88
- สุราษฎร์ธานี 2017: B สูงไป 106.10 แต่ C สูงไป 341.07 เป็น largest weather loss 234.97
- จันทบุรี 2017: B ต่ำไป 650.90, C ต่ำไป 497.78; Weather ช่วย แต่ข้อผิดพลาดยังสูง

Residuals ระบุว่าโมเดลยังพลาดทั้งการเพิ่ม/ลดผลผลิตเฉียบพลัน และบางจังหวัดทายต่ำต่อเนื่อง
ยังแยกไม่ได้ว่าเกิดจากการจัดการสวน ระบบน้ำ หรือความละเอียดอากาศ ไม่อนุมานภัยแล้ง/น้ำใต้ดิน/สรีรวิทยาเป็นสาเหตุ
ข้อมูล OAE รวมพันธุ์และนอกฤดู ไม่ใช่หมอนทองล้วน; อากาศหนึ่งจุด/จังหวัดและฤดู/อายุผลเป็น proxy
Future weather ใช้ climatology ไม่ใช่ archived historical forecast; POWER เป็น revised meteorology/reanalysis
OAE/POWER historical vintage และ publication dates ยัง unverified; guard ผ่านไม่ทำให้ Historical PIT ผ่าน
Inner แรกมี train 20 แถว และ Outer 2017–2025 เคยใช้ตรวจระหว่างพัฒนา ไม่ใช่ independent confirmation set

## Protocol, Checks และไฟล์

คง 5 จังหวัด, Fixed-calendar, lead 60, Outer 2017–2025, Inner 3 ปีก่อน, shared fit cutoff เดิม
seed 42, CatBoost 400 iterations/Ordered/RMSE/lr .03/l2 10/depth 2–3 ตามเดิม
B มี 7 design columns; C มี 14, weather เจ็ดตัวรวม VPD ตรง Phase 2
No Weather ตัด weather/derived weather ออกจาก actual model inputs และ consumed lineage/dependencies
ทั้ง 36 contexts ตรวจ row keysets, cutoffs, actual value lineage และ availability records ก่อน fit
ทุก Outer estimates/choices freeze ก่อนอ่าน Outer targets; cache แยก arm/protocol/params/cutoffs/consumed inputs
ไม่มีข้ามครอบครัว ไม่มีเพิ่มจังหวัด ไม่มี feature selection ไม่มี rerun experiment เพื่อไล่คะแนน

Outputs ใหม่: [โฟลเดอร์รัน](../research_data/five_province_history/training/weather_ablation_exploratory/20261011T122324056845Z/)
เก็บ config/protocol/data/code/manifest hashes, source_snapshot, consumed dependencies/lineage,
fold cutoffs, availability, 135 predictions, 135 tuning rows, 27 choices, 162 fit audit records
58 fresh helper calls (46 estimator fits + 12 Last-year ไม่ fit) และ 104 identical-cache reuses
ตรวจ artifact inventory 32 รายการและ protected hashes 249 ไฟล์หลัง Training ตรงทั้งหมด
Protocol SHA256: `5189287244e2809b41866399a117e4fa0836efdaacabb2cccfea29c7fae87a55`
Production SHA256: `B4B9E0985E6BA5E6EE371D8988CAD5E65DEE031B345EB0CF13A8695F91658680`

ก่อน Training: Python 225/225 (211 เดิม + 14 ใหม่), JavaScript 30/30 ผ่าน ไม่มี regression
หลัง Training: Python 225/225 และ JavaScript 30/30 ผ่านอีกครั้ง ไม่มี failure หรือ skipped tests
หลัง tests ตรวจ protected hashes 249 ไฟล์และ artifact hashes 32 รายการอีกครั้ง ไม่พบเปลี่ยน
Logs อยู่ `.build/rebaseline-backups/phase3-weather-ablation/` แยก preflight/postflight
สำเนา README ก่อนแก้เป็น allowlist; source snapshot เก็บเฉพาะโมเดล ไม่รวม env/API credentials

ไฟล์ที่เพิ่ม: experiment_weather_ablation.py, test_weather_ablation.py และรายงานนี้
แก้ tools/durian_model/README_TH.md เฉพาะคำสั่ง/สถานะอนุมัติ; ไม่แก้ helper/Production/API/Frontend
ตาม Ponytail ใช้ shared builder/guard/design/fitter เดิม แต่แยก runner และ artifacts เพื่อรักษา callers เดิม
หยุดหลังตรวจส่งงาน ไม่เปลี่ยนโมเดลบนเว็บ ไม่ทดลองเพิ่ม และรอคำสั่งถัดไป
