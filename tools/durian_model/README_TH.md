# โมเดลผลผลิตทุเรียน: โค้ดขั้น 0-6 สำหรับ VS Code

## การตรวจ snapshot ข้าม Mac/Windows — 1 พฤศจิกายน 2569

`common.check_snapshot()` และการตรวจ input snapshot ของโมเดลในขั้น 6 ยอมรับไบต์ตรง SHA256 เดิมก่อน หากไม่ตรง จะยอมรับเฉพาะไฟล์ CSV input ทั้งสามที่ต่างเพียงการแปลง LF ↔ CRLF แบบสม่ำเสมอและเป็น UTF-8 โดย hash ของรูปแบบอีกด้านต้องตรงกับ digest ใน audit/โมเดลเดิมจริง ไม่ strip BOM, ช่องว่าง, แถวว่าง หรือแก้ตัวเลข และไม่ยอมรับ newline แบบผสม/CR เดี่ยวเป็นข้อยกเว้น

`hashes()` ยังคืน SHA256 ของไบต์จริงทุกครั้ง ส่วน `verify_input_snapshot(expected)` คืนหลักฐานต่อไฟล์ (`actual_sha256`, `expected_sha256`, `comparison` และรูปแบบ newline เมื่อมีการแปลงเพื่อเปรียบเทียบ) ไม่มีการเขียนทับ CSV, audit หรือโมเดล และเพิ่ม `.gitattributes` เฉพาะ CSV ทั้งสามเพื่อไม่ให้ Git แปลง newline เพิ่มใน checkout ใหม่ การแก้ปัญหานี้ไม่ต้องรันขั้น 0–6 หรือ train ใหม่

ดู [บันทึกแก้ไขและขอบเขต](../../docs/updates/SNAPSHOT_HASH_FIX_2026-11-01_TH.md) การตรวจ seal/hash ของ artifacts งานวิจัยอื่นยังเป็นแบบไบต์ตรงตามเดิม ไม่ได้รับการยกเว้นทั้งหมดโดยการแก้นี้

## Phase 1 — Rebaseline Preparation (ยังไม่ฝึกโมเดล)

อ่าน [แผนและผลตรวจ](../../docs/research/modeling/DURIAN_REBASELINE_PLAN_TH.md) ก่อนดำเนินการ
Phase 1 ไม่เรียก estimator; หลังอนุมัติ Phase 2 เพิ่ม `--train` แบบ opt-in ใน `experiment_rebaseline.py`
ค่าเริ่มต้นยังแสดง help เท่านั้น และ `--prepare` ยังคงไม่ฝึกโมเดล
ใช้ `--prepare` เพื่อสร้าง/audit Features และ 36 nested contexts แล้วเก็บ artifacts ใน
`training/rebaseline_exploratory/<run_id>/` โดยปฏิเสธชื่อซ้ำ ไม่ทับผลเดิม
คำสั่งนี้ไม่สร้าง MAE หรือเปลี่ยน Production แต่ต้องมี dependencies เดิมครบรวม CatBoost

```powershell
.build/national-analysis-venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -p test_rebaseline.py -v
```

ตรึง 5 จังหวัด, Lead 60, Fixed-calendar จาก Manifest เดิม และชุดพารามิเตอร์ Last-year/Ridge/CatBoost
Features และวัน/ค่าต้นทางที่ใช้จริงแยกจาก Training labels และ Evaluation reference
ข้อมูล Revised และ Publication date ที่พิสูจน์ไม่ได้คงเป็น unverified; preparation ผ่านไม่ใช่ PIT certification
`--train` ใช้เฉพาะ Exploratory, เลือกพารามิเตอร์ภายในแต่ละ family จาก Inner MAE และไม่เขียนทับ Production
ผู้ใช้อนุมัติ Rebaseline Training หลัง tests ผ่านแล้ว และอนุมัติ Weather Ablation ตาม protocol ที่ล็อกไว้; ไม่อนุมัติ Province Expansion

## Phase 3 — Weather Ablation (Exploratory เท่านั้น)

Runner แยก `experiment_weather_ablation.py` เปรียบเทียบ Last-year, CatBoost No Weather และ With Weather
No Weather ใช้จังหวัด/ปี/ผลผลิตปีก่อน; With Weather เพิ่ม 7 features เดิมรวม VPD
แต่ละแขนเลือก depth 2/3 จาก Inner 3 ปี; ไม่เลือก features หรือ parameters จาก Outer 2017–2025
ค่าเริ่มต้นแสดง help ไม่ fit; `--prepare` ตรวจ inputs/lineage/availability เท่านั้น
`--train` ใช้เฉพาะเมื่อ tests ผ่านและมีอนุมัติ Training แล้ว

```powershell
.build/national-analysis-venv/Scripts/python.exe -X utf8 tools/durian_model/experiment_weather_ablation.py --train
```

ผลอยู่ `training/weather_ablation_exploratory/<run_id>/` แบบ exclusive พร้อม config/protocol hash,
consumed feature lineage/dependencies แยกแขน, fold cutoffs, source snapshot และ protected hashes
With Weather ต้องตรง Phase 2 snapshot ก่อน fit และ fresh predictions ต้องตรงก่อน finalize
ไม่มีการอ่านผลเก่ามาใช้ selection; current OAE/POWER vintages ยัง unverified จึงไม่รับรอง PIT

## Availability Guard (Experimental เท่านั้น)

