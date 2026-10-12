# Phase 8A — Durian Forecast Readiness & Data Gap Review

วันที่ 12 ตุลาคม 2026 (Asia/Bangkok) — Audit only; หยุดการทดลองไล่ MAE
ใช้รายงานและ Sealed Artifacts เดิม ไม่ฝึก/จูน ไม่เพิ่ม Inputs ไม่แก้ Production/API/Frontend
Historical PIT ยังไม่รับรอง; ข้อเสนอด้านเว็บและการเก็บข้อมูลด้านล่าง **ยังไม่ได้ Implement**

## 1. ข้อสรุปความพร้อม

ระบบมีความพร้อมด้าน **การทดลองย้อนหลังที่ตรวจสอบย้อนกลับได้** มากกว่าด้าน **พยากรณ์ล่วงหน้าที่รับรองข้อมูลตามเวลา**
ข้อจำกัดไม่ได้มีเพียงชนิดโมเดล: มีทั้งข้อมูลอากาศอนาคตที่แทนด้วย Climatology, รุ่นข้อมูล OAE/POWER ที่ยังยืนยันไม่ได้ และปีทดสอบเก่าที่ถูกใช้วิเคราะห์ระหว่างพัฒนาหลายครั้ง
หยุดเพิ่มความซับซ้อนของ ML ชั่วคราวเหมาะสม; งานถัดไปควรสร้างหลักฐานจากการออกพยากรณ์จริง ไม่ใช่เลือกผู้ชนะใหม่จาก Outer เดิม

| ระดับใช้งาน | ความพร้อม | ขอบเขตที่อนุญาตให้สื่อสาร |
|---|---|---|
| Historical Analysis | พร้อมแบบมีข้อจำกัด | แสดงข้อมูลย้อนหลังฉบับที่ใช้จริง, ปี/จังหวัด/หน่วย/รุ่นข้อมูล และผลทดลองย้อนหลัง ไม่อ้างคะแนนเป็น Lead-60 ที่รับรอง PIT |
| Experimental Forecast | พร้อมด้าน Protocol; ยังต้องตรวจระบบออกพยากรณ์จริง | ใช้ Shadow/Research output หลังผ่าน As-of input preflight และอนุมัติ Candidate ที่ตรึงไว้; แสดงสถานะทดลองและ Climatology อย่างชัดเจน |
| Verified Forecast | ยังไม่พร้อม | ต้องยืนยัน Inputs/Labels/Rule ณ Cutoff และมีบันทึกออกจริง; ความถูกต้องตามเวลายังไม่เท่ากับความแม่นที่ยืนยันด้วยปีใหม่ |

คำว่า Verified ควรแยกสองแกน: **ตรวจสอบข้อมูล ณ เวลาออกแล้วหรือไม่** และ **ประสิทธิภาพบนปีใหม่ผ่านเกณฑ์หรือไม่** ไม่ใช้ Badge เดียวแทนทั้งสองเรื่อง
Production ปัจจุบันเป็น Ridge VPD แบบใช้หน้าต่างอากาศครบฤดู; Contract ระบุ Demo ใช้ Observed weather ไม่ใช่ Live forecast
MAE 190.87 ของงานครบฤดูจึงไม่ใช่คะแนนการใช้งานก่อนฤดู 60 วัน และไม่เทียบตรงกับคะแนนด้านล่าง
ไม่มีการเลือก/Promote Experimental model ใน Audit นี้ และไม่ได้ตรวจ Live serving, Login หรือการเชื่อม Supabase รอบนี้
ML รายจังหวัดรายปีไม่ใช่โมเดลผลผลิตสวนรายแปลง และไม่สามารถบอกระยะผลจริงของสวนจากผลผลิตจังหวัดได้

## 2. ผล Phase 2–7: แยก Outer และ Inner

### Outer Exploratory: 2017–2025

Primary ทุกแถวด้านล่างใช้ 45 Keys ของจันทบุรี ศรีสะเกษ อุตรดิตถ์ สุราษฎร์ธานี และชุมพร
หน่วย MAE/RMSE/Bias = กก./ไร่; Bias = ทำนาย − จริง; ไม่ใช่ PIT Certified หรือ Independent final holdout

