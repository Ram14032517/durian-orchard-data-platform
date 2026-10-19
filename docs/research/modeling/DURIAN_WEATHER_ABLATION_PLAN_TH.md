# Phase 3 — Weather Ablation Preparation: ตรวจความสอดคล้องและเสนอแผน

วันที่ 11 ตุลาคม 2026 (Asia/Bangkok)
รอบนี้ตรวจข้อมูล/โค้ดและคำนวณฟีเจอร์ซ้ำเท่านั้น ไม่รัน experiment training
แก้เฉพาะรายงานนี้ ยังไม่ implement pipeline/tests ใหม่ และไม่แก้ Production/API/Frontend

## 1. ทำไม CatBoost ได้ MAE 204.85 เหมือนเดิม

เปรียบเทียบ legacy `training/issue_date_*` ที่ Lead 60 กับ Rebaseline run
`training/rebaseline_exploratory/20261010T131023246729Z/` ไม่เทียบ Lead 0 หรือ Auto Select
จับคู่ด้วย province_code/year_ce และตรวจครบจำนวนก่อนเปรียบเทียบ

| รายการ | ผลตรวจ |
|---|---|
| Last-year (legacy lag) | 45/45 predictions และ targets ตรงกันทุกแถว; max delta = 0 |
| Ridge (legacy stage_ridge) | 45/45 predictions และ targets ตรงกันทุกแถว; max delta = 0 |
| CatBoost (legacy stage_catboost) | 45/45 predictions และ targets ตรงกันทุกแถว; max delta = 0 |
| Issue date / weather cutoff | ตรงทั้ง 80 จังหวัด–ปี (2010–2025), 560 feature-context rows |
| Weather coverage fractions | max delta 1.11e-16 จาก CSV floating-point serialization |
| Ridge/CatBoost parameter choices | ตรง 18/18 ปี–โมเดล; Inner mean MAE delta = 0 |
| Source inputs | SHA256 annual/monthly/weather ตรงทั้งสองรอบและไฟล์ปัจจุบัน |
| Rebaseline artifacts/code/manifest | artifact inventory 18 รายการ, code hashes และ manifest hash ตรง |

Legacy weather_context ระบุฤดูเดียวตลอด: 22=(4,5,6), 33=(5,6,7), 53=(6,7,8),
84/86=(7,8,9) ซึ่งตรงกับ Fixed-calendar anchors 04-01/05-01/06-01/07-01/07-01
ตัวอย่าง issue ปี 2023: จันทบุรี 31 ม.ค., ศรีสะเกษ 2 มี.ค., อุตรดิตถ์ 2 เม.ย.,
สุราษฎร์ธานี/ชุมพร 2 พ.ค. ทั้งสอง artifacts ตรงกัน
สำเนา source ก่อน Phase 1 ก็สร้าง seasons จาก manifest anchors ไม่ใช่ training_seasons
คำอธิบาย/HORIZONS comment ที่กล่าวถึง train-derived season ไม่ตรงกับ implementation ณ สำเนาที่ตรวจ
ไม่ได้แก้ comment/โค้ดในรอบนี้ และไม่ถือข้อความนั้นเป็นหลักฐานว่า dates ต่างกัน

คำนวณ weather features ใหม่ทั้ง 80 แถวจาก source ปัจจุบัน โดย mock fit_predict ให้ raise ถ้าถูกเรียก
เทียบ 7 features กับ predictors.csv: max absolute delta ≤5.69e-14 (CSV/float round-trip)
API เดิม features() กับ features_with_lineage() ให้ feature values/issue/cutoff เท่ากันทุก 80 แถว
Features ทั้งสอง candidate lists ตรงกัน: lag yield + 7 weather variables; design เพิ่มจังหวัด/ปีเหมือนกัน
อายุ proxy 140 วัน, weather lag 7 วัน, climatology 10 ปีก่อน, Inner 3 ปี และ CatBoost depth 2/3 เหมือนกัน

ดังนั้นเลขตรงกันไม่ใช่แค่ปัด MAE บังเอิญเท่ากัน: มีหลักฐานว่า inputs และ within-family selection
เหมือนกัน ทำให้ predictions เหมือนกันทั้งสามโมเดล งาน Rebaseline เพิ่ม audit/isolation ไม่ได้เปลี่ยน
effective numerical calendar ของ artifacts ชุดเดิมที่นำมาเทียบ
ไม่ได้คัดลอกคะแนนเดิม และไม่ถือ Rebaseline เป็นการยืนยันผลบนข้อมูลอิสระใหม่
ข้อสรุปนี้เฉพาะ artifacts ที่ตรวจ ไม่ใช่ทุก protocol ที่เคยทดลองในโครงการ

