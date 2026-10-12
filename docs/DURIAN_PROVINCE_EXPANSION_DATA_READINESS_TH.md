# Phase 6A — Province Expansion Data Readiness

วันที่ตรวจ: 11 ตุลาคม 2026 — **เตรียมข้อมูลเสร็จสำหรับ Exploratory; ยังไม่ฝึกโมเดล และไม่ใช่ Historical PIT Certified**

## ข้อมูลที่ผ่าน

Run ใหม่: `research_data/province_expansion_inputs/phase6a_20261011T134340704642Z/`

| จังหวัดเพิ่ม | รหัส | Daily weather 2000–2025 | Annual target 2010–2025 | Lag 2009 | Anchor |
|---|---|---:|---:|---|---|
| ระยอง | 21 | 9,497 วัน | 16 ปี | ครบ | 04-01 |
| นครราชสีมา | 30 | 9,497 วัน | 16 ปี | ครบ | 05-01 |
| ประจวบคีรีขันธ์ | 77 | 9,497 วัน | 16 ปี | ครบ | 06-01 |
| นครศรีธรรมราช | 80 | 9,497 วัน | 16 ปี | ครบ | 07-01 |
| ระนอง | 85 | 9,497 วัน | 16 ปี | ครบ | 07-01 |

- ใหม่รวม 47,485 daily rows; ไม่มี missing/fill/nonfinite ใน 7 source parameters และไม่มีวันขาด/ซ้ำ
- Annual snapshot รวมเดิมและใหม่ 170 แถว (2009–2025): พื้นที่ให้ผลต้องมากกว่า 0, ผลผลิตต้องไม่ติดลบ และ target = tonnes × 1,000 / bearing rai; ไม่ใช้ค่าผลผลิตต่อไร่ที่ปัดเศษใน source
- Calendar ใหม่ตามแผนเดิม: ปริมาณผลผลิตรายเดือนที่มีจริง 2004–2009 reconcile 6/6 ปีต่อจังหวัด; pooled peaks 5/6/7/8/8 และฤดู proxy 3 เดือน คง anchors เดิมของจังหวัดเก่า
- เดือนที่ไม่มีแถวไม่ถูกเติมเป็นศูนย์; calendar นี้ยังเป็นกฎทดลองสร้างในปี 2026 ไม่ใช่ historical predeclared calendar

## วิธีเตรียม Weather และ Lineage

ใช้ [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) แบบ AG / JSON / LST และ 7 source parameters เดิม:
`T2M,T2M_MAX,T2M_MIN,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN,WS2M`.
รังสีมีหน่วย `MJ/m²/day`; WS2M เก็บไว้ตามนิยาม downloader เดิม แต่ไม่เพิ่มเป็น predictor.

ดาวน์โหลด 15 ช่วงข้อมูล (2000–2009, 2010–2019, 2020–2025 ต่อจังหวัด) พร้อมเก็บ bytes จริง, SHA256, URL/request, retrieval timestamp และ response metadata. API version ที่ได้รับ `v2.10.0`; source models ที่พบรวม `MERRA2, POWER, SRB, SYN1DEG` โดยเก็บ header แยกแต่ละ request ไม่เหมารวมว่าทุกช่วงใช้ source เดียวกัน.

พิกัดเป็น **province reference proxy ไม่ใช่พิกัดหรือค่าเฉลี่ยสวนจริง** ตาม national dataset เดิม. ช่วง 2000–2025 เพียงพอสำหรับ climatology ย้อนหลัง 10 ปีของแถวเริ่มปี 2010; ไม่มีการโหลดใหม่หรือแก้ weather ของจังหวัดเก่า.

เรียก `IssueWeather.features_with_lineage` เดิมโดยตรง: อายุผล 140 วัน, issue lead 60 วัน, weather lag 7 วัน, หน้าต่างและ reducers เดิมทั้งหมด. หลังวันตัดใช้ prior-year climatology ตามวิธีเดิม ไม่ใช่ Historical Weather Forecast.

ได้ predictors 160 จังหวัด–ปี (2010–2025 × 10 จังหวัด), 1,280 actual feature traces: lag 1 ตัว + weather 7 ตัวรวม VPD. Traces ผูก observed/normal dates, consumed-value/component hashes และ reducer กับค่าที่ Feature Builder ใช้จริง. ไม่มี target/พื้นที่ให้ผล/production/ENSO ใน predictor table.

## Fold และการรักษา Protocol

- 36 nested contexts ต่อ cohort รวม 72 contexts สำหรับ 5/10 จังหวัด; Outer 2017–2025, Inner 3 ปีก่อน Outer, train เริ่ม 2010
- ตรวจ 130,887 dependency consumptions: feature 124,740; training label 5,130; selection label 405; evaluation target 540; issue rule 72
- ตรวจ consumed observations/normals/lag/training labels ณ fit cutoff และ inner selection labels ณ outer selection cutoff; evaluation references แยก role และอนุญาตให้เป็นข้อมูลจริงภายหลัง
- ไม่พบ reference period หลัง cutoff ใน consumptions ที่ไม่ใช่ evaluation targets; climatology ไม่ใช้ปีของ row หรือปีอนาคต
- Shared Fit Cutoff ของ cohort 10 เท่ากับ cohort 5 ทุก context: Outer 31 มกราคมปกติ / 1 กุมภาพันธ์ใน 2020 และ 2024 เวลา 00:00 +07:00
- Selection cohort ยังคง 5 จังหวัดเดิม; labels ของจังหวัดใหม่ถูกตรวจ availability แต่ไม่อนุญาตให้ใช้เปลี่ยน selection objective
- Primary evaluation keys เดิมครบ 45; secondary จังหวัดใหม่ 45 แยกต่างหาก
- Target/Lag จังหวัดเดิมตรงเดิม; Weather Features ของเดิมทั้ง 80 จังหวัด–ปีเทียบ Phase 2 ได้ **max absolute difference = 0.0**

