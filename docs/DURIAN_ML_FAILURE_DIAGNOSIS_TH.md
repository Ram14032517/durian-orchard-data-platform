# Phase 7A — Durian ML Failure Diagnosis

วันที่ 11 ตุลาคม 2026; Audit only ใช้ Artifacts เดิม ไม่ฝึกโมเดล ไม่จูน ไม่เพิ่ม Inputs และไม่เปลี่ยน Production/API/Frontend
Historical PIT ยังไม่รับรอง ผลทั้งหมดเป็น Exploratory และเป็นการวิเคราะห์หลังเห็น Outer Outcomes ไม่ใช่หลักฐานยืนยันโมเดลใหม่

## Findings

### 1. Expansion แย่ลงโดยกระจุกตัว ไม่ใช่ทุกจังหวัด

Primary Evaluation ใช้ 45 Keys เดิม: จันทบุรี ศรีสะเกษ อุตรดิตถ์ สุราษฎร์ธานี ชุมพร × 2017–2025
ตัวอักษร A–D ในรายงานนี้หมายถึงแขน Phase 6B ไม่ใช่ตัวอักษรของ Phase 3

| แขน | MAE | RMSE | Bias: ทำนาย−จริง |
|---|---:|---:|---:|
| A: 5 จังหวัด / No Weather | 207.45 | 267.01 | -60.92 |
| B: 5 จังหวัด / Weather | 204.85 | 266.47 | -59.53 |
| C: 10 จังหวัด / No Weather | 230.58 | 280.92 | -59.21 |
| D: 10 จังหวัด / Weather | 211.82 | 270.11 | -64.91 |

หน่วย กก./ไร่; Expansion Gain = MAE กลุ่มฝึกเดิม − MAE กลุ่มฝึกขยาย
A→C Gain -23.13 ชนะ/เสมอ/แพ้ 17/0/28; B→D Gain -6.97 ชนะ/เสมอ/แพ้ 16/0/29
Secondary MAE ของ C/D = 178.61/171.58 ไม่ใช่หลักฐานว่าการขยายดีกว่าสำหรับจังหวัดใหม่ เพราะไม่มีแขนฝึก 5 จังหวัดที่ประเมินกลุ่มใหม่นี้เป็นคู่เทียบ

| จังหวัดเดิม | MAE B | MAE D | Expansion Gain | Bias B → D |
|---|---:|---:|---:|---:|
| จันทบุรี | 297.10 | 343.39 | -46.28 | -205.10 → -245.77 |
| ศรีสะเกษ | 175.28 | 172.94 | +2.33 | -58.78 → -22.85 |
| อุตรดิตถ์ | 125.06 | 143.11 | -18.05 | -68.78 → -49.59 |
| สุราษฎร์ธานี | 176.22 | 175.18 | +1.04 | +139.29 → +90.27 |
| ชุมพร | 250.61 | 224.48 | +26.13 | -104.27 → -96.63 |

| ปี | MAE B | MAE D | Expansion Gain |
|---|---:|---:|---:|
| 2017 | 325.16 | 322.25 | +2.90 |
| 2018 | 205.02 | 140.73 | +64.28 |
| 2019 | 321.92 | 357.49 | -35.57 |
| 2020 | 254.72 | 223.72 | +31.00 |
| 2021 | 112.91 | 136.26 | -23.34 |
| 2022 | 213.57 | 288.73 | -75.15 |
| 2023 | 72.90 | 104.07 | -31.17 |
| 2024 | 214.27 | 213.36 | +0.92 |
| 2025 | 123.21 | 119.78 | +3.43 |

จันทบุรี 2022 เพียงแถวเดียวมี Absolute Error เพิ่ม 240.54 กก./ไร่ คิดเป็น +5.35 ต่อ MAE รวม 45 แถว เทียบกับการแย่ลงสุทธิ +6.97
นี่คือการแยกองค์ประกอบทางเลขคณิต ไม่ใช่เหตุผลให้ตัดแถวนี้ทิ้ง และไม่ใช่คำอธิบายเชิงสาเหตุ

### 2. Distribution Shift มีทั้งระหว่างจังหวัดและตามเวลา