| Phase / แขน | Cohort ฝึก | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| 2 Last-year | 5 | 215.51 | 269.55 | -44.41 |
| 2 Ridge | 5 | 212.20 | 258.03 | -27.48 |
| 2 CatBoost Weather / 3 With Weather / 5B Weather / 6B B | 5 | 204.85 | 266.47 | -59.53 |
| 3 No Weather / 6B A | 5 | 207.45 | 267.01 | -60.92 |
| 5B Weather + Observed ENSO State | 5 | 213.97 | 272.01 | -47.00 |
| 6B C No Weather | 10 | 230.58 | 280.92 | -59.21 |
| 6B D With Weather | 10 | 211.82 | 270.11 | -64.91 |

คะแนนซ้ำของแขนอ้างอิงเป็นการตรวจ Reproduction ของ Protocol ไม่ใช่หลักฐานทดลองอิสระเพิ่มหลายชุด
Phase 2 CatBoost เทียบ Last-year ลด MAE 4.95% แต่ Ridge มี RMSE ต่ำกว่า และ CatBoost แย่กว่า Last-year ที่จันทบุรี/ชุมพร
Phase 3 Weather gain 2.60 (1.25%), ชนะ/เสมอ/แพ้ 27/0/18; ไม่ได้พิสูจน์ผลเฉพาะ VPD หรือความสัมพันธ์เชิงสาเหตุ
Phase 5B ENSO gain -9.12, ชนะ/เสมอ/แพ้ 18/0/27; ไม่ช่วย MAE รวมภายใต้การทดลองนี้
Phase 6B เพิ่มจังหวัดทำให้ MAE Primary แย่ลง 23.13 เมื่อไม่มีอากาศ และ 6.97 เมื่อมีอากาศ; With Weather ชนะ/เสมอ/แพ้ 16/0/29
Secondary จังหวัดใหม่ 45 Keys: C = 178.61/228.66/-50.01 และ D = 171.58/217.64/-34.70 (MAE/RMSE/Bias)
Secondary ไม่มีแขนฝึก 5 จังหวัดที่เป็นคู่เทียบ จึงไม่อ้างว่าการเพิ่มจังหวัดช่วยกลุ่มใหม่จากคะแนนเหล่านี้

### Inner Validation และ Phase 7B

Phase 2/3/5B/6B ใช้ Inner 3 ปีก่อนแต่ละ Outer เลือกพารามิเตอร์ภายในแขน; ตัวเลขตารางข้างบนเป็น Outer ไม่ใช่ Selection score
Phase 4/5A/6A/7A เป็น Audit/Preparation ไม่มีผล Training ใหม่; Phase 7A เป็น Diagnosis หลังเห็น Outcomes ไม่ใช่การยืนยันสาเหตุ

| Phase 7B Inner เท่านั้น | Level | Signed Delta |
|---|---:|---:|
| MAE | 206.28 | 208.29 |
| RMSE | 262.57 | 274.34 |
| Bias | -54.91 | +16.46 |
| P90 Absolute Error | 420.10 | 442.89 |

135 Context-rows/แขน แต่มี 55 จังหวัด–ปีไม่ซ้ำ (2014–2024), นับซ้ำ 80 แถว; ไม่ใช่ 135 ตัวอย่างอิสระ
เลือก Depth และตรวจ Gate บน Inner เดียวกัน จึงมี Selection Optimism
MAE improvement -0.97%, RMSE แย่ลง และ MAE ศรีสะเกษ/อุตรดิตถ์แย่เกิน 10%: Inner Gate ไม่ผ่าน
**หยุด Delta และไม่ได้ Fit/Evaluate Outer** ห้ามเทียบ 206.28/208.29 กับ Outer 204.85 เพื่อจัดอันดับโมเดล

## 3. อากาศที่ทราบ ณ Issue Date: สิ่งที่ขาดจริง

Phase 7A ตรวจ Actual-consumption Lineage ของ 5 จังหวัดเดิมใน Outer ได้สัดส่วนดังนี้:

