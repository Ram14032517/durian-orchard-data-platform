# Phase 4 — Province Expansion Audit & Plan

วันที่ตรวจ: 11 ตุลาคม 2026 (Asia/Bangkok)
สถานะ: เสนอแผนเท่านั้น ยังไม่ implement/download/train และไม่เปลี่ยน Production/API/Frontend
ผลในอนาคตต้องติดป้าย Exploratory retrospective — not Point-in-Time certified

## 1. ข้อมูลที่ตรวจจริงและผลตรวจ

อ่าน audit เดิม `docs/DURIAN_EXPANSION_AUDIT_TH.md`, inventory
`training/expansion_coverage.csv`, README/SOURCE ของ national comparison,
Phase 3 plan และโค้ด common/rebaseline/weather ablation/issue-date/manifest ที่เกี่ยวข้อง
ไม่รัน audit_expansion.run() เพราะจะเขียนทับ artifacts เดิม และไม่สำรวจ repo ใหม่ทั้งหมด
ไม่พบ AGENTS.md ที่ root; git มีการแก้ไข/ไฟล์ untracked เดิมจำนวนมาก จึงไม่ stage/reset/clean

ตรวจจากไฟล์จริงแบบ read-only:

- ตาราง annual มี 1,107 จังหวัด–ปี ไม่มี key ซ้ำ; ค่า production, bearing area,
  planted area และ source yield ตรงกับ OAE workbook ทั้ง 1,107 แถว
- พบ 30 จังหวัดที่ครบ usable targets ทุกปี 2010–2025 ตรงกับ inventory เดิม
  usable หมายถึง production/bearing เป็น finite, production >= 0 และ bearing > 0
  ไม่ใช่การรับรองคุณภาพการสำรวจหรือวันเผยแพร่ และไม่เติม missing เป็นศูนย์
- ข้อมูล 5 จังหวัดเดิม 145 แถว (1997–2025) ตรงกับตาราง national ทั้ง production,
  bearing area และ calculated yield; max delta = 0
- 5 จังหวัดที่เสนอมี annual 1997–2025 ครบ 29 ปี ไม่มี invalid target
  และมีปี 2009 สำหรับ lag ของแถว 2010 ครบทุกจังหวัด
- Monthly 2004–2016 reconcile กับ annual 13/13 ปีต่อจังหวัดตาม inventory;
  ตรวจซ้ำเฉพาะ 2004–2009 ได้ 6/6 ปีต่อจังหวัด (tolerance max(1 ตัน, 0.5%))
  ไม่ตีความเดือนที่ไม่มีแถวเป็นศูนย์แม้ยอดรวมตรงกัน
- Daily weather ของ experimental ปัจจุบันมีเฉพาะรหัส 22/33/53/84/86
  ตั้งแต่ 1981-01-01 ถึง 2026-09-25 จังหวัดละ 16,704 แถว
  national monthly weather 2021–2025 มีอยู่ แต่แทน daily windows/normals ไม่ได้
- Historical publication/vintage ของ OAE, POWER และ issue rule ยังไม่ verified
  วันที่ดาวน์โหลดหรือ data_date ของฉบับใหม่ไม่ใช่วันเผยแพร่ในอดีต

ชุดข้อมูลเป็นทุเรียนรวมทุกพันธุ์ ไม่สามารถอ้างว่าเป็นผลผลิตหมอนทองล้วน

### 30 จังหวัดที่ครบ 2010–2025

12 นนทบุรี; 20 ชลบุรี; 21 ระยอง; 22 จันทบุรี; 23 ตราด; 25 ปราจีนบุรี;
26 นครนายก; 30 นครราชสีมา; 33 ศรีสะเกษ; 53 อุตรดิตถ์; 54 แพร่;
64 สุโขทัย; 65 พิษณุโลก; 71 กาญจนบุรี; 76 เพชรบุรี; 77 ประจวบคีรีขันธ์;
80 นครศรีธรรมราช; 81 กระบี่; 82 พังงา; 83 ภูเก็ต; 84 สุราษฎร์ธานี;
85 ระนอง; 86 ชุมพร; 90 สงขลา; 91 สตูล; 92 ตรัง; 93 พัทลุง;
94 ปัตตานี; 95 ยะลา; 96 นราธิวาส