ใช้ Sealed annual.csv ที่ Phase 6B อ้างผ่าน input_snapshot ของ Phase 6A ไม่ดาวน์โหลดหรือเปลี่ยน Dataset
Target = production_tonnes × 1,000 / bearing_rai; 170 จังหวัด–ปี 2009–2025 ไม่มี Key ซ้ำหรือ Target ขาด
สูตรตรง Target ที่ประเมินทุกแถว ภายใน Floating-point Tolerance

| ช่วง / กลุ่ม | n | Mean | Median | SD | Min–Max |
|---|---:|---:|---:|---:|---:|
| 2010–2016 เดิม | 35 | 935.99 | 992.75 | 315.59 | 241.57–1,436.24 |
| 2010–2016 ใหม่ | 35 | 781.78 | 776.00 | 306.42 | 272.99–1,380.94 |
| 2017–2025 เดิม | 45 | 1,208.38 | 1,130.27 | 396.54 | 559.59–2,194.40 |
| 2017–2025 ใหม่ | 45 | 1,043.24 | 964.23 | 438.32 | 392.41–2,098.81 |

เป็นค่าเฉลี่ยจังหวัด–ปีน้ำหนักเท่ากัน ไม่ใช่ Yield รวมที่ถ่วงพื้นที่ ข้อมูล 2010–2016 ไม่ใช่ Training Set เดียวของทุก Fold เพราะ Training ขยายตามเวลา
กลุ่มใหม่มีระดับผลผลิตเฉลี่ยก่อน Outer ต่ำกว่าเดิม 154.21 กก./ไร่ แต่ไม่ได้ต่ำทุกจังหวัด: ระยองเฉลี่ย 1,256.03 ใกล้จันทบุรี 1,293.56 ขณะที่นครราชสีมาเฉลี่ย 448.98
ทั้งสองกลุ่มมี Mean สูงขึ้นในช่วง Outer ดังนั้นการรวมจังหวัดที่มี Level ต่างกันและการเปลี่ยน Level ตามเวลาเป็นคนละประเด็น ไม่ควรเรียกรวมว่า Climate Shift
การเพิ่มจังหวัดเพิ่มจำนวนแถว แต่ไม่ได้เพิ่มจำนวนปีอิสระ และแต่ละจังหวัดยังมี Annual Target เพียงปีละครั้ง

### 3. โมเดลจับการเปลี่ยนรุนแรงไม่ทัน และมี Compression บางพื้นที่

กำหนดกลุ่มเปลี่ยนรุนแรงเพื่อวินิจฉัยด้วย Q75 ของ |Yield ปีนี้−ปีก่อน| จากจังหวัดเดิมปี 2010–2016 = 220.70 กก./ไร่
ใช้เกณฑ์นี้กับ Outer โดยไม่เปลี่ยน Model Configuration และไม่สร้าง Feature ใหม่: 17/45 แถวเข้าเกณฑ์
B มี MAE 305.46 ในกลุ่มนี้ เทียบ 143.77 ในอีก 28 แถว; D = 333.55 เทียบ 137.91
SD ของ Predictions / SD ของ Actual แบบรวม = 0.820 สำหรับ B และ 0.813 สำหรับ D สอดคล้องกับการทำนายที่แปรผันน้อยกว่าจริง
แต่เมื่อแยกจังหวัด B มี Ratio ชุมพร 0.614 ขณะที่จันทบุรี 1.195 และศรีสะเกษ 1.245 จึงห้ามสรุปว่า CatBoost บีบค่าทุกจังหวัดเสมอ

เทียบกับ Q25/Q75 ของ Yield แต่ละจังหวัดจาก 2010–2016: Outer ต่ำกว่า Q25 มี 6 แถว B Bias +236.44 และ D +181.86
สูงกว่า Q75 มี 32 แถว B Bias -132.22 และ D -124.89; กลางช่วงมี 7 แถว
นี่เป็นหลักฐานเชิงพรรณนาของ Tail Bias ไม่ใช่การพิสูจน์กลไก Regression-to-Mean โดยเฉพาะเมื่อช่วง Outer มี Upward Shift
Correlation แบบรวมระหว่าง Yield กับ Absolute Error = 0.446/0.489 สำหรับ B/D แต่ใน B สุราษฎร์ธานีเป็น -0.532 ขณะที่ชุมพร +0.703
ทิศทางจึงขึ้นกับจังหวัด การรวมข้อมูลอาจกลบรูปแบบจริง และ Correlation ที่ใช้ Actual กับ Error ไม่ใช่หลักฐานอิสระเชิงสาเหตุ