Manifest คง 2×2: A=5/No Weather, B=5/With Weather, C=10/No Weather, D=10/With Weather. No Weather ระบุ lag เท่านั้นร่วมกับ province/year identifiers; With Weather เพิ่ม weather เดิมทั้ง 7 ตัว. Grid depth 2/3, seed 42, parameters เดิมคงไว้. **ยังไม่มี estimator, cache reuse, hyperparameter selection หรือผลทำนายของการขยายจังหวัด**; การตรวจ model-level 2×2/encoding/cache/selection ต้องทำก่อน Training ใน Phase ถัดไป ไม่อ้างว่า data preparation แทนการตรวจเหล่านั้นได้.

## สิ่งที่ยังขาด / ข้อจำกัด

1. Manifest dependencies 62 records เป็น `unverified` ทั้งหมด: OAE revised snapshot, POWER current retrieval และ calendar provenance ยังไม่มี version-specific historical publication evidence. มี unverified warnings ใน 130,347 consumptions ที่ไม่ใช่ evaluation references. วันที่ดาวน์โหลด **ไม่ถูกใช้แทน publication date**.
2. ไม่สามารถรับรอง Revised Data Leakage/Historical PIT แม้ consumed-date guards ผ่าน. NASA reanalysis/revised data และ prior-year climatology ไม่เท่ากับ forecast ที่ออกจริง ณ historical issue date.
3. Annual target เป็นทุเรียนรวมพันธุ์ ไม่ใช่หมอนทองล้วน; ไม่อ้างว่าจังหวัดใหม่มี cultivar/ฤดูเดียวกันทั้งหมด.
4. พิกัดจุดเดียวมี spatial aggregation uncertainty; calendar เป็น season proxy และไม่ใช่ surveyed anthesis.
5. ยังไม่มีผลคะแนนขยายจังหวัด จึงไม่สรุปว่าการเพิ่มจังหวัดทำให้ MAE ดีขึ้น.

## Tests, ปัญหาที่พบ และ Protected Files

- Python ทั้ง Repository รอบสุดท้าย: **257/257 ผ่าน** (`unittest discover -s tests -q`, 184.270s); เดิม 245 + ใหม่ 12
- JavaScript ทั้ง Repository: **30/30 ผ่าน** (`node --test tests/*.js`)
- Tests ใหม่ครอบคลุม cohorts/keys, target/lag ขาดหรือซ้ำ, invalid targets, calendar source/ปีขาด, leap/shared cutoffs, missing parameters/dates/fill values, หน่วย/LST/physical invalidity, exclusive artifacts, source hashes และ actual lineage ที่มี future weather/climatology/wrong lag
- Tests เดิมที่เรียก training orchestration ใช้ synthetic/mock fitters ตาม test contract; **ไม่ได้รัน exploratory training ของ Phase 6A**
- พบ parser bug ในสคริปต์ใหม่: อ่านทั้ง percentage และ tonnes รายเดือนจนดูเหมือน duplicate calendar records. แก้ให้กรอง `ปริมาณผลผลิตรายเดือน` เหมือน Audit เดิม; ไม่เติมเดือนหรือผ่อนเกณฑ์. Failed snapshot `phase6a_20261011T134118161720Z/failure.json` เก็บไว้ ไม่ลบ/เขียนทับ.
- Snapshot source-only แบบ allowlist และ hash inventory เก็บใน run; ไม่รวม environment/secret files. Artifacts เดิม 42 ไฟล์ใน preparation seal ตรวจตรงทั้งหมด และ supplemental verification แยกไฟล์ใหม่.
- ไฟล์เดิมที่บันทึก hash ก่อนงาน **684/684 ไม่เปลี่ยน** รวม protected Production/API/Frontend และ artifacts เดิม; collector ของ preparation ตรวจ 685 ไฟล์ (เพิ่มสคริปต์ใหม่ขณะเริ่ม run).
- Production SHA256: `b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

## ไฟล์ใหม่และการใช้งาน

- `tools/durian_model/experiment_province_expansion.py`: prepare-only runner, exclusive run_id, fail-fast data/lineage/fold audit; ไม่มี train option
- `tools/durian_model/audit_province_expansion_inputs.py`: ตรวจ sealed artifacts/source/code hashes/cutoffs/keys และสร้าง verification แบบไม่เขียนทับ
- `tests/test_province_expansion_preparation.py`: regression tests ใหม่ 12 ข้อ
- รายงานนี้ และ input run ใหม่ (`raw/`, `annual.csv`, `new_weather_daily.csv`, `predictors.csv`, `feature_lineage.json`, `manifest.json`, `folds.json`, `availability_checks.json`, `evaluation_keys.json`, `config.json`, `source_metadata.json`, `weather_quality.csv`, `verification.json`, snapshots/hashes)

ตรวจ QC ราย parameter ได้จาก `weather_quality.csv` (35 แถว); ความครบถ้วนและ availability warnings จาก `verification.json`.
สั่ง prepare ใหม่ได้ด้วย `.build/national-analysis-venv/Scripts/python.exe -X utf8 tools/durian_model/experiment_province_expansion.py --prepare`; จะสร้าง run ใหม่เสมอ ไม่เขียนทับของเดิม.
Audit CLI ใช้กับ run ที่ยังไม่มี verification เท่านั้น; ถ้ามีแล้วจะปฏิเสธการเขียนทับ.

**หยุดรออนุมัติก่อน Training; ไม่เริ่ม ENSO, Province Expansion Training หรือแก้ Production.**