อ่าน [คู่มือ Guard](../../docs/research/modeling/DURIAN_AVAILABILITY_GUARD_TH.md) ก่อนรันใหม่ คำสั่ง `experiment_issue_date.py` ตอนนี้ตรวจ preflight อย่างเดียวโดยค่าเริ่มต้น เลือก `--mode exploratory` หรือ `--mode strict`; การฝึกต้อง opt-in ด้วย `--train` เท่านั้น รอบเพิ่ม Guard ไม่ได้ฝึกหรือเปลี่ยน MAE เดิม ปฏิทิน fixed-calendar ใหม่เป็น scenario ที่สร้างตอนนี้ ไม่ใช่หลักฐานประกาศในอดีต ผลใหม่แยกไว้ใน `training/issue_date_guarded/<mode>/` ไม่ทับผลเดิม

## ทดสอบวันออกพยากรณ์: 10 ตุลาคม 2569

อ่าน [รายงานผล issue-date](../../docs/research/modeling/ML_ISSUE_DATE_EXPERIMENT_TH.md) ก่อนใช้คะแนนเดิมเป็นคะแนนพยากรณ์สด ทดลองกันอากาศหลังวันออกพยากรณ์ออก ใช้ climatology จาก 10 ปีก่อนเป็นสถานการณ์อนาคต แล้วเปรียบเทียบ baselines, Ridge (lag only / stage), Random Forest และ CatBoost บน nested walk-forward เดิม 2017–2025 เลือกทั้ง family/parameter จาก inner validation เท่านั้น อายุผล proxy ตรึง 140 วัน ไม่ปรับสมมติฐานจาก error ปี test

```powershell
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/durian_model/experiment_issue_date.py
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/durian_model/report_issue_date.py
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_issue_date_experiment.py -v
```

ผลแยกเป็น `training/issue_date_*` ไม่เปลี่ยนโมเดลหลัก/API คะแนน inner-selected ก่อนฤดู 60 วัน MAE 233.62 และวันเริ่มฤดู 248.43 กก./ไร่ แพ้ค่าปีก่อน 215.51 ยังไม่พร้อม promote แม้ CatBoost ก่อนฤดูได้ 204.85 การเลือกจากคะแนนนี้เป็น exploratory outer selection ไม่ใช่ holdout ใหม่ ต้องเก็บ forecast archive และวันที่ประกาศผลผลิต/พื้นที่ให้ผลเพื่อทำ vintage evaluation ต่อ

ข้อมูลยังเป็นทุกพันธุ์ จุดอ้างอิงหนึ่งจุด/จังหวัด และสัดส่วนอากาศจริง/สถานการณ์ระบุใน `issue_date_weather_context.csv` ค่า lag 7 วันเป็นสมมติฐาน ไม่ใช่เวลาที่ NASA รับรอง แบบจำลองไม่ใช้พื้นที่ให้ผลจริงปี test เพื่อสร้างผลพยากรณ์ตันโดยไม่มีหลักฐานว่าทราบในวันนั้น

## ทดลองภูมิประเทศและอากาศ: 9 ตุลาคม 2569

รันจาก root ด้วย interpreter เดิม ไม่ต้องติดตั้ง dependency เพิ่ม:

```powershell
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/durian_model/experiment_terrain_interaction.py
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -p test_terrain_interaction.py -v
```