| กรณี | Actual | YoY | Prediction B / D | Error B / D |
|---|---:|---:|---:|---:|
| ชุมพร 2019 | 1,759.64 | +708.20 (+67.36%) | 1,019.30 / 1,078.69 | -740.33 / -680.95 |
| จันทบุรี 2022 | 2,194.40 | +351.59 (+19.08%) | 1,727.78 / 1,487.24 | -466.62 / -707.16 |
| จันทบุรี 2024 | 1,519.58 | -448.13 | 1,912.71 / — | +393.13 / — |

เครื่องหมาย — หมายถึงไม่ได้แสดงค่าของแขน D ในแถวนี้ ไม่ใช่ Prediction ขาด
ปี 2019 B Bias รวม -210.86 แต่ปี 2024 +213.71: โมเดลพลาดทั้ง Upward และ Downward Shock
Phase 2 Ridge RMSE 258.03 ต่ำกว่า CatBoost 266.47 แม้ MAE สูงกว่า และ Phase 5B ENSO MAE 213.97 แย่กว่า Weather 204.85
จึงไม่มีหลักฐานว่าตระกูล CatBoost หรือการเพิ่ม Climate Input จะชนะทุก Metric/ทุกพื้นที่

### 4. Capacity และ Encoding: มีข้อจำกัด แต่ยังแยกสาเหตุไม่ได้

Snapshot ระบุใช้ Province Indicators + Year + Lag Yield ไม่ใช่ตัวเลขรหัสจังหวัดที่ตีความเป็นอันดับ และไม่ได้ใช้ Native Categorical Province Embedding
5→10 จังหวัดเพิ่ม Design Columns No Weather 7→12 และ Weather 14→19 ขณะที่ Grid ยัง Depth 2/3, 400 Iterations, lr .03, l2 10, RMSE, Ordered, Seed 42
Indicators บอกเอกลักษณ์จังหวัด แต่ไม่เข้ารหัสความใกล้เคียงทางภูมิอากาศ และไม่ได้รับประกันว่าจะเรียน Interaction เฉพาะทุกจังหวัดได้
Earliest Inner มี 20/40 Training Rows สำหรับ 5/10 จังหวัด แต่ต่อจังหวัดยังมีเพียง 4 ปี
Training Objective ของ 10 จังหวัดรวมจังหวัดใหม่ ขณะที่ Inner Selection Objective ยังประเมิน 5 จังหวัดเดิม จึงเป็นการเปลี่ยน Distribution ของการ Fit ไม่ใช่แค่เพิ่มตัวอย่างชนิดเดิม

Depth B ปี 2017–2025 = 3,3,3,2,2,2,2,2,2; D = 3,3,3,3,3,2,3,3,3 ต่างกัน 5/9 ปี
ผล B→D จึงรวมผลของ Training Cohort และการเลือก Depth ใหม่ภายใต้ Protocol เดิม ไม่สามารถแยกเป็น Pure Pooling Effect ได้
ยังไม่มี Leaf/Split Diagnostics หรือ Fixed-depth Counterfactual ที่พิสูจน์ว่า Capacity ไม่พอ ห้ามอ้าง Underfitting เป็นข้อยุติหรือเพิ่ม Depth ตาม Outer Errors

### 5. สัญญาณอากาศปลายฤดูถูกแทนด้วย Climatology มาก

คำนวณจาก Actual-consumption Lineage ของ 5 จังหวัดเดิมปี 2017–2025:

| Weather Feature | Observed Fraction เฉลี่ย | Climatology Fraction |
|---|---:|---:|
| Pre-bloom Rain และ Pre-bloom VPD | 98.19% | 1.81% |
| Fruit 0–29 Rain และ Early VPD | 64.82% | 35.18% |
| Fruit 30–59 Rain | 32.14% | 67.86% |
| Fruit 60–89 Solar | 3.81% | 96.19% |
| Fruit 90–Harvest Temperature | 0.00% | 100.00% |