| หน้าต่าง / Features | Observed | Climatology |
|---|---:|---:|
| Pre-bloom Rain / VPD | 98.19% | 1.81% |
| Fruit 0–29 Rain / Early VPD | 64.82% | 35.18% |
| Fruit 30–59 Rain | 32.14% | 67.86% |
| Fruit 60–89 Solar | 3.81% | 96.19% |
| Fruit 90–Harvest Temperature | 0.00% | 100.00% |

นี่คือ Cells ใน Harvest-cohort × Stage-window Matrix ไม่ใช่ร้อยละวันไม่ซ้ำหรือความแม่นพยากรณ์
Climatology ใช้ Calendar-day normals จาก 10 ปีก่อน; ไม่ใช่ Reanalysis ของปีเป้าหมายหรือ Historical forecast ที่ออกจริง
จึงไม่มีข้อมูลเฉพาะปีของ Shock ปลายฤดูใน Features ที่ใช้ Climatology เกือบทั้งหมด
Observed ก่อน Cutoff ก็ยังมีปัญหา Vintage: ค่าที่ดาวน์โหลดปัจจุบันอาจต่างจากค่าที่เคยเผยแพร่ ณ Issue Date
Lag อากาศ 7 วันเป็น Policy ไม่ใช่หลักฐานว่าทุกรายการเผยแพร่ทันทุกปี; Climatology เองต้องตรวจ Vintage ของข้อมูลต้นทางด้วย
One reference grid/จังหวัด และหน้าต่างอายุผลสมมุติที่เฉลี่ยหลาย Cohorts อาจลดสัญญาณพื้นที่/เหตุการณ์สั้น; ยังวัดส่วนแบ่งของ Error ที่เกิดจากแต่ละกลไกไม่ได้
Seasonal monthly rainfall/temperature forecast ไม่สามารถแทน Daily rain events, Radiation หรือ VPD P90 ได้โดยตรง ต้องมีแผนแปลงและ Validation แยกก่อนเพิ่ม Feature

## 4. Vintage และ Issue-rule gaps

- OAE annual snapshot มี `data_date` 2026-07-14 และ CKAN resource timestamps สิงหาคม 2026 แต่ยังพิสูจน์วันเผยแพร่/Revision ของแต่ละจังหวัด–ปีไม่ได้ วันที่ไฟล์/ดึงข้อมูล/ลง Catalog ไม่ใช่ Historical publication date โดยอัตโนมัติ
- Yield เป็น Production / Bearing area: Revision ของทั้งเศษและส่วนกระทบ Target, Lag และ Labels; ฉบับปรับปรุงใช้ Evaluation truth ภายหลังได้ แต่ไม่ได้รับอนุญาตเป็น Input ณ อดีตโดยปริยาย
- Training/Selection labels ต้องมีจริงก่อน Shared fit cutoff ไม่ใช่แค่ Year น้อยกว่า Outer; Last-year baseline มีความเสี่ยง Vintage เช่นเดียวกับ ML
- Fixed-calendar สร้างในปี 2026 ไม่ใช่หลักฐานว่าประกาศก่อน 2017; ทราบจากนิยามไม่เท่ากับ Historical rule verification
- เดิมกำหนด Anchor เดิมห้าจังหวัดเป็น 04-01/05-01/06-01/07-01/07-01 แล้วลบ 60 วัน; Shared fit cutoff คือ Issue แรกสุดของกลุ่มเวลา 00:00 ไทย ต้องไม่แก้ตามผลผลิต/ฤดูจริงภายหลัง
- NOAA archive ยืนยันวันที่ออกเอกสารก่อน Cutoff ได้ แต่ Audit มี Archived-content authenticity unverified 100%: SHA ของไฟล์ที่ดึงปี 2026 พิสูจน์ Bytes ที่ใช้ตอนนี้ ไม่พิสูจน์ว่าไม่เคยแก้ย้อนหลัง
- ENSO State เป็น Observed state ใน Bulletin ไม่ใช่พยากรณ์อากาศจังหวัด; Revised ONI ไม่ใช่ Vintage และห้ามเติม Probability vector ที่ยังไม่ตรวจครบ
- Climate feasibility audit พบ NMME realtime เริ่ม 2011 กับ Hindcasts 1982–2010 และ C3S hindcast/forecast ต่างช่วง/ระบบ; Hindcast ที่สร้างภายหลังไม่ใช่ Realtime vintage ของวันในอดีต