การมีเป้าหมายครบไม่เท่ากับพร้อมฝึก: ต้องผ่าน lag, weather, calendar, lineage
และ availability checks เพิ่มด้วย การคัดจากความครบถึง 2025 เป็น retrospective cohort
มีความเสี่ยง coverage/survivorship bias ไม่ใช่ province universe ที่รู้ล่วงหน้าในปี 2017

## 2. เสนอเพิ่ม 5 จังหวัด โดยไม่ใช้ Outer Scores

เดิม: 22 จันทบุรี, 33 ศรีสะเกษ, 53 อุตรดิตถ์, 84 สุราษฎร์ธานี, 86 ชุมพร

| เพิ่ม | เหตุผลก่อนดูคะแนน | Peak จาก monthly 2004–2009 | Anchor/ฤดู proxy ที่เสนอ |
|---|---|---|---|
| 21 ระยอง | annual/monthly ยาวครบ; เพิ่มตัวแทนตะวันออก | พฤษภาคม | 04-01 / เม.ย.–มิ.ย. |
| 30 นครราชสีมา | annual/monthly ยาวครบ; เพิ่มตัวแทนอีสานต่างพื้นที่จากศรีสะเกษ | มิถุนายน | 05-01 / พ.ค.–ก.ค. |
| 77 ประจวบคีรีขันธ์ | annual/monthly ยาวครบ; เพิ่มตัวแทนภาคตะวันตก | กรกฎาคม | 06-01 / มิ.ย.–ส.ค. |
| 80 นครศรีธรรมราช | annual/monthly ยาวครบ; ขยายพื้นที่ภาคใต้ฝั่งอ่าวไทย | สิงหาคม | 07-01 / ก.ค.–ก.ย. |
| 85 ระนอง | annual/monthly ยาวครบ; เพิ่มพื้นที่ภาคใต้ฝั่งอันดามัน | สิงหาคม | 07-01 / ก.ค.–ก.ย. |

ความหลากหลายภูมิอากาศ ณ ตอนนี้ใช้การกระจายภูมิศาสตร์/ฤดูเป็น proxy เท่านั้น
ยังไม่ได้วัดความต่างของ rain/VPD/solar ระหว่างจังหวัดใหม่ ต้องตรวจเมื่อมี daily data
ห้ามสรุปว่าจังหวัดใดแล้ง/ชื้นที่สุดจากตารางนี้
เลือกจากกลุ่มที่ audit เดิมเสนอไว้ ไม่อ่าน paired errors หรือจัดอันดับด้วย Outer target values
ตราดมีข้อมูลดีแต่เพิ่มตัวแทนตะวันออกซ้ำมากกว่าเป้าหมายกระจายพื้นที่;
พิษณุโลกเป็นตัวสำรอง ไม่สลับเข้าเพราะเห็นคะแนนไม่ดี

ข้อควรระวังเฉพาะนครราชสีมา: ปี 2009 bearing area 43 ไร่, production 17 ตัน
เป็นฐานเล็ก (ไม่ใช่ missing) จึงรายงานพื้นที่/ความผันผวนเพื่อประกอบการตีความ
ไม่ใส่ area เข้า predictor ไม่ลดน้ำหนักจังหวัดหรือปรับ cohort หลังเห็น Outer results

กฎ calendar ใหม่: รวม monthly ที่มีจริงเฉพาะ 2004–2009 หา peak แล้วใช้
start = max(1, min(10, peak_month - 1)), ฤดู 3 เดือนต่อเนื่อง; exact tie เลือกเดือนเลขน้อย
ตรึงกฎ/anchors ก่อน fit ทุก fold ไม่ใช้ peak รวม 2004–2016 ย้อนกำหนด Inner ปี 2014
คง anchors ของเดิมทุกจังหวัด ไม่คำนวณของเดิมใหม่เพื่อปรับคะแนน
แม้ใช้ปีข้อมูลก่อนฝึก แต่เป็น rule ที่ออกแบบในปี 2026 และ source ฉบับปรับปรุง;
ไม่ใช่หลักฐานว่าปฏิทินนี้ประกาศหรือทราบจริงก่อนปี 2010

## 3. Availability, Lineage, Issue Date และ Cutoff