Fraction นับ Cells ใน Harvest-cohort × Stage-window Matrix ไม่ใช่ร้อยละวันไม่ซ้ำหรือ Forecast Accuracy
ตัวอย่างจันทบุรี 2023 Builder เฉลี่ย 91 Harvest-cohort Days; ใช้ Fruit Solar Observed 105 จาก 2,730 Cells
ดังนั้น Input ไม่ใช่ Phenology ของสวนหนึ่งแปลงที่ทราบวันดอกบานจริง และการเฉลี่ยข้าม Cohorts อาจลดความชัดของเหตุการณ์สั้น ๆ
Climatology ใช้ Calendar-day Normals จาก 10 ปีก่อน ไม่ใช่ Historical Weather Forecast และไม่ทราบ Shock ปลายฤดูของปีเป้าหมาย
One Weather Reference Grid ต่อจังหวัด ไม่มี Bearing-orchard Weights; ยังวัดไม่ได้ว่าการคลาดเชิงพื้นที่หรือเชิงระยะผลมีส่วนต่อ Error เท่าใด
Phase 3 Weather Gain เพียง 2.60 กก./ไร่ เป็น Contribution ของ Pipeline ที่เลือก Depth แยก ไม่ใช่ผลเฉพาะ VPD หรือหลักฐานเชิงสาเหตุ

### 6. พื้นที่ให้ผลเปลี่ยนมาก และ Historical Vintage ยังเป็นช่องว่าง

ช่วง Outer Bearing-area YoY Median เดิม +6.42% ใหม่ +8.04%; สูงสุดกลุ่มใหม่ +294.30% (นครราชสีมา 2019 จาก 316 เป็น 1,246 ไร่)
ก่อน Outer ระนอง 2014 เพิ่ม +224.64%; ศรีสะเกษ 2022 เพิ่ม +72.50% แต่ Yield เปลี่ยนเพียง +0.74%
จึงไม่สามารถใช้การเพิ่มพื้นที่อธิบายการเปลี่ยน Yield ตรง ๆ: Yield Ratio = Production Ratio / Bearing-area Ratio
ชุมพร 2019 Production +79.44%, Bearing Area +7.22%, Yield +67.36%; จันทบุรี 2022 = +29.98%, +9.15%, +19.08%
Annual Aggregate แยกต้นเริ่มให้ผล/อายุสวน/พันธุ์/การจัดการไม่ได้ และพื้นที่ให้ผลไม่ใช่ Predictor ในแขนนี้ แต่เป็นตัวหารของ Target และ Lag
ข้อมูลฉบับปรับปรุงอาจเปลี่ยนทั้ง Numerator/Denominator/Training Labels/Baseline โดยไม่มี Historical Vintage ให้แยกการเปลี่ยนจริงออกจาก Revision
ไม่ตีความ Area Jump ว่าเป็นข้อมูลผิด ไม่ตัดแถว และไม่ยกระดับ PIT Status

## Hypotheses — ลำดับความสำคัญ

ลำดับนี้จัดงานตรวจ ไม่ใช่การเลือก Configuration จาก Outer Scores; โอกาสช่วยเป็นการประเมินเชิงคุณภาพ ยังไม่ใช่ผลทดลอง

| ลำดับ / สมมติฐาน | หลักฐานปัจจุบัน | ความเสี่ยง / ต้นทุนตรวจ | โอกาสช่วย |
|---|---|---|---|
| 1. Global Level Target ผสมระดับจังหวัดและจับ YoY Shock ไม่ทัน | Pre-Outer Level ต่างกัน; Tail Bias และ Severe-change Errors สูง | ต่ำ–กลาง / ต่ำ หากทดสอบ Target Transform เดียว | มีเหตุผลให้ทดสอบ แต่ไม่รับประกัน |
| 2. Late-season Inputs ไม่มีสัญญาณปีเป้าหมายมากพอ | Solar 96.19%, Late Temperature 100% เป็น Climatology | สูงด้าน Vintage / สูงสำหรับ Historical Forecast | อาจช่วย แต่ข้อมูลและ PIT ยังไม่พร้อม |
| 3. Pooling + Indicators + Capacity มี Negative Transfer บางจังหวัด | Expansion เสียทั้งมี/ไม่มี Weather และ Depth เปลี่ยน | Overfitting สูง / กลาง; แยกภูมิภาคลดจำนวนแถวอีก | ยังไม่ยืนยันจาก Tree Diagnostics |
| 4. Target Composition/Revision และ Bearing-area Dynamics | Area Jumps; Target คำนวณจากอัตราส่วนฉบับปัจจุบัน | Historical Evidence ขาด / สูง | เพิ่มความน่าเชื่อถือได้ ไม่รับประกัน MAE ลด |
| 5. Spatial/Phenology Averaging ซ่อนเหตุการณ์และการจัดการสวน | One-grid, Cohort Averaging, Fixed-age Proxy | ต้องข้อมูลแปลง / สูง | ยังประเมินไม่ได้จาก Artifacts นี้ |