ดึง SRTM30m ผ่าน [Open Topo Data](https://www.opentopodata.org/datasets/srtm/) ครั้งแรก 90 พิกัดในคำขอเดียว แล้วใช้ cache `research_data/five_province_history/terrain_srtm30_samples.json` รันครั้งต่อไปแบบไม่ต้องเรียก API ใหม่ ตรวจ status/dataset/พิกัด/ค่าขาดก่อนคำนวณ slope เป็นเปอร์เซ็นต์ด้วย Horn gradient บน 3×3 จุดห่าง 1 arcsecond หน่วยเมตรตาม latitude; elevation เป็นค่าเฉลี่ย 9 samples ของแต่ละ patch ทั้งสอง **ไม่ใช่ค่าเฉลี่ยอำเภอหรือสวนที่ให้ผล** ตำแหน่งมาจากผู้ใช้ ยังไม่ตรวจว่าเป็นตัวแทนสวนจริง ไม่อ้างว่าค่า patch ที่ต่างพิสูจน์ว่าค่าเฉลี่ยอำเภอเดิมผิด

เก็บทั้งค่าที่ผู้ใช้ส่ง (ไม่มี DEM ต้นทาง จึงเป็น scenario only) และค่าดึง API ใน `terrain_selected_points.csv` แล้วเฉลี่ยสองจุดต่อจังหวัดด้วยน้ำหนักเท่ากัน ไม่ใช่น้ำหนักพื้นที่ให้ผล ไม่ใช้ข้อมูลน้ำใต้ดิน/ความลึกราก/TWI ที่ไม่ได้ตรวจสอบ

เพิ่ม weather control คือ `fruit_rx7day_mm` (ฝนสะสม 7 วันสูงสุดภายในช่วงผล) และ `early_fruit_hot38_days` (วัน Tmax >38°C ในวัน 0–29) คำนวณทุก cohort ก่อนเฉลี่ยตามฤดูและระยะผลเดิม ไม่ใช่เหตุการณ์น้ำท่วม/ผลร่วงที่สำรวจจริง ตัวแปร interaction คือ slope% × rx7 และ elevation(m) × hot38; ไม่บังคับ coefficient เป็นลบ กลุ่ม main เพิ่มเฉพาะ elevation/slope; กลุ่ม interaction รวม main + weather control + interactions จึงต้องเทียบ weather control ด้วย ไม่อนุมานว่าคะแนนที่ดีขึ้นทั้งหมดเกิดจากภูมิประเทศ

84 configurations (7 groups × 4 อายุผล × 3 alpha), outer test 2017–2025 จำนวน 45 แถวต่อ policy; inner 3 ปีก่อน test ฝึกเฉพาะปีน้อยกว่าปี validation รวมฤดูและ scaling จาก train เท่านั้น แก้ข้อผิดพลาดในตัวอย่างที่ใช้ `year != validation_year` ซึ่งทำให้ปีหลัง validation ปนเข้ามา Baseline ทุก fold ต้องเลือกค่าเอง ไม่ล็อก 140/alpha1 ตลอดย้อนหลัง และตรวจ reproduction ครบ 45 predictions

| วิธี | MAE กก./ไร่ | RMSE กก./ไร่ |
| --- | ---: | ---: |
| Baseline | 190.87 | 243.42 |
| เพิ่มอากาศสั้นอย่างเดียว | 179.94 | 232.89 |
| ค่าสมมติฐานผู้ใช้: main | 179.42 | 228.48 |
| ค่าสมมติฐานผู้ใช้: interaction + อากาศ | 177.46 | 229.76 |
| SRTM sampled proxy: main | 191.91 | 244.41 |
| SRTM sampled proxy: interaction + อากาศ | 184.21 | 237.27 |
| จังหวัด × อากาศ (diagnostic control) | 198.28 | 253.89 |
| Inner เลือกทุกกลุ่ม รวม scenario | 183.54 | 234.58 |
| Inner เลือกโดยไม่รับ scenario ที่ไม่มีหลักฐาน | 182.42 | 234.71 |

**ภูมิประเทศยังไม่ช่วยเหนืออากาศอย่างเดียว** ชุดอากาศลด MAE จาก baseline ประมาณ 5.73% แต่ descriptive paired year-block bootstrap ของเปอร์เซ็นต์ที่ดีขึ้น −12.49% ถึง 14.94% ยังคร่อมศูนย์ และแย่ลงในปี 2020/2023/2024 รายจังหวัดอากาศช่วยจันทบุรี สุราษฎร์ธานี อุตรดิตถ์ แต่ชุมพร/ศรีสะเกษแย่ลง นโยบาย evidence-selected ลด MAE 4.43% แต่ช่วง −7.82% ถึง 12.20% ยังคร่อมศูนย์ ไม่ใช่ independent holdout ใหม่

ตัวแปรดิน/terrain คงที่รายจังหวัดอยู่ใน span ของ province indicators จึงไม่มีข้อมูลเชิงพื้นที่อิสระเพิ่ม การเพิ่มคอลัมน์ซ้ำเชิงเส้นอาจเปลี่ยน Ridge regularization และคะแนน ไม่ใช่หลักฐานทางชีววิทยา โดยเฉพาะ scenario-main ที่ดูดี ไม่อ้างว่าน้ำใต้ดินช่วยผลผลิตปี 2019 หรือ slope ทำให้ผลร่วง

ผลทดลองแยกใน `research_data/five_province_history/training/terrain_results.json`, `terrain_summary.csv`, `terrain_predictions.csv` (405 rows), `terrain_tuning.csv` (840 rows) มีคะแนนรายจังหวัด/ปี bootstrap เปรียบ baseline และ weather-control fold choices และ hashes ตรวจย้อนกลับได้ **ไม่ทับโมเดลหลัก PDF หรือแดชบอร์ด**

### ตัวทำนายทดลองที่รันต่อได้

`terrain_candidate_model.json` เลือกจาก inner validation เท่านั้นและตัดสองกลุ่ม supplied ออก เพื่อไม่ใช้ค่าภูมิประเทศที่ไม่มีต้นทาง ใน final refit ถึงปี 2025 เลือก **baseline อายุผล 140 วัน alpha 1** ไม่บังคับใช้กลุ่มที่คะแนน outer ดีที่สุด ชุด inner-selected ที่รวม scenario อยู่ในผลเพื่อวิเคราะห์เท่านั้น ไม่ผ่านช่องทาง predict

กรอก `terrain_future_input_template.csv` ด้วยข้อมูลจริง/สถานการณ์ที่คำนวณแล้ว: จังหวัด รหัสปี อายุผล `140`, `season_months` ตาม model (`22:4,5,6`, `33:5,6,7`, `53:6,7,8`, `84:6,7,8`, `86:7,8,9`), FEATURES เดิมและสองค่าฝน/ร้อนข้างต้น `bearing_rai` optional หากไม่มีให้ลบคอลัมน์ ใช้พื้นที่ให้ผลไม่ใช่พื้นที่ปลูกทั้งหมด ต้องคำนวณ stage predictors ด้วยสูตรและ aggregation เดียวกับการฝึก ห้ามกรอกอากาศที่ยังไม่เกิดเหมือนเป็นค่าจริงหรือใส่ target ใน input

```powershell
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/durian_model/experiment_terrain_interaction.py --predict-input C:\path\complete_stage_weather.csv --output C:\path\new_conditional_predictions.csv
```

ปฏิเสธคอลัมน์ target/metadata ที่ไม่อยู่ใน contract, ปี <=2025, พันธุ์/จังหวัดนอกขอบเขต, stages ที่อายุ/ฤดูผิด, missing/ค่าผิดช่วง และไม่เขียนทับ output เดิม ผลเป็น **exploratory conditional estimate** ไม่ใช่พยากรณ์ operational: ยังไม่ทำ forecast-vintage evaluation หรือ prediction intervals และ target ยังเป็นทุเรียนรวมทุกพันธุ์ การใช้ฟีเจอร์อากาศทั้งฤดูไม่ใช่การทำนายล่วงหน้าก่อนมีข้อมูลครบ

## ทดลองล่าสุด: ปรับช่วงย้อนหลังตาม ENSO และอากาศพื้นที่

### ทดลองตำแหน่งเวลา: Dry-Spell Trigger พร้อม Rain Reset

รัน `tools/durian_model/experiment_dry_trigger.py` ด้วย interpreter เดิม ใช้ฟีเจอร์เดิมทั้งหมด รวม VPD และรังสีเฉลี่ย MJ/m²/วัน คำนวณใหม่ตามหน้าต่างที่ขยับ ไม่เพิ่ม predictors เพื่อแยกผลของตำแหน่งเวลา ผลบันทึกแยกใน `research_data/five_province_history/training/dry_trigger_*` ไม่ทับ baseline หรือผลทดลองเก่า

กติกาการทดลอง: ฝนเฉลี่ยย้อนหลัง 15 วัน <1 มม./วัน วันแรกที่เข้าเกณฑ์ของแต่ละ episode +50 วันเป็นวันดอกบานประมาณการ ภาคใต้เริ่มค้น 15 มกราคม ภาคอื่น 1 ธันวาคมปีก่อนฤดูเก็บเกี่ยว หากเข้าเกณฑ์อยู่ก่อนขอบค้นหา ถือว่า left-censored และไม่สร้างวัน trigger ที่ขอบโดยพลการ รุ่นที่ใช้ reset ตัด candidate ที่มีฝน >25 มม. ในวัน t ถึง t+30 รวมปลายทั้งสองด้าน แล้วรอการเข้าเกณฑ์แห้งรอบใหม่ ไม่ได้นับใหม่อัตโนมัติจากวันที่ฝนตก

สำหรับแต่ละวันเก็บเกี่ยวในฤดู 3 เดือนที่เรียนรู้จากปีก่อน เลือกวันดอกบานประมาณการใกล้ anchor เดิมที่สุดภายใน ±30 วัน ถ้าไม่มีให้ใช้ anchor เดิมพร้อม `dry_trigger_not_found` แยกเหตุผลว่าไม่มี episode ที่ยอมรับ หรือ candidate อยู่นอกช่วงจับคู่ ถ้ามีเฉพาะบาง cohort ให้ระบุ partial fallback; ไม่ลบแถวที่หาไม่พบ ไม่ใช้ผลผลิตหรือสัดส่วนฤดูของปี test เลือกวัน ข้อมูลฝนขาดหายทำให้หยุด ไม่ถือเป็นปีไม่มี trigger

36 configurations (3 recipes × 4 ระยะผล × 3 alpha), inner validation 3 ปีก่อน test; 45 จังหวัด–ปีเดิม:

| นโยบาย | MAE กก./ไร่ | RMSE กก./ไร่ |
| --- | ---: | ---: |
| เดิม | 190.87 | 243.42 |
| Dry Trigger | 211.27 | 257.59 |
| Dry Trigger + Rain Reset | 202.30 | 251.28 |
| ให้ inner validation เลือกเอง | 191.48 | 244.23 |

**รอบนี้ไม่ดีขึ้น** แบบ trigger/trigger-reset มี fallback ประมาณ 53.23%/53.89% ของ cohorts ใน fold ที่เลือก ส่วน baseline เองไม่มีการพยายามหา trigger จึงไม่นับเป็น fallback ข้อมูล context เก็บวันที่ขอบค้นหา ช่วง bloom proxy จำนวน candidate จำนวนที่ถูก reset และสัดส่วนการกลับ baseline แต่ช่วง bloom proxy อาจผสมวันสมมติและวันประมาณการ ไม่ใช่ช่วงที่สำรวจจริง

วันที่เริ่มค้นหา เกณฑ์ reset ระยะ ±30 วัน และวิธีจับคู่กับฤดูเป็นสมมติฐานปรับใช้ของเรา ไม่ใช่กฎจากงาน [Eguchi et al.](https://doi.org/10.1007/s00484-024-02819-x) ความแม่นที่แย่ลงยังไม่พิสูจน์ว่าช่วงแห้งไม่กระตุ้นดอก: ไม่มีวันดอกบานจริง/ข้อมูลการให้น้ำ/ความพร้อมต้นสำหรับสอบเทียบ และห้ามกล่าวว่า reset ยืนยันว่าตาดอกแท้ง

อุณหภูมิยังอยู่ในฟีเจอร์เดิม ไม่ใช้ข้อสรุปของมาเลเซียตัดอุณหภูมิออกจากประเทศไทย ยังไม่มีแขนทดลอง surveyed-bloom เพราะไม่มีข้อมูลตรวจยืนยัน ห้ามสร้าง ground truth จากวันตัดมีดแรก [NASA ระบุความละเอียด](https://power.larc.nasa.gov/docs/tutorials/) อากาศ 0.5×0.625 องศา และรังสี 1×1 องศา ไม่ใช่เซนเซอร์สวนหรือทุกตัวแปรมีกริดเดียวกัน ตรวจเอกสาร 9 ตุลาคม 2569

### ทดลองเพิ่มเหตุการณ์อากาศสั้น

#### ทดลองเจาะช่วงวัน 30–50 หลังดอกบานสมมติ

รัน `tools/durian_model/experiment_critical_window.py` ด้วย interpreter เดิม ผลแยกใน `research_data/five_province_history/training/critical_window_*` ไม่เขียนทับผลรอบก่อน เพิ่ม CDD, วัน Tmax >38°C, ระยะร้อนต่อเนื่อง, วันฝน >=10 มม. หลัง 7 วันก่อนหน้าทั้งหมดมีฝน <1 มม. และ interaction จำนวนวันร้อน × CDD คูณในแต่ละ cohort ก่อนเฉลี่ย ไม่บังคับ coefficient ให้เป็นลบ

หน้าต่างนับวัน 30 ถึง 50 รวมปลายทั้งสองด้าน (21 วัน) คำนวณย้อนหลังตามระยะผลสมมติ 120/130/140/150 วันและฤดูจากปีฝึก ไม่มีตัวแปรอายุต้น `local_age`/`enso_local_age` ในกราฟเก่าเป็นชื่อวิธีปรับระยะผล ไม่ใช่ฟีเจอร์อายุต้น จึงไม่ได้ทำ log/sigmoid ของอายุต้นที่ไม่มีข้อมูลจริง

| นโยบาย | MAE กก./ไร่ | RMSE กก./ไร่ |
| --- | ---: | ---: |
| เดิม | 190.87 | 243.42 |
| Critical window | 197.26 | 247.34 |
| Critical + interaction | 194.22 | 246.11 |
| Critical + ฝนหนักสะสม | 189.38 | 246.06 |
| ให้ inner validation เลือกทุกชุด | 192.87 | 247.81 |

48 configurations บน 45 test rows เดิม ชุดรวมฝนหนักลด MAE 0.78% แต่ RMSE สูงขึ้น ช่วง bootstrap เปอร์เซ็นต์ที่ดีขึ้น −6.15% ถึง 5.89% คร่อมศูนย์ **ยังไม่ช่วยอย่างชัดเจน** ทุกนโยบายของปี 2024 และ final refit ปี 2026 เลือก baseline อายุ 140 alpha 1 จึงยังไม่แก้ overprediction ปี 2024 และไม่เปลี่ยนโมเดลหลัก

นี่ไม่พิสูจน์ว่าผลอ่อนช่วงนี้ไม่ไวต่ออากาศ เพราะช่วงวันดอกบานเป็น proxy และอากาศยังจุดเดียวต่อจังหวัด ฝนหลังแล้งไม่ได้ยืนยันการแตกใบอ่อนจริง ไม่มีข้อมูลผลร่วง/ชลประทาน/อายุต้น กราฟ error และ coefficients ไม่พิสูจน์สาเหตุหรือความสัมพันธ์เชิงเหตุผล เกณฑ์ 38°C, ฝน 10 มม. และระยะ 7 วันเป็น hypotheses สำหรับทดสอบ ไม่ใช่เกณฑ์เสียหายที่สอบเทียบแล้ว ตัวเลขร่วง 70–90% หรือร้อน 3–5 วันแล้วร่วงทันทีจากข้อความส่งต่อยังไม่ได้รับรองเป็นกฎทั่วไป

เอกสาร [สำนักงานเกษตรจังหวัดยะลา](https://yala.doae.go.th/blog/2026/05/15/%E0%B9%80%E0%B8%81%E0%B8%A9%E0%B8%95%E0%B8%A3%E0%B8%A2%E0%B8%B0%E0%B8%A5%E0%B8%B2-%E0%B8%A5%E0%B8%87%E0%B8%9E%E0%B8%B7%E0%B9%89%E0%B8%99%E0%B8%97%E0%B8%B5%E0%B9%88%E0%B8%AA%E0%B8%B3%E0%B8%A3%E0%B8%A7/) กล่าวถึงการรักษาความชื้นสม่ำเสมอในระยะผลเล็ก 1–2 เดือนและป้องกันการแตกใบอ่อน ใช้เป็นบริบทเท่านั้น ไม่ใช่หลักฐานยืนยันค่า thresholds หรือสาเหตุ error ทั้งห้าจังหวัด ตรวจหน้าเว็บ 9 ตุลาคม 2569

#### การทดลอง shock รอบก่อน

รัน `tools/durian_model/experiment_weather_shocks.py` ด้วย interpreter เดิม ไม่ต้องดาวน์โหลดใหม่ ใช้ Ridge + VPD และระยะคงที่ 120/130/140/150 วันเป็น control เพื่อแยกผลของ shock features จากการปรับระยะตาม ENSO ไม่ได้รวมสองการทดลองนี้เป็นโมเดลเดียว

เพิ่มฝนทิ้งช่วงสูงสุดก่อนดอก/ผลอ่อน (ฝน <1 มม./วัน), จำนวนวันและช่วงต่อเนื่อง Tmax >35°C ในผลอ่อน, จำนวนวัน >38°C และฝนสะสม 3/7 วันสูงสุดในระยะผล เกณฑ์ร้อนเป็นสมมติฐาน ไม่ใช่จุดเสียหายทุเรียนที่พิสูจน์แล้ว คำนวณเหตุการณ์ของแต่ละวันเก็บเกี่ยวสมมติก่อน แล้วเฉลี่ยข้าม cohorts ไม่ใช้ผลผลิตปี test ถ่วงฤดู ไม่มีข้อมูลแหล่งน้ำ ชลประทาน หรือความเสียหายน้ำท่วมจริงเพิ่มในรอบนี้

48 configurations (4 ชุด predictors × 4 อายุ × 3 alpha); 3 ปี inner validation ก่อน test แต่ละปี ชุดที่เพิ่ม predictors ยังเลือก control เดิมได้ ผลบน 45 จังหวัด–ปีเดิม:

| นโยบาย | MAE กก./ไร่ | RMSE กก./ไร่ |
| --- | ---: | ---: |
| เดิม | 190.87 | 243.42 |
| ร้อนและฝนทิ้งช่วง | 193.03 | 245.30 |
| ฝนหนักสะสม | 184.01 | 235.47 |
| รวม shock ทั้งหมด | 186.21 | 241.71 |
| ให้ inner validation เลือกทุกชุด | 193.99 | 244.32 |

ชุดฝนหนักลด MAE 3.59% แต่ช่วง bootstrap −13.83% ถึง 11.84% คร่อมศูนย์ แย่ลงในปี 2020, 2023, 2024 ผลรายจังหวัดดีขึ้นที่จันทบุรี สุราษฎร์ธานี อุตรดิตถ์ แต่แย่ลงที่ชุมพรและศรีสะเกษ การเลือกผู้ชนะจากคะแนน outer เป็น exploratory selection ไม่ใช่หลักฐานยืนยันว่าใช้จริงจะดีกว่า นโยบาย inner-selected ไม่ชนะเดิม และการ refit ปี 2026 เลือก baseline อายุ 140 วัน alpha 1 จึง **เก็บโมเดลหลักเดิม**

ผลแยกอยู่ใน `training/weather_shock_results.json`, `weather_shock_predictions.csv`, `weather_shock_tuning.csv`, `weather_shock_context.csv` และ `weather_shock_comparison.png` (ใต้ `research_data/five_province_history/`) context มีเฉพาะสูตร inner-selected คะแนนต้นฉบับถูกตรวจว่าทำซ้ำตรงทั้ง 45 แถว ห้ามตีความฝนหนักเป็นน้ำท่วมหรือ CDD เป็นการขาดน้ำในสวนโดยตรง อ่านนิยามดัชนี [Climdex](https://www.climdex.org/learn/indices/) ประกอบ; เราปรับใช้กับหน้าต่างระยะผล ไม่ใช่ดัชนีรายปีมาตรฐาน

### การทดลองระยะผล ENSO ก่อนหน้า

โค้ดแยกจากขั้น 0–6 เพื่อไม่เขียนทับโมเดลหลัก ใช้ฤดูหลัก 3 เดือนจากปีฝึกเป็น proxy ของฤดูพันธุ์หลัก ไม่ใช่ข้อมูลหมอนทองแยกพันธุ์หรือวันดอกบานจริง เป้าหมายยังเป็นผลผลิตทุเรียนรวม / พื้นที่ให้ผล

```powershell
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/fetch_enso_context.py
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/durian_model/experiment_climate_age.py
```

คำสั่งแรกต้องใช้อินเทอร์เน็ตและดึง NOAA ฉบับล่าสุด; คำสั่งที่สองใช้ข้อมูลในเครื่องและตรวจ hash กับ snapshot ของขั้น 0–6 หากจะทำซ้ำผลเดิมให้เก็บ `enso_context.json` และ evidence ฉบับเดิม ไม่รีเฟรชข้อมูลกลางการตรวจผล

| นโยบาย | MAE กก./ไร่ | RMSE กก./ไร่ |
| --- | ---: | ---: |
| ระยะคงที่เดิม | 190.87 | 243.42 |
| ขยายช่วงระยะคงที่ | 192.07 | 245.12 |
| ปรับตาม ENSO | 194.58 | 245.59 |
| ปรับตามอากาศพื้นที่ | 190.09 | 246.22 |
| ปรับตาม ENSO และอากาศพื้นที่ | 186.23 | 242.42 |
| ให้ inner validation เลือกทุกสูตร | 188.23 | 243.98 |

153 configurations; ฝึกปี 2010–2025 และทดสอบเดินหน้าปี 2017–2025 รวม 45 แถวต่อนโยบาย เลือกฤดู ค่าเฉลี่ย/ส่วนเบี่ยงเบนอากาศ สูตร วัน และ alpha ด้วยปีก่อน test เท่านั้น ขยับระยะครั้งละ 5 วัน สูงสุด ±10 วัน; เปิดให้เลือกไม่ขยับด้วย การขยายระยะคงที่เป็น control แยกผลของการเพิ่ม search space

สูตรผสม ENSO และอากาศพื้นที่มี MAE ต่ำที่สุดในการสำรวจนี้ (ลด 2.43%) แต่ช่วง bootstrap ของเปอร์เซ็นต์ที่ดีขึ้น −0.72% ถึง 9.78% คร่อมศูนย์ และแย่กว่าเดิมในปี 2019, 2024, 2025 จึงยังไม่พิสูจน์ว่าดีกว่าอย่างสม่ำเสมอ ปีทดสอบเคยถูกสำรวจแล้ว การเลือกนโยบายจากคะแนนนี้มี selection optimism นโยบาย inner-selected ลด MAE ประมาณ 1.38% แต่ RMSE ไม่ดีขึ้น ช่วง bootstrap ก็คร่อมศูนย์

การ refit สำหรับปี 2026 ของ inner-selected เลือกสูตรเปียก/แสงน้อย ฐาน 140 วัน ขยับได้ 5 วัน alpha 1 ไม่ได้เลือกสูตรผสมเพราะคะแนน test ต่ำสุด ยังไม่มีผลผลิตพยากรณ์สด ต้องมี weather features ครบหรือ scenario ที่ระบุชัดก่อน

ไฟล์ผลอยู่ใน `research_data/five_province_history/training/`:

- `climate_age_results.json`: วิธีทดลอง คะแนนรายพื้นที่/ปี สูตรแต่ละ fold พารามิเตอร์ refit และ hash
- `climate_age_predictions.csv`: 270 แถวสำหรับตรวจผลจับคู่ 6 นโยบาย
- `climate_age_context.csv`: 45 แถวของนโยบาย inner-selected พร้อมอากาศ/ดัชนี ENSO/ป้ายท้องถิ่นและระยะที่เลือก ไม่ใช่บริบทของทุกนโยบาย
- `climate_age_tuning.csv`: คะแนน validation ของ 153 configurations ต่อ origin
- `climate_age_comparison.png`: กราฟสรุป

แก้สูตรและ grid ที่ `experiment_climate_age.py`; แก้การอ่านแหล่ง ENSO ที่ `tools/fetch_enso_context.py` [NOAA ใช้ RONI ติดตาม ENSO](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/) และเผยแพร่ [ความน่าจะเป็นพยากรณ์รายฤดู 3 เดือน](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/probabilities/) ไม่ใช่สถานะจริงตายตัวของทั้งปี เก็บพยากรณ์แยกจากข้อมูลย้อนหลังและไม่ใช้พยากรณ์ปัจจุบันย้อนเทรนอดีต

RONI ที่ใช้ย้อนหลังเป็น revised snapshot แม้เลือกเฉพาะฤดูที่สิ้นสุดก่อนช่วงคำนวณก็ยังไม่ยืนยัน publication-time vintage อากาศยังเป็นจุดอ้างอิง NASA POWER ไม่ใช่ค่าเฉลี่ยถ่วงพื้นที่สวนที่ให้ผล อายุเป็นสมมติฐาน feature ไม่ใช่ค่าที่วัดจริง Bootstrap ใช้ 9 บล็อกปี สุ่มแบบ circular 3 ปี 20,000 ครั้ง seed 42 ไม่ refit หรือแก้ selection bias **ผลชุดนี้ไม่แทนโมเดลหลัก รายงาน PDF หรือหน้าเว็บอัตโนมัติ**

เลือก **Ridge + VPD** จากผลเปรียบเทียบเดิม 26 กลุ่มโมเดล โดยใช้ MAE เป็นเกณฑ์หลัก ไม่ใช่เลือกเพราะชื่อโมเดลซับซ้อน ข้อมูลปี 2010-2025; ทดสอบแบบเดินหน้าปี 2017-2025 รวม 45 จังหวัด-ปี ผลชุดนี้เป็นการสำรวจย้อนหลัง ไม่ใช่ holdout ใหม่ที่ยังไม่เคยเห็น

## เปิดและรัน

เปิดโฟลเดอร์ repo หลักใน VS Code แล้วเลือก Python interpreter ของโครงการ `.build/national-analysis-venv/Scripts/python.exe` ไฟล์ทุกขั้นมี `if __name__ == '__main__'` จึงกด **Run Python File** ได้ รันตามเลข ไม่ต้องเปิดเว็บไซต์หรือใช้ API key

| ขั้น | ไฟล์ที่เปิดแก้ในโฟลเดอร์นี้ | หน้าที่ / ผลลัพธ์ |
| --- | --- | --- |
| 0 | `step0_audit_data.py` | ตรวจยอดจริง พื้นที่ให้ผล หน่วย ปี และ hash; สร้าง panel/audit |
| 1 | `step1_split_years.py` | กำหนดปี train/validation/test ตามเวลา ไม่สุ่ม |
| 2 | `step2_process_data.py` | เรียนรู้ฤดูจากปี train และสร้าง weather/VPD ตามช่วงอายุผล |
| 3 | `step3_train_model.py` | Tune อายุ 120/130/140/150 วัน และ alpha 1/10/100; เก็บโมเดล JSON |
| 4 | `step4_investigate_feature_importance.py` | ดู coefficient ที่ standardize แล้ว พร้อมกราฟ ไม่ใช่เหตุเชิงสาเหตุ |
| 5 | `step5_evaluate_result.py` | MAE/RMSE/bias รายปี/จังหวัด เทียบ baseline ตรวจผลเดิม และ paired year-block bootstrap |
| 6 | `step6_predict_live.py` | สาธิตทำนายปี 2025 ด้วยโมเดล train ถึง 2024; รับ CSV ปีใหม่ได้แบบมีเงื่อนไข |
| รวม | `run_all.py` | รันทั้งเจ็ดขั้นตามลำดับ |
| ส่วนร่วม | `common.py` | paths/schema/scaling/validation/สูตร target; ไม่ต้องคัดลอกฟังก์ชันซ้ำ |
| รายงาน | `build_report.py` | สร้าง Notebook ที่ execute จริง รายงาน Markdown และ PDF |

ใน Terminal (PowerShell) ที่ root:

```powershell
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/durian_model/run_all.py
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/durian_model/step5_evaluate_result.py
& .\.build\national-analysis-venv\Scripts\python.exe -m unittest discover -s tests -p test_durian_steps.py -v
```

ถ้าไม่มี venv นี้ สร้าง venv ใหม่ด้วย Python 3.12+ แล้วติดตั้ง `numpy pandas matplotlib` สำหรับขั้น 0-6; การสร้างรายงานเพิ่ม `reportlab>=4.4 uharfbuzz nbformat nbclient ipykernel pypdf` ไม่ต้องติดตั้ง CatBoost เพื่อรันโมเดลที่เลือก

## ไฟล์ผลลัพธ์และการแก้ต่อ

- ผลทุกขั้นอยู่ `research_data/five_province_history/training/ridge_vpd_*` ไม่เปลี่ยนข้อมูลดิบหรือผลทดลองก่อนหน้า รันซ้ำจะเขียนทับเฉพาะชุดผลลัพธ์นี้
- Notebook: `notebooks/DURIAN_RIDGE_VPD_STEPS.ipynb`
- รายงานอ่าน/คัดลอกข้อความได้: `docs/research/modeling/DURIAN_RIDGE_VPD_REPORT_TH.md`; PDF: `output/pdf/DURIAN_RIDGE_VPD_REPORT_TH.pdf` หากแก้ข้อความถาวร ให้แก้ `report_pages()` ใน `build_report.py` แล้วสร้างใหม่ เพราะ Markdown เป็นผลลัพธ์ที่สร้างจากโค้ด
- ตารางครบ 26 วิธี: `ridge_vpd_comparison_models.csv`; ข้อผิดพลาดจับคู่รายปี: `ridge_vpd_paired_year_errors.csv`; ช่วง bootstrap และข้อจำกัด: `ridge_vpd_evaluation.json`
- ถ้าแก้แหล่งข้อมูล ต้องรัน 0-6 ใหม่ทั้งหมด; snapshot check จะไม่ยอมให้เอา input ใหม่ปนกับ model เดิม
- รันขั้นก่อนหน้าซ้ำจะทำให้สถานะผลขั้นถัดไปใช้ไม่ได้จนกว่าจะรันใหม่ตามลำดับ ไฟล์เก่ายังอยู่เพื่อไม่ลบงาน แต่ต้องดู `ridge_vpd_workflow_state.json` ไม่ใช่ดูว่าไฟล์มีอยู่แล้วอย่างเดียว
- ถ้าแก้รายการ feature/encoding ให้แก้ `common.py` แล้วตรวจ `step2`/`step3`/`step6` กับ tests ด้วย อายุ/alpha อยู่ใน constants ของ `tools/compare_harvest_stage_yield.py` ซึ่งใช้ร่วมกับงานวิจัยเดิม
- ผล baseline/model อื่นในรายงานอ้างผล benchmark เดิมที่มี hash ตรงกัน; pipeline นี้รันใหม่เฉพาะ Ridge + VPD ไม่อ้างว่าฝึกครบ 26 กลุ่มใหม่

## ขั้น 6 ไม่ใช่ระบบพยากรณ์สดสำเร็จรูป

Demo ใช้อากาศที่เกิดแล้ว โมเดลสุดท้าย train ถึง 2025 (อายุสมมติ 140 วัน, alpha 1) รับปี >2025 เท่านั้น กรอก template ทุก feature ด้วยอายุ/ฤดูใน `ridge_vpd_prediction_contract.json` ถ้าอากาศยังไม่เกิดต้องใช้ค่าพยากรณ์หรือ scenario พร้อมติดป้ายให้ชัด ห้ามใช้ค่าเฉลี่ยทั้งปีแทนช่วง feature โดยเงียบ ๆ

```powershell
& .\.build\national-analysis-venv\Scripts\python.exe -X utf8 tools/durian_model/step6_predict_live.py --input path/to/new_stage_features.csv --output path/to/new_predictions.csv
```

CSV ต้องมี `province_code,year_ce` และ predictors ตาม contract; optional `bearing_rai` ใช้แปลงผล kg/rai เป็นตัน ห้ามใส่ target/ยอดผลผลิตปัจจุบันเข้า input ไม่มีการใส่ข้อมูลสมมติใน template

## ข้อจำกัดที่ต้องติดไปกับงาน

อากาศเป็น NASA POWER จุดอ้างอิงหนึ่งจุดต่อจังหวัด ไม่ใช่ค่าเฉลี่ยถ่วงด้วยสวนที่ให้ผล; ฤดู 3 เดือนและอายุผลเป็น proxy ไม่ใช่วันดอกบานจริง; VPD คำนวณจาก RH เฉลี่ยรายวันไม่ใช่ VPD ที่ใบ; coefficient ไม่พิสูจน์น้ำท่วม ลูกร่วง หรือความพร้อมต้น ยังไม่ได้ใส่ NDVI/ชุดดิน/ภัยพิบัติที่พื้นที่และเวลาข้อมูลไม่ตรงกันลงในโมเดลตัวนี้

11.44% เทียบค่าปีก่อนและ 2.07% เทียบ Ridge ไม่มี VPD คำนวณก่อนปัดเศษ เป็นผลสำรวจ ไม่ใช่ความเหนือกว่าทางสถิติ โมเดลแย่กว่าค่าปีก่อนในปี 2018, 2020, 2021 Bootstrap ใช้บล็อกปีต่อเนื่อง 3 ปีและ sensitivity 2 ปี เก็บทั้งห้าจังหวัดร่วมกัน สุ่ม 20,000 ครั้ง seed 42 ช่วงเปอร์เซ็นไทล์ 95% ทั้งสองตัวเทียบคร่อมศูนย์ มีเพียง 9 ปี สมมติฐาน stationarity ยังไม่ยืนยัน และไม่ได้ปรับการเลือกผู้ชนะ 26 วิธีหรือเทรนใหม่ในแต่ละรอบ จึงไม่ใช่ confirmatory confidence interval หรือ prediction interval