## 2. Cache, Protocol Hash และ Artifact Loading

- Legacy: frame cache อยู่ใน run() ใช้ (season signature, lead); estimates cache (year,candidate)
  สร้างใหม่ในแต่ละ lead ส่วน cutoff argument ของ frame_for ไม่เปลี่ยนฤดูเพราะ seasons คงที่
  normal cache ผูก instance, province และ year; normal history ใช้เฉพาะ y-10 ถึง y-1
- Rebaseline: cache อยู่ภายใน train_predictions() เริ่มว่างทุก call; key=(fold_year,candidate index)
  ก่อน reuse ตรวจ digest ของ train predictors + training labels + forecast predictors
  fit_audit 189 records: 120 reuses ของ context ที่ตรงกัน; ไม่ใช่การโหลด estimator/predictions จากดิสก์
  candidate/grid คงทั้ง call จึงไม่พบ cross-feature-set/cross-protocol reuse ในรอบ Phase 2
- prepare() โหลด annual/weather และ manifest ใหม่; common.check_snapshot() อ่าน ridge_vpd_audit.json
  เพื่อตรวจ input hashes ไม่โหลด Production parameters/predictions เข้า fit
  runner ไม่อ่าน issue_date_predictions.csv หรือ Rebaseline predictions เก่าเพื่อออก predictions ใหม่
  การอ่านไฟล์เหล่านั้นในงานนี้เป็นการตรวจ read-only เท่านั้น
- Rebaseline เก็บ schedule hash, manifest hash, code/data hashes และ config แต่ยังไม่มี
  canonical hash เดียวที่ครอบคลุม full protocol + feature set จึงต้องเพิ่มใน runner Phase 3 ใหม่
  ห้ามใช้ candidate index อย่างเดียวเมื่อ No Weather/With Weather อยู่ในรอบเดียวกัน

Schedule SHA256 ปัจจุบัน:
`51eca525b6cc2f6d7dfe3401613253d202ea3a254712c0526229b6d0b46405ae`
legacy plan มี input hashes/candidate config แต่ไม่มี complete execution code hash และ artifact inventory
รวมทั้งไม่ได้เก็บ numeric feature matrix เดิมครบ จึง reconstruct inputs ได้ แต่ไม่ authenticate
historical execution ทั้งหมดอย่างอิสระได้ ไม่พบความผิดปกติที่ต้องหยุดก่อนเสนอแผน
หากขั้น implement พบ cache signature mismatch, artifact mismatch หรือผิด calendar ให้หยุดก่อน fit

## 3. แผนการทดลองที่ขออนุมัติ

| แขนทดลอง | Predictors ที่ส่งเข้า estimator | การเลือกพารามิเตอร์ |
|---|---|---|
| Last-year | previous_yield_kg_rai เท่านั้น | ไม่ fit/ไม่จูน |
| CatBoost No Weather | province one-hot 5 ตัว + year_ce + previous_yield_kg_rai | depth 2/3 จาก Inner ของแขนนี้ |
| CatBoost With Weather | Non-weather เดิมทั้งหมด + weather 7 ตัว | depth 2/3 จาก Inner ของแขนนี้ |

No Weather มี 7 design columns; With Weather มี 14 ตาม helper เดิม
province_code/year_ce เป็นตัวแปรนิยาม ไม่ใช่ metadata อากาศ; ห้ามเพิ่ม area, production หรือ target
ตัด weather ทั้งเจ็ดจาก No Weather ไม่แทนด้วยศูนย์ ไม่ impute และไม่ส่งแฝงผ่าน interaction:

1. pre_bloom_90d_rain_mm
2. fruit_0_29d_rain_mm
3. fruit_30_59d_rain_mm
4. fruit_60_89d_solar_mj_m2_day
5. fruit_90_to_harvest_temperature_c
6. vpd_pre_bloom_mean_kpa
7. vpd_early_fruit_p90_kpa

ตัวแปร VPD, climatology/scenario summaries และทุก derived weather dependency ถือเป็น weather
ตรวจ actual design-column whitelist และ lineage transitive dependencies ไม่ใช้เพียงชื่อคอลัมน์
ไม่มี ENSO/interaction ใน predictors ปัจจุบัน; ไม่เพิ่มหรือเลือก feature จาก Outer scores

ใช้ Fixed-calendar/Lead 60/5 จังหวัด/Outer 2017–2025/Inner 3 ปีก่อนเหมือน Phase 2
training starts 2010, ต้องครบ 80 panel rows และ 45 evaluation keys ต่อแขน ห้ามลดแถว
 shared fit cutoff = issue แรกสุดของ 5 จังหวัด เวลา 00:00 +07:00; train ใช้ปี < fold_year