| Dependency | ผล audit ณ ตอนนี้ | เงื่อนไขก่อน fit |
|---|---|---|
| Annual lag/training/selection labels ใหม่ | มีค่าจริง; publication/vintage unverified | separate roles; lag ต้อง source year = row year - 1; ตรวจทุก fold |
| Evaluation target | มี revised reference 2010–2025 | เก็บแยก predictors; ใช้หลัง freeze predictions เท่านั้น |
| Calendar/issue rule | anchors เสนอครบ; historical rule unverified | calendar-by-definition แยกจาก rule provenance; hash ตรึงก่อน fit |
| POWER observed ใหม่ | ยังไม่มี daily experimental inputs | หยุดก่อน fit หากไม่ครบ/พิกัด/หน่วยผิด; ห้ามเติม monthly/ศูนย์ |
| POWER climatology ใหม่ | ยังสร้าง/ตรวจ actual lineage ไม่ได้ | ทุก row ใช้ y-10..y-1; ตรวจวันที่ที่ consumed จริง |

Manifest ใหม่ต้องแยก records ตาม source/province/role; รองรับ verified_available,
verified_unavailable, unverified และ not_applicable เหมือน guard เดิม
Exploratory อนุญาต unverified พร้อม warnings แต่ไม่อนุญาต known-future records;
Strict ต้องปฏิเสธข้อมูล unverified ไม่มี publication date ห้ามแปลงเป็น verified
Training labels ตรวจ ณ fold fit cutoff; Inner selection labels ณ Outer selection cutoff
ไม่ใช้วันที่ 2026 ของ current edition แทนวันที่ historical vintage

Issue = anchor ใน target year - 60 วัน (calendar days, ไม่ใช่ 2 เดือน)
anchors ของใหม่ไม่มีจังหวัดใดก่อน 04-01 จึง min issue ของทั้ง 5 และ 10 จังหวัดเหมือนเดิม
Shared fit cutoff = min(issue ของ cohort) เวลา 00:00 +07:00:
2017/2018/2019/2021/2022/2023/2025 = 31 มกราคม;
2020/2024 = 1 กุมภาพันธ์ และใช้กฎเดียวกันใน Inner ปี 2014–2024
ห้ามเปลี่ยน min cutoff เพื่อเพิ่มข้อมูลฝึก; assert เท่ากันทั้งสี่แขนทุก nested context
พิกัด/anchor/lead เป็น immutable config ไม่เลือกใหม่จาก Outer scores

อากาศใช้ observed เฉพาะ <= provincial issue - 7 วัน (lag เป็นสมมติฐาน ไม่ใช่ verified release)
วันที่หลังจากนั้นใช้ prior-year climatology เดิม ไม่ใช่ archived weather forecast
ต้องมี daily source ครอบคลุมทุก observed date และ normal calendar day ที่ builder ใช้จริง
แถว 2010 ต้อง normals จาก 2000–2009; minimum 8 valid cells/day และ Feb29 rule เดิม
ห้าม relax coverage เพื่อลด missing หรือทิ้งแถวให้รันได้
Lineage ต้องออกจาก features_with_lineage() ของ actual builder ทั้งค่า/dates/source hashes
แล้ว replay ตรวจเทียบ inputs ไม่สร้าง metadata วันย้อนหลังจากสมมติฐานอย่างเดียว
ตรวจ row issue cutoff และ fold consumption cutoff ทั้ง train/forecast ทุก Outer/Inner

พิกัด national ที่มีอยู่เป็น representative_point ภายใน polygon จังหวัด ไม่ใช่สวน:
21=(12.87429,101.44464), 30=(14.96614,102.07023), 77=(11.80445,99.72466),
80=(8.57693,99.70082), 85=(10.04423,98.76673)
เสนอใช้จุดอ้างอิงเหล่านี้แบบติดป้าย proxy และตรึง source/coordinates ก่อนดาวน์โหลด
ไม่เปลี่ยน spatial resolution ของ 5 จังหวัดเดิมไปพร้อมกับ expansion
เก็บ source responses/parameters/units/hash แยก ไม่เขียนทับ weather_daily.csv เดิม
ยังไม่ยืนยัน weather comparability จนตรวจ product/version/missingness จริง

## 4. การทดลอง 2×2 ที่เสนอ