## Evidence Gaps

- ไม่มี Historical OAE/POWER Vintages ที่พิสูจน์ข้อมูล ณ Issue/Fit Cutoff ครบ จึงแยก Revision Bias จากความผิดพลาดโมเดลไม่ได้
- ไม่มี Ground Truth วันดอกบาน พันธุ์ อายุสวน ระบบน้ำ หรือ Orchard Mask ที่ใช้ทดสอบคำอธิบายเชิงชีววิทยา ห้ามอนุมานจาก Province Residual
- ไม่มี Model Dumps/Leaf Audit หรือการทดลองตรึง Depth คู่กันเพื่อแยก Pooling ออกจาก Selection Effect
- 45 แถวไม่ใช่ 45 ตัวอย่างอิสระ: มีจังหวัดซ้ำ ปีร่วมกัน และ Inner Windows ซ้อนกัน ไม่อ้าง Significance
- Outer 2017–2025 ถูกดูซ้ำในการพัฒนา ไม่ใช้ผลนี้เลือก Region Routing, Weighting, Grid หรือ Target-transform ผู้ชนะ

## Recommended Next Experiment

เสนอเพียง **หนึ่งการทดลองหลังอนุมัติ**: Global Level vs Global Year-over-year Delta Target โดยคง 10 จังหวัดและ Weather Inputs ของ Phase 6B D ทั้งหมด
เปลี่ยนเพียง Target: Delta = Yield ปีเป้าหมาย − Lag Yield; Reconstruction = Lag Yield + Predicted Delta
คง Calendar, Cutoffs, Evaluation Keys, Depth 2/3, Seed และ Inner Objective เดิม ไม่เพิ่ม Feature/ENSO/จังหวัด และไม่คัดจังหวัดตาม Outer Scores
Motivation จาก Pre-Outer: Delta Mean เดิม/ใหม่ -13.30/-14.81 และ SD 200.49/167.31 ต่างกันด้าน Level น้อยลงหลังเปลี่ยน Target แต่ยังไม่พิสูจน์ว่าทำนายดีขึ้น

ต้องเตรียม Signed-target Path แยกใน Experimental เท่านั้นเมื่อได้รับอนุมัติ: Helper เดิม Clamp Predictions ที่ศูนย์ ซึ่งห้ามใช้ Clamp กับ Delta ติดลบ
ตรวจ Lag และ Label Availability ทั้งสองปีทุก Fold; Clamp Yield ที่ Reconstruction หากใช้ต้องประกาศไว้ก่อน ไม่แก้ Shared Production Helper
เปรียบเทียบกับ Level Reference ภายใต้ Protocol เดียวกัน เลือก Depth จาก Inner แยกแขน ห้ามเลือก Delta/Level จาก Outer ที่เห็นแล้ว

เกณฑ์หยุดที่เสนอให้ล็อกก่อนเริ่ม: หยุดทันทีเมื่อ Hash/Keys/Cutoff/Lineage ไม่ผ่าน; ไม่ตัดแถวหรือเติมอนาคต
หยุดการพัฒนาวิธี Delta หลังหนึ่งรอบ หาก Aggregate Inner MAE ลดไม่ถึง 5%, Inner RMSE แย่ลง หรือ Inner MAE ของจังหวัดเดิมใดแย่เกิน 10% เทียบ Level
คำนวณ Aggregate บน Protocol-defined Inner Contexts เท่ากันทั้งแขน แจ้งว่า Validation Rows ซ้ำระหว่าง Contexts ไม่ใช้เป็น Independent Significance Test
5%/10% เป็นเกณฑ์ใช้งานที่เสนอ ไม่ใช่ Threshold ที่ข้อมูลพิสูจน์แล้ว ต้องอนุมัติ/ล็อกก่อน Training ไม่เปลี่ยนตามผล และไม่ขยาย Grid เมื่อไม่ผ่าน
แม้ผ่าน Inner และรายงาน Outer ได้ ก็ยังเป็น Exploratory ต้อง Preregister และรอปีเป้าหมายใหม่ที่ยังไม่เห็นก่อนอ้างประสิทธิภาพยืนยัน ไม่แทน Production อัตโนมัติ