training inputs/labels, lag, observed weather และ normal sources ตรวจ cutoff ทุก Outer/Inner
Inner selection labels ตรวจ ณ Outer selection cutoff; evaluation targets อ่านหลัง freeze ทุกแขน
seed 42, iterations 400, RMSE loss, Ordered, l2_leaf_reg=10, learning_rate=.03,
thread_count=1, allow_writing_files=False; candidate order depth 2 แล้ว 3 เป็น tie-break
ไม่มี early stopping/eval_set ด้วย Outer labels และไม่เลือก family ข้ามแขน

สร้าง audited full predictors สำหรับ With Weather ด้วย builder เดิม แล้วแยก projection ของ No Weather
ให้เหลือ province/year/lag ก่อนส่ง fit; weather lineage คงอยู่เฉพาะแขน With Weather
Manifest ของ No Weather ระบุ consumed dependencies แค่ calendar/issue_rule/annual_lag และ labels
ไม่อ้างว่า No Weather ใช้ weather เพราะ shared preparation คำนวณ matrix ของอีกแขน
ใช้ source snapshot/keyset/fold memberships เดียวกันทั้งสามแขน เพื่อตัด confounding จาก row filtering

## 4. Implementation หลังอนุมัติ (ยังไม่แก้ในรอบนี้)

- เพิ่ม `tools/durian_model/experiment_weather_ablation.py` เป็น isolated runner ไม่เปลี่ยน API ของ
  experiment_rebaseline.py / experiment_issue_date.py / shared Production helpers
  reuse prepare(), cutoffs, digest และ fit_predict เดิม แต่ explicit feature projections/arms
  และ validation/output schema สำหรับชื่อสามแขนใหม่ใน runner นี้
- เพิ่ม `tests/test_weather_ablation.py` ใช้ synthetic inputs และ mock fitter ไม่ฝึกเพื่อทดสอบ
- เพิ่ม usage ใน `tools/durian_model/README_TH.md` หลังอนุมัติ และรายงานผลแยกหลังอนุมัติ Training
- Output root ใหม่ `training/weather_ablation_exploratory/<run_id>/` exclusive; default help,
  --prepare ไม่มี fit และ --train ต้องได้รับอนุมัติแยก ไม่เปิด training ในงาน preparation
- Cache ภายในรันเท่านั้น; key มี protocol_sha256, arm/ordered feature-set hash, candidate parameters,
  fold year, fit/forecast cutoffs และ consumed predictor/label digest ไม่ใช้ evaluation targets
  ไม่โหลด Phase 2 model/predictions/tuning มาใช้ใน selection; ใช้เป็น read-only consistency reference
- canonical protocol hash ครอบคลุม calendar, years/provinces/order, feature sets/design, grid, seed,
  cutoff/normal/lag/selection policies; ไม่รวม timestamp/run_id ที่ไม่เปลี่ยน semantics
  code/data/manifest/lineage hashes เก็บแยกและผูก run provenance ไม่ให้ labels/target ถูกซ่อนใน predictors
- เก็บ immutable config, versions/dependencies, fold cutoffs, consumed lineage per arm, availability,
  tuning, choices, fit audit, predictions และ artifact inventories ก่อน/หลังรัน
  snapshot source แบบ allowlist ไม่รวม secrets; hashes อย่างเดียวไม่ทำให้ vintage verified

## 5. Tests ที่ต้องเพิ่มก่อน Training

1. Exact predictor/design whitelist: No Weather 7 columns, With Weather 14; ไม่มี target/area/production
   และ reject unknown/derived weather columns ใน No Weather รวม weather descendant lineage
2. Weather poisoning: เปลี่ยน weather ทั้งเจ็ดใน valid audited fixture ไม่เปลี่ยน No Weather matrix,
   mock predictions หรือ depth selection; ต้องเปลี่ยน With Weather inputs อย่างน้อยหนึ่งตัว
3. Future weather/normal poisoning: observed หลัง issue-7 หรือ normal ปีปัจจุบัน/อนาคตเข้าไม่ได้
   อิง actual builder traces ไม่ใช่ metadata ที่แต่ง; cutoff ทุก 36 nested contexts
4. Target poisoning: Outer target ไม่เปลี่ยน predictors/preprocessing/choices/predictions ของ fold นั้น
   แต่ยอมเปลี่ยน evaluation metrics; Inner labels ใช้ selection ได้หลัง audited publication policy เท่านั้น
5. Missing/duplicate year, province, predictor, lineage, source record, train/selection label หรือ fold:
   fail ก่อน fit; ห้าม inner join/drop/fallback ทำให้จำนวนแถวลด