ข้อความเกี่ยวกับ Archive coverage มาจาก Audit เดิมวันที่ 10–11 ตุลาคม 2026 ไม่ได้ตรวจผู้ให้บริการใหม่ในงานนี้
ต้องแยก Initialization date, Publication date, Valid period, Retrieval time และ Source/system version ไม่ใช้ชื่อเดือนหรือ Directory timestamp แทนหลักฐานปล่อยข้อมูล
Availability Guard ลดการใช้ผิดเงื่อนไข แต่ไม่ Authenticate หลักฐานหรือสร้าง Historical vintages ที่ไม่มีอยู่; Tests/Hashes ผ่านไม่ได้รับรอง PIT

## 5. สิ่งที่ผู้ใช้ควรเห็นบนเว็บ (ข้อเสนอเท่านั้น)

หน้า Historical แสดงว่าเป็นข้อมูลย้อนหลังฉบับปรับปรุง พร้อมช่วงประเมินและจำนวนจังหวัด–ปี
หน้า Forecast แยกชัดจาก Historical โดยแสดงจังหวัด/ปี/หน่วย, Issue และ As-of cutoff, Model version, สถานะ Experimental, วันอัปเดตต้นทาง และส่วนที่เป็น Observed/Climatology/Forecast จริง
ข้อความตัวอย่าง: “พยากรณ์ทดลองระดับจังหวัด — อากาศอนาคตบางช่วงใช้ค่าปกติย้อนหลัง ยังไม่ยืนยันความแม่นบนปีใหม่”
หาก Input ขาด/เก่า/ไม่มีหลักฐาน ให้แสดง “ยังออกพยากรณ์ไม่ได้” พร้อมสาเหตุ ไม่แสดงศูนย์หรือใช้อนาคตเติมเงียบ ๆ
MAE/RMSE/Bias และ Error รายจังหวัดแสดงเป็น **สถิติย้อนหลังเชิงพรรณนา** มีช่วงปีและ n กำกับ ไม่ใช่ Confidence/Predictive interval ของปีนี้
ไม่ใช้ ±MAE เป็นช่วง 95%, ไม่สร้างโอกาสผลผลิตลด/ความน่าจะเป็นภัยแล้ง หรือ Band ที่ไม่มี Calibration
เมื่อมี Residuals ของการออกจริงเพียงพอจึงเสนอ Interval protocol ใหม่ โดยตรวจ Dependence/พื้นที่/ฤดูกาลและ Out-of-sample coverage ก่อน
ข้อมูลสดสวนจาก Sensor แสดงสถานะ/เวลา/ข้อมูลขาดแยกจาก ML จังหวัด; ไม่บอกว่าระยะผลหรือผลผลิตสวนผ่านการสอบเทียบแล้ว
การแปลง กก./ไร่ เป็นตันต้องมี Bearing area ที่ทราบ ณ Issue; พื้นที่จริงภายหลังใช้ประเมินย้อนหลัง ไม่เขียนทับสมมติฐาน Forecast ที่ออกไป

## 6. แผนเก็บการออกพยากรณ์จริงแบบ Prospective