| แขน | จังหวัดที่ฝึก | Predictors | Design columns |
|---|---|---|---|
| A | เดิม 5 | province indicators + year + lag yield | 7 |
| B | เดิม 5 | A + weather 7 เดิม รวม VPD | 14 |
| C | รวม 10 | province indicators + year + lag yield | 12 |
| D | รวม 10 | C + weather 7 เดิม รวม VPD | 19 |

CatBoost ทุกแขน: depths {2,3}, seed 42, iterations 400, learning_rate .03,
l2_leaf_reg 10, RMSE loss, Ordered, thread_count 1, allow_writing_files False
ไม่เพิ่ม grid, features, early stopping หรือ Auto Select ข้าม family
Weather ทั้ง 7 ใช้ schema เดิมของ Phase 3: rain pre-bloom/0–29/30–59,
solar mean 60–89 (MJ/m²/day), temperature 90–harvest, pre-bloom mean VPD,
early-fruit p90 VPD; age proxy 140 วัน
No Weather ห้าม weather หรือ descendants รวม normals/coverage/ENSO/interactions เข้าสู่ design

Walk-forward: train เริ่ม 2010, Outer 2017–2025, Inner = Outer-3..Outer-1
fit แต่ละ inner ด้วยปี 2010..inner-1; Outer fit ใช้ 2010..outer-1
เลือก depth แยกแต่ละแขนจาก mean MAE ของ Inner บน 5 จังหวัดเดิมเท่านั้น
Inner loss มี 15 keys เท่ากันทั้งสี่แขน; depth 2 ชนะ exact tie
จังหวัดใหม่เพิ่ม training samples เท่านั้น ไม่เปลี่ยน selection objective ไปเป็น mean ของ 10 จังหวัด
Inner ของจังหวัดใหม่เป็น diagnostics ไม่ใช้เลือก depth/provinces/features
Outer targets ทุกจังหวัดแยกไว้ ไม่เข้าถึง feature engineering/preprocessing/tuning/fit
target ของปีก่อนอาจเป็น lag/training label ใน fold ปีถัดไปได้ตาม policy; ไม่ห้ามย้อนหลังทั้งหมด

ต้องครบ panel 80/160 keys (16 ปี × 5/10) และ lag source ปี 2009 ทุกจังหวัด
Inner แรก 2014 มี train 20/40 แถว; Outer แรก 2017 มี train 35/70 แถว
ทุก fold ต้องครบ exact province-year membership ไม่มี silent drop/inner join สูญแถว
คงแถวของ 5 จังหวัดเดิมจาก Phase 3, เพิ่มเฉพาะจังหวัดใหม่ ไม่เปลี่ยน target จาก rounded source yield
ใช้ production tonnes × 1000 / bearing rai เหมือนเดิม; reconcile old keys/values ก่อน fit

Primary evaluation keys = {22,33,53,84,86} × 2017..2025 รวม 45 keys ทุกแขน
Secondary keys = {21,30,77,80,85} × 2017..2025 อีก 45 keys เฉพาะ C/D
ไม่ส่งจังหวัดใหม่ให้ A/B ซึ่งไม่เคยเรียน province indicators ของจังหวัดเหล่านั้น
Last-year รายงาน reference แยก old/new cohorts ด้วย lag เดียวกัน ไม่ fit/จูน
ห้ามรวม 90 แถวแล้วเทียบ MAE กับ 45 แถวเพื่ออ้าง expansion ดีขึ้น

## 5. ผลที่ต้องรายงานหลังอนุมัติ Training

บน old 45 keys: MAE/RMSE/Bias (prediction - actual), รายปี/จังหวัด,
paired gain = AE(5 provinces) - AE(10 provinces) แยก No/With Weather,
ค่าเฉลี่ย/มัธยฐาน/ชนะ-เสมอ-แพ้ (นิยาม tie tolerance ล่วงหน้า เช่น 1e-9 kg/rai)
Weather gain = AE(No Weather) - AE(With Weather) แยกขนาด cohort
interaction = weather gain ของ 10 - weather gain ของ 5 รายคู่ และค่าเฉลี่ย
รายงาน depth choices/inner gaps/จำนวนสลับ depth/maximum AE/maximum degradation,
signed errors ของจันทบุรีและชุมพร ไม่รายงานแต่ MAE รวม
บน new 45 keys: C/D เทียบกันและ Last-year แยกตารางทุกจังหวัด/ปี
ไม่ใช้ผล secondary เลือกสมาชิกเพิ่มหลังรัน