6. Independent depth selection: mocked Inner losses เลือกต่าง depth ในสองแขนได้; ties เลือก depth 2
   ทั้งสองไม่อ่าน Outer targets; reject seed/grid/calendar/validation overrides
7. Cache isolation: candidate index/depth เดียวกันต่างแขนไม่ reuse; changed features/parameters/cutoffs/
   source content/protocol เปลี่ยน key หรือ fail; identical same-arm context reuse ได้; stale signature fail
8. Artifact isolation: refuse existing directory, traversal/symlink/wrong root; ห้ามอ่าน old predictions
   เป็น input; --prepare/default ไม่ fit; mismatched inventories/provenance fail ก่อน training
9. Metrics: ต้องครบ 135 predictions บน 45 keys; paired weather gain/sign, wins/ties/losses,
   province/year aggregation, depth switches และ worst signed errors ตรวจด้วย fixture ค่าที่รู้แน่นอน
10. With Weather preparation regression: issue/features/cutoffs ตรง Phase 2 snapshot; หลังอนุมัติ Training
    จึงตรวจ fresh With Weather predictions เทียบ Phase 2 ภายใต้ dependency versions เดียวกัน
    ความต่างเกิน numerical serialization tolerance ต้องหยุด ไม่ปรับ protocol เพื่อให้คะแนนตรง
11. Production/input/code hashes ก่อน/หลัง และ no writes สู่ old artifacts/API/Frontend

ทดสอบสิ่งเหล่านี้ร่วมกับ suite เดิมก่อนขออนุมัติฝึก; ไม่ hard-code ว่า weather ต้องชนะ

## 6. ตารางผลและขอบเขตการสรุป (เตรียม schema ยังไม่มีคะแนนใหม่)

Overall/by_year/by_province: model, n, MAE, RMSE, Bias=prediction−actual, median AE
Paired rows: province, year, issue_date, actual, predictions/errors ทั้งสามแขน,
weather_gain=|error No Weather|−|error With Weather| และ gain ของแต่ละ CatBoost เทียบ Last-year
Weather contribution รายปี/จังหวัด: mean/median paired gain, MAE difference, RMSE difference,
Bias ของแต่ละแขน, relative MAE reduction (ถ้า denominator=0 ให้ missing), wins/ties/losses
Choices/tuning: arm/year/depth, Inner losses ทั้งสอง depth, winner margin, depth switches
Worst errors: signed/absolute error สูงสุดของแต่ละแขนและ largest paired weather loss พร้อม key

กำหนด gain บวก=weather ช่วย; ไม่อ้างนัยสำคัญจาก 45 แถวที่สัมพันธ์กันตามจังหวัด/ปี
การเลือก depth แยกแต่ละแขนวัดคุณค่าของ weather-enabled pipeline รวมผลการจูน ไม่ใช่ causal effect
ของ weather ที่ตรึงโมเดลเหมือนกัน และไม่ใช่หลักฐานความเครียด/น้ำใต้ดิน/กลไกพืชโดยตรง
ไม่มี archived forecast; future weather ใช้ climatology, POWER เป็น revised meteorology/reanalysis;
OAE labels/lag ยังไม่มี historical vintage evidence จึง Exploratory ไม่ใช่ PIT Certified
ปี 2017–2025 เคยเห็นแล้ว ไม่ใช่ independent confirmation set; ไม่มีการเปลี่ยน Production จากคะแนนรอบเดียว

## 7. ผลตรวจปัจจุบันและการหยุดรอ

รัน Python ทั้ง repository: 211/211 ผ่าน; JavaScript: 30/30 ผ่าน ไม่มี failure ใหม่
suite เดิมมี model-fit unit fixtures บางส่วนและ mocked training tests ไม่ใช่ Phase 3 experiment run
Production model SHA256 ตรงค่าที่บันทึก:
`B4B9E0985E6BA5E6EE371D8988CAD5E65DEE031B345EB0CF13A8695F91658680`
ไม่แก้โค้ด/tests/manifest หรือ artifacts เดิม; Git มี dirty/untracked เดิม เก็บไว้ไม่ reset/commit
ตรวจ hashes ก่อน/หลังเขียนรายงานของ source/tests/API/Frontend และ old artifacts ที่เลือกไว้ 92 ไฟล์
ไม่พบการเปลี่ยนแปลง; git whitespace check ของรายงานผ่าน มีเพียงคำเตือน LF/CRLF
สกิล Ponytail ใช้จำกัด scope เป็น read-only audit และเสนอ isolated runner ที่ reuse helpers เดิม
รออนุมัติ implement Preparation/Tests ก่อน และต้องมีอนุมัติ Training แยกต่างหาก