สร้าง Offline append-only ledger แยกจาก Production หลังอนุมัติงานใหม่; ยังไม่สร้างในรอบนี้
ต่อ Forecast เก็บ `forecast_id`, province, target_year, planned_issue_date, issued_at, shared_fit_cutoff, model_version/artifact_hash, protocol/config/code_hash และ Prediction หน่วย กก./ไร่
ต่อ Input เก็บ Source/version, Publication evidence/date/timezone, Retrieval time, Bytes SHA256, Observation/Forecast valid period, Provider initialization/release time, Role และ Availability status
เก็บ Feature Lineage ที่ใช้จริง, Training/Selection label vintages, Lag yield vintage, Normal-year set/Climatology fraction, Dependencies และ Missing-data reasons
ก่อน Issue ตรวจ Schema/Coverage/Cutoff/Encoding และ Availability; ห้ามใช้ Dataset ฉบับที่ยังไม่เผยแพร่ให้ครบด้วยข้อมูลภายหลัง
หากไม่ผ่านให้บันทึก “no forecast issued” ไม่ลบกรณีนี้จากตัวหาร Coverage; Forecast ที่ออกช้าต้องแยก ไม่อ้างว่าเป็น Lead-60 ตรงเวลา
เก็บ Output/Inputs ณ เวลาออกแบบไม่ทับ; Revised forecast ต้องมี ID/Version ใหม่ผูก Original พร้อมเหตุผล ไม่แก้ประวัติ
เมื่อ OAE ประกาศ เก็บ First-release actual และ Later revised actual แยก พร้อมวันที่/หลักฐาน/Hash; ตรึง Scoring truth policy ก่อนเห็น Outcomes และรายงาน Sensitivity ต่อ Revision
Baseline Last-year ต้องใช้ Vintage ที่มีจริง ณ Issue เช่นเดียวกัน; หากไม่มีให้รายงาน Unavailable ไม่ใช้ Revised label มาแก้ Baseline ภายหลัง
การ Freeze Candidate/การ Refit สำหรับปีใหม่ต้องขออนุมัติแยก; Audit นี้ไม่เลือก Candidate ใหม่จาก Outer เดิม และไม่อนุญาต Training อัตโนมัติ

## 7. จัดอันดับ Data gaps

อันดับเป็น Priorities สำหรับการลงทุนข้อมูล ไม่ใช่ผลทดลองยืนยันว่าช่วยลด MAE; ต้นทุนเป็นประมาณเชิงเปรียบเทียบ ไม่ใช่ราคาเสนอ

| อันดับ | Gap | คุณค่า / ความเป็นไปได้ / ต้นทุน |
|---|---|---|
| 1 | Prospective input/output vintages และ OAE release registry | สำคัญที่สุดต่อความน่าเชื่อถือ; เริ่มเก็บตั้งแต่ตอนนี้ได้; ต่ำ–กลาง ไม่ต้องตามหาอดีตทุกปีให้ครบก่อน |
| 2 | Seasonal rainfall/temperature forecast ที่ออกจริงก่อน Issue | มีศักยภาพเติมข้อมูลเฉพาะปีแทน Normals; ยังไม่พิสูจน์ Skill ทุเรียน; กลาง–สูง ต้องตรวจ Archive/Release/System/พื้นที่ก่อน |
| 3 | OAE historical releases ของ Yield/Bearing area และ Revision history | ตรวจ Lag/Training/Baseline และ Denominator ได้; ความครบถ้วนไม่แน่; กลาง–สูง ห้ามค้นแบบไม่มีขอบเขต |
| 4 | สัดส่วนพื้นที่ปลูก/ฤดูผลจริง และการจัดการน้ำ | อาจลด Spatial/Phenological mismatch; ต้องสำรวจ/เชื่อมหน่วยพื้นที่; สูง ยังไม่เพิ่ม Feature ในรอบนี้ |
| 5 | Archived POWER vintages และความหน่วงจริง | ช่วยตรวจ Inputs/Normals ตามเวลา; มี SHA ปัจจุบันไม่พอ; กลาง–สูงและย้อนหลังอาจกู้ไม่ได้ |

สำหรับการพยากรณ์ **สวนของผู้ใช้** ข้อมูลระยะดอก/ผล จำนวนผล การให้น้ำ และผลผลิตจริงรายแปลงมีความสำคัญต่อความเกี่ยวข้องมากกว่าการเพิ่มจังหวัด แต่ยังไม่ใช่หลักฐานว่าช่วยโมเดลระดับจังหวัด
เพิ่มจังหวัด/ENSO/Target transform ไม่ใช่ช่องว่างข้อมูลลำดับแรกแล้ว; ไม่กลับไปจูนจากผล Outer เก่า