ใช้ year-block uncertainty แบบ descriptive เก็บทุกจังหวัดในปีเดียวกันร่วมกัน
มีเพียง 9 ปีและ Outer years เคยถูกตรวจแล้ว ไม่ใช่ independent confirmatory holdout
ไม่อ้าง causal weather effect หรือความแม่น PIT-certified
การเพิ่มจังหวัดเปลี่ยน training sample และ province indicator dimension ตามการออกแบบ
แต่ไม่เปลี่ยนเวลาเริ่มฝึก/ปฏิทิน/grid/selection objective/feature bundle พร้อมกัน

## 6. ไฟล์ที่เสนอให้เพิ่ม/แก้เมื่อได้รับอนุมัติ

| ไฟล์ | หน้าที่ |
|---|---|
| tools/durian_model/experiment_province_expansion.py (ใหม่) | isolated runner/configured cohort, prepare/audit/train/report |
| tools/durian_model/province_expansion_manifest.json (ใหม่) | frozen old/new cohorts, anchors, points, source/dependency/availability roles |
| tests/test_province_expansion.py (ใหม่) | fail-fast, lineage, nested boundaries, isolation, reference parity |
| research_data/province_expansion_inputs/<snapshot_id>/ (ใหม่) | immutable annual/calendar/daily source snapshots + provenance ไม่รวม secrets |
| research_data/five_province_history/training/province_expansion_exploratory/<run_id>/ (ใหม่) | exclusive run outputs/config/hash inventory/fold cutoffs/metrics |
| tools/durian_model/README_TH.md | เพิ่มวิธี prepare/train หลังอนุมัติ implementation เท่านั้น |
| docs/DURIAN_PROVINCE_EXPANSION_RESULT_TH.md (ใหม่ ภายหลัง) | ผลจริงหลังอนุมัติและรัน Training |

ไม่แก้ common.PROVINCES/load_panel(), experiment_rebaseline หรือ Phase 3 global constants
เพราะ validate_panel/build_inputs/fold_dates/audit ผูก 5 จังหวัด/80 แถว/640 traces
ห้าม monkeypatch globals ให้ 10 จังหวัดแล้วเรียก callers เดิม
runner ใหม่ส่ง immutable cohort/calendar/source context ชัดเจน;
reuse IssueWeather/availability guard/design/fit_predict แบบ read-only ตาม interfaces เดิม
หากจำเป็นต้องเปลี่ยน shared helper/interface หรือไฟล์นอกขอบเขต ให้หยุดเสนออนุมัติก่อน

เก็บ config, code/data/manifest/protocol/actual lineage hashes, dependencies/runtime versions,
seed, source URLs/parameters/point versions, train/selection cutoffs ทุก fold และ source allowlist snapshot
cache key รวม cohort/order, calendar, arm/features, candidate, cutoffs, source/code hashes,
train predictors+labels และ forecast predictors; ไม่ใส่ Outer targets
ไม่ reuse cache/estimators จาก Phase 3 หรือข้าม 5/10 cohort
Phase 3 artifacts เป็น read-only parity reference เท่านั้น
reserve output directory ด้วย exclusive creation; default/prepare ไม่ fit
fail-fast หาก root ผิด, path traversal/symlink, run_id มีอยู่, sources/artifacts เปลี่ยน
ล็อกทั้ง production paths และ artifacts Phase 2/3 ก่อนและหลัง run

## 7. Automated Tests ที่ต้องเพิ่มก่อน Training

1. Exact cohorts 5/10, years, 80/160 panel keys, 45 primary/45 secondary keys;
   reject missing province/year/lag/dependency/duplicate/nonfinite ไม่ลดจำนวนตัวอย่าง
2. Source reconciliation: old targets/lags/issue dates/7 features เท่า Phase 3;
   5-province A/B fresh predictions/choices ต้องตรง Phase 3 ภายใน frozen tolerance
   หากไม่ตรงหยุด ไม่แก้เพื่อไล่คะแนนหรือโหลด predictions เก่ามาเป็นผลใหม่
3. Calendar poison: monthly ตั้งแต่ 2010 หรือ new Outer targets เปลี่ยน
   ต้องไม่เปลี่ยน frozen anchors/issue rules; reject anchor hash mutation