Global Modeling ทำต่อได้ด้วยจำนวนแถวเดิมและ Shared Learning แต่เสี่ยง Negative Transfer
Regional Modeling ยังไม่เสนอเป็นรอบฝึกถัดไป: 10 จังหวัดมี East/NE/North/West/South = 2/2/1/1/4 จังหวัด
Earliest Inner Training ของ Regional Models จะมีเพียง 8/8/4/4/16 แถว ไม่เพิ่มจำนวนปีและเสี่ยง Selection Variance มาก
หากจะพิจารณาภายหลัง ต้องกำหนด Region Membership จากข้อมูลภายนอก/นิยามเดิมก่อนประเมิน และทำ Sample-size Feasibility Gate ไม่แบ่งพื้นที่ตาม Outer Winners/Losers

## หลักฐานและ Integrity Checks

อ่านรายงาน Phase 2/3/5B/6B และ Predictions, Choices, Config, Fit Audit, Source Snapshots/Lineage ที่เกี่ยวข้องเท่านั้น
ใช้ annual.csv/feature_lineage.json จาก Sealed Input ที่ Phase 6B อ้างโดยตรง ไม่สำรวจ Dataset ใหม่
คำนวณด้วย Bundled Python/pandas แบบ Read-only ไม่ Import Estimator ไม่ Fit หรือสร้าง ML Artifacts
Weather Predictions ของ Phase 2 → 3 → 5B → 6B B ตรงกันทั้ง 45 Keys (Maximum Absolute Difference = 0)
จึงไม่ใช่การทดลองอิสระสี่ครั้ง และไม่พบ Reference-prediction Drift จากหลักฐานนี้
ตรวจ Lineage 1,280 Records: Observed/Normal Source Dates ไม่เกิน Weather Available-through ของแถวนั้น แต่ไม่ได้รับรอง Publication/Vintage หรือ Replay Guard ทุก Fold ใหม่ในงานนี้

ตรวจ SHA256 ก่อนและหลังสร้างรายงาน: Protected 749 Entries, Phase 6A Inputs 57 Entries และ Sealed Run Inventories Phase 2/3/5B/6B จำนวน 18/32/105/23 Entries ตรงทั้งหมด (อาจมีไฟล์ซ้ำระหว่าง Inventories)
Production SHA256 คงเดิม:
`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

Diagnostic Source SHA256:

- annual.csv: `41cb083c253c95469819c66fe945a56a9ba5c18d6e1885521b2e5cc37a66f7d3`
- feature_lineage.json: `69b2ac919f6c97c598504d35940b07ea96baecfb2672e2c2b4239a04087a5803`
- Phase 6B predictions.csv: `a8e1ff61530a8f020544e6e4fbf9f6114264fe199dd6bc24e5a3cbdc3cbeabc9`

Source directories อยู่ใต้ `research_data/five_province_history/training/`:
Phase 2 `rebaseline_exploratory/20261010T131023246729Z/`; Phase 3 `weather_ablation_exploratory/20261011T122324056845Z/`;
Phase 5B `enso_state_preparation_exploratory/phase5b_20261011T132904962005Z/`; Phase 6B `province_expansion_exploratory/phase6b_20261011T140737783448Z/`
Input snapshot: `research_data/province_expansion_inputs/phase6a_20261011T134340704642Z/`

เปลี่ยนเพียงรายงานใหม่นี้ รักษา Dirty/Untracked เดิม ไม่รัน Repository Tests ซ้ำเพราะไม่มี Code Change และไม่ถือ Hash/Test Pass ว่าปราศจาก Leakage
หยุดรออนุมัติ ไม่เริ่ม Training หรือการทดลองอื่น