## 8. ประเมินกับปีใหม่ที่ไม่เคยใช้พัฒนา

ณ 12 ตุลาคม 2026 Issue มกราคม–พฤษภาคมของปี 2026 ผ่านไปแล้ว จึงไม่ควรเรียกการออกย้อนหลังตอนนี้ว่า Prospective Lead-60
เสนอเริ่มปี 2027 หาก Freeze และเก็บ Inputs ทัน **ก่อน Issue แรก**; ไม่รับรอง Availability ของข้อมูลปีใหม่ล่วงหน้า
ตรึง Candidate ที่ผู้ใช้อนุมัติหนึ่งตัว, Last-year หนึ่ง Baseline, Protocol/Rule/Primary keys/หน่วย/Truth policy และเกณฑ์ก่อน Outcome แรก
Primary ใช้ห้าจังหวัดเดิม; หาก Candidate มี Cohort เดิมสิบจังหวัดให้ Secondary แยกตามที่อนุมัติ ไม่เพิ่มจังหวัดใหม่หรือรวมคะแนนเพื่อกลบ Primary
ห้ามใช้ผล 2017–2025 เลือก Candidate ใหม่ในขั้นนี้; การเปลี่ยนรุ่นเริ่มชุดประเมิน Prospective ใหม่และเก็บรุ่นเดิมไว้
ปี 2027 เพียงปีเดียวมี Primary 5 แถวที่สัมพันธ์กันตามปี เหมาะกับ Diagnostic ไม่ใช่การรับรองความแม่นทั่วไป
เสนอสะสมอย่างน้อย 3 ปีใหม่ (15 Primary จังหวัด–ปี แต่เพียง 3 Year blocks) และรายงาน MAE/RMSE/Bias, Paired errors, Worst error, รายจังหวัด/ปี, Coverage และ Revision sensitivity
เกณฑ์เสนอเพื่อขออนุมัติก่อนเริ่ม: Coverage ครบและ Cutoff ถูกต้องทุก Key; MAE ลด ≥5% เทียบ Last-year, RMSE ไม่แย่ลง และ MAE แต่ละจังหวัดไม่แย่ >10% บนชุดปีใหม่เดียวกัน
เกณฑ์เหล่านี้เป็น Decision gate ไม่ใช่ Statistical significance; สามปีต่อจังหวัดยังน้อย ต้องคงข้อจำกัดและไม่อ้าง CI/นัยสำคัญโดยไม่มีวิธีทดสอบที่เหมาะสม
หากข้อมูลไม่ทัน/ขาด ต้องรายงาน Protocol failure แยก ห้าม Drop keys ให้ผลดีขึ้น; หาก Performance gate ไม่ผ่านไม่ Promote และไม่จูนบนชุดยืนยันเดิม

## 9. งานถัดไปไม่เกินสองงาน และงบการทดลอง

**งาน 1 — Prospective Forecast Evidence Preparation**
เตรียม Ledger/Source registry/Issue calendar/As-of preflight แบบ Offline และออกแบบ Freeze request สำหรับ Candidate ที่มีอยู่; ไม่แก้ Production
รวมการตรวจวันเผยแพร่ OAE ของ Inputs ที่จะใช้ปีใหม่ ไม่ต้องรับรอง Historical vintages ทุกปีให้เสร็จก่อน
งบ: 1 Protocol, 1 Candidate ที่ต้องอนุมัติ + 1 Baseline; ขั้น Preparation **0 Fits / 0 Hyperparameter trials / 0 Forecast runs**
หลังอนุมัติการออกจริง แผนคือหนึ่ง Primary forecast ต่อจังหวัดต่อ Issue ที่กำหนด (5 ต่อปี), ไม่มีรันซ้ำไล่คะแนน; Secondary ต้องระบุใน Freeze request
หยุดก่อนออกหาก Lag/Labels/Weather vintage หรือ Feature contract ไม่พร้อม; หากต้อง Refit หรือเปลี่ยน Feature/Rule ให้ขออนุมัติ ไม่แก้เงียบ ๆ