4. Shared fit/selection cutoffs เท่ากัน 4 แขนทุก 36 Outer/Inner contexts รวม leap years
5. Actual lineage replay ทุก feature/row/arm; weather future value mutation
   ไม่กระทบ features; missing dates/normals/daily params ต้อง fail
6. Climatology exclude row year/later, minimum coverage, Feb29 และ observation cutoff;
   ตรวจ consumed dates ผ่าน fold cutoff ไม่ใช่แค่ field name whitelist
7. Training/selection label role guards: known later publication/version mismatch fail;
   unverified มี warning ใน Exploratory และ Strict fail; evaluation revised target แยกไว้
8. No Weather exact design whitelist 7/12 columns + transitive dependency check;
   reject weather derivatives, area, production, target แม้เปลี่ยนชื่อคอลัมน์
9. Poison Outer target ของจังหวัดใหม่/เดิมใน fold เดียวกันต้องไม่เปลี่ยน features,
   preprocessing, candidates, chosen depth หรือ predictions ก่อน evaluation
   Inner targets ของจังหวัดใหม่ไม่เปลี่ยน selection เพราะ loss ใช้ old 5 เท่านั้น
10. Cache separation ทุก cohort/arm/year/point/source/manifest/cutoff/grid;
    wrong-context cache reuse ต้อง fail ไม่ใช้ candidate index อย่างเดียว
11. Artifact isolation: existing run/source/output root ต้องไม่ทับ, protected hashes unchanged;
    incomplete preflight ต้องหยุดก่อน fitter ถูกเรียก และ source snapshot ไม่รวม secrets
12. Reference parity + existing full Python/JS suites ก่อน/หลัง training;
    แยก unrelated failures ไม่ตีความ tests ผ่านเป็นหลักฐาน PIT

## 8. สถานะตรวจในรอบนี้ / ข้อจำกัด / ขั้นถัดไป

- รัน expansion audit unit tests: 3/3 ผ่าน; read-only source/inventory/overlap checks ผ่าน
- ไม่รัน full suite ใหม่ในรอบ report-only นี้; 225 Python/30 JS เป็นผลจาก Phase 3
  ต้องรัน full suite อีกครั้งหลัง implementation และก่อน Training
- ไม่มี training หรือคะแนน expansion ใหม่ ไม่มีการอ้างว่าการเพิ่มจังหวัดช่วยแล้ว
- ตรวจ Shared Fit Cutoff เท่ากันทั้ง 5/10 จังหวัดครบ 36 nested contexts ด้วย date arithmetic: ผ่าน
- Hash protected files ก่อน/หลังรายงาน 282 ไฟล์ไม่เปลี่ยน รวม Production และ artifacts Phase 2/3
  SHA256 Production ตรงค่าที่บันทึกไว้; git diff เดิมไม่ถูกแก้โดยงานนี้
- ข้อจำกัดคงอยู่: revised OAE/POWER vintages, rule สร้างปี 2026, all-cultivar annual target,
  point proxy ไม่ใช่สวน, main-season 3 เดือนกับ annual totals, climatology ไม่ใช่ historical forecast
- ขออนุมัติ implementation/data preparation ของแผนนี้ก่อน; จังหวัดใหม่ยังไม่ผ่าน
  actual weather lineage preflight เพราะไม่มี daily data จึงยังไม่พร้อม Training

### SHA256 ที่ตรวจ ณ audit

| Input | SHA256 |
|---|---|
| OAE durian_province.xlsx | 6a3ae44026b5ef8037a8bb091852281d890168a8d795c9c44d5cde9a48613d4c |
| OAE durian_monthly_province.xlsx | 461dab6a68ff2aca9bceb81e9a35b0137e77aff7ed9afb29054910ddf53cb62f |
| national production_province_year.csv | 017f6fd1eb3da5fc8bb6a7f340988228ac8fe2a6e3ece9e38264fa12ec07d425 |
| existing availability_manifest.json | 4d6e3b77d0f2561a5ce3dbb14ca322a21a03e7e4005d0153314c80b5cbbde827 |
| Production ridge_vpd_final_model.json | b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680 |

Hashes รับรอง bytes ที่ตรวจ ไม่รับรอง historical availability