**งาน 2 — Bounded Seasonal Forecast Vintage Pilot Audit**
เลือกหนึ่ง Archive family จาก Inventory เดิมด้วย Coverage/Access/Evidence ไม่ใช้ Yield scores; ตรวจ Rainfall/Temperature metadata และไฟล์จริงก่อนเสนอการทดลองใด ๆ
จำกัด Pilot ปี 2017/2020/2023/2025 × Issue dates ที่ไม่ซ้ำของห้าจังหวัด (4 ต่อปี) = 16 As-of selections; หลาย Keys ใช้ไฟล์เดียวได้ ไม่ใช่ 16 Downloads จำเป็น
งบ: 1 Source family, สูงสุด 16 Selections, **0 ML Fits / 0 Feature changes / 0 paid compute**; การเข้าถึงที่มีค่าใช้จ่ายต้องขออนุมัติ
หยุด Pilot หากไม่มี Publication evidence/Valid horizon/Version หรือไฟล์ต้องใช้ข้อมูลออกหลัง Issue; รายงาน Missing ไม่แทนด้วย Hindcast หรือ Climatology โดยปริยาย
Pilot ผ่านก็ยังไม่อนุญาต Train: ต้องเสนอ Full Train/Inner/Outer coverage audit ก่อน; หากต้นปี Train ขาด ห้ามเปลี่ยน Locked protocol ให้รันได้เอง

## 10. หลักฐานและ Integrity รอบนี้

อ่านรายงาน Phase 2/3/5B/6B/7A/7B, Availability/PIT และ Climate/ENSO archive audits เดิม พร้อม Production prediction contract
ก่อนเขียนรายงาน ตรวจ Protected hashes จาก Phase 7B config **778/778**, Postflight artifact hashes **20/20** และ Report hashes **2/2** ตรงทั้งหมด
หลังเขียนรายงานตรวจซ้ำ: Protected 778/778, Artifacts 20/20, Reports 2/2, Input 57/57 และ Code 6/6 ตรง; Manifest SHA ตรง `manifest.json` ของ Phase 6A
Production Hash ตรงเดิม; Git Status เพิ่มเพียงรายงานนี้ ไม่มี Status เดิมหายหรือเปลี่ยน; Hash ตรวจความคงเดิมของ Bytes ไม่รับรอง PIT
ผล Tests ล่าสุดใน Phase 7B Postflight: Python 279/279, JS 30/30 ไม่มี Failure/Skip; **ไม่ได้รัน Tests ใหม่ใน Audit-only นี้** เพราะไม่มีการแก้โค้ด
Production SHA256: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`
เพิ่มเฉพาะรายงานนี้ ไม่ทับ Artifacts ไม่แก้ไฟล์ Dirty/Untracked เดิม; ไม่มีการทดสอบ Skill ของ Seasonal forecast หรือการตรวจ Live API ในงานนี้

หลักฐานอ้างอิงใน Repository:

- `docs/DURIAN_REBASELINE_RESULT_TH.md`, `docs/DURIAN_WEATHER_ABLATION_RESULT_TH.md`
- `docs/DURIAN_ENSO_STATE_ABLATION_RESULT_TH.md`, `docs/DURIAN_PROVINCE_EXPANSION_RESULT_TH.md`
- `docs/DURIAN_ML_FAILURE_DIAGNOSIS_TH.md`, `docs/DURIAN_DELTA_TARGET_RESULT_TH.md`
- `docs/DURIAN_POINT_IN_TIME_AUDIT_TH.md`, `docs/DURIAN_AVAILABILITY_GUARD_TH.md`
- `docs/DURIAN_CLIMATE_SIGNAL_FEASIBILITY_AUDIT_TH.md`, `docs/DURIAN_ENSO_OUTLOOK_ARCHIVE_AUDIT_TH.md`
- Phase 7B `config.json` / `postflight.json` ใน `training/delta_target_exploratory/phase7b_20261011T170140373940Z/`
- `research_data/five_province_history/training/ridge_vpd_prediction_contract.json`

หยุดรออนุมัติ ไม่ดำเนินงาน 1/2 หรือ Training ต่อ
