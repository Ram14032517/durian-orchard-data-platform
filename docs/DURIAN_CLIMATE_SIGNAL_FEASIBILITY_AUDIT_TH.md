# Climate Signal Feasibility Audit — Lead 60 วัน

วันที่ตรวจแหล่งข้อมูล: 11 ตุลาคม 2026 (Asia/Bangkok)
Audit/แผนเท่านั้น: ไม่แก้ Production/Pipeline/API/Frontend ไม่ฝึกโมเดล
เก็บ DURIAN_PROVINCE_EXPANSION_PLAN_TH.md เดิมไว้โดยไม่เปลี่ยน

## ข้อสรุปเพื่อเลือกงานต่อ

เสนอทำ **ENSO Outlook vintage inventory แบบไม่ fit ก่อน**: เป็นทางเลือกต้นทุนต่ำกว่า
Seasonal Forecast แบบกริด และตรวจวันออกเอกสารได้จาก archive ที่พบ
ยังไม่พร้อมเพิ่ม features ทันที และยังไม่มีหลักฐานว่าดีกว่า Province Expansion
หาก inventory ไม่ครบ 2010–2025 ให้หยุด ไม่ลดปีฝึก/ปีทดสอบเพื่อให้รันผ่าน
Province Expansion มีความพร้อมด้าน annual targets สูงกว่า แต่ต้องเตรียม daily weather ใหม่
Seasonal rainfall/temperature forecast ตรงโจทย์อากาศอนาคตมากกว่า แต่มีต้นทุนและ vintage gaps สูงสุด

## 1. สิ่งที่มีอยู่ในโครงการ

อ่านเฉพาะ expansion plan, PIT audit/issue-date report, enso_context.json,
experiment_climate_age.py และข้อมูลอ้างอิงจากแหล่งทางการ ไม่สำรวจ repo ใหม่ทั้งหมด
ใช้แนว Ponytail จำกัดงานเป็นรายงานและ decision gates ไม่สร้าง connector หรือ abstraction ใหม่

- `enso_context.json`: observed 424 รายการ = ONI 212 + RONI 212, ปี 2009–2026
  เป็น revised snapshot ที่ดึง 2026-10-09; ตรวจ snapshot hashes ตรงทั้ง 3 แหล่ง
- Forecast ที่เก็บในไฟล์นี้เป็น RONI outlook เดือนตุลาคม 2026 ไม่ใช่ archive 2010–2025
  issued_day เป็น null / month_only จึงยังไม่พอสำหรับ cutoff รายวัน
- experiment_climate_age ใช้ RONI หลังสามเดือนของ season จบตามปฏิทิน
  แต่ season จบไม่เท่ากับข้อมูลเผยแพร่แล้ว; ไม่ reuse ผลนี้เป็นหลักฐาน PIT
  โค้ดระบุเองว่า probabilities ปัจจุบันไม่ใช้สร้าง test inputs ในอดีต
- ยังไม่มี climate forecast archive ที่ครบทุก input/fold ของ protocol นี้

Observed climate indices ที่นำมาใช้ตอนนี้อาจทำ exploratory revised-data study ได้
แต่ไม่ยืนยันว่าเป็นค่าที่มีจริง ณ historical issue date

## 2. เปรียบเทียบแหล่งข้อมูลและความพร้อม

| แหล่ง/ผลิตภัณฑ์ | Historical coverage ที่พบ | Issue-date vintage | ความพร้อมต่อ protocol |
|---|---|---|---|
| NOAA ONI / Niño 3.4 index tables | ONI มีประวัติตั้งแต่ 1950; local snapshot 2009–2026 | ตารางปัจจุบันปรับย้อนหลัง ไม่ใช่ historical release archive | ใช้ revised values ได้เฉพาะ exploratory; ต้องหา bulletin ที่ลงวันที่สำหรับ as-issued values |
| NOAA CPC ENSO diagnostic / outlook | เปิดเอกสารลงวันที่ Jan 2017 และ Jan 2025 ได้ | มี issuance date ในตัวเอกสาร; probabilities บางส่วนเป็นภาพ/link ต้องตรวจรุ่นที่ link ชี้ | candidate ดี แต่ยังไม่ได้ตรวจครบทุกปี/เดือนที่ต้องใช้ |
| IRI ENSO forecast archive | index มี 2002–2013; เปิด Jan 2010 และ Jan 2017 ได้ | Jan 2010 update ลงวันที่ 21 Jan; Jan 2017 แยก CPC 12 Jan กับ plume 19 Jan | มีทางครอบคลุมปีฝึกต้น ๆ; ต้องตรวจทั้ง source-family และวันออกแต่ละชุด |
| NMME precipitation/2m temperature | realtime เริ่ม Aug 2011; directory มี 2017–2025; มี hindcasts 1982–2010 | พบรายรันและไฟล์ GRIB แต่ init/mtime ไม่ใช่ publication proof | ยังไม่ครอบคลุมปีฝึก 2010 แบบ realtime; ห้ามแทนด้วย hindcast เงียบ ๆ |
| Copernicus C3S seasonal | catalog ระบุ 1993–2016 hindcasts, 2017–present forecasts | ต้องแยก origin/system/version และ release time จาก initialization | ใช้ศึกษาได้ แต่ปีฝึก 2010–2016 ไม่ใช่ forecast ที่ออกจริงตามบริการนี้ |
| TMD คาดหมายราย 3 เดือน | พบหน้าบริการและเอกสารรายฤดู; ยังไม่พบ archive สมบูรณ์ 2010–2025 ในรอบนี้ | ต้องตรวจวันที่ในเอกสาร/รุ่นก่อน issue; URL latest อาจทับไฟล์ | ใช้ประกอบความเข้าใจประเทศไทย; ยังไม่พร้อมเป็น reproducible predictor |

หลักฐานดัชนี: [NOAA ONI definition/revision](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v5/)
ระบุ ONI เป็นค่าเฉลี่ยสามเดือนของ Niño 3.4, baseline ปรับทุก 5 ปี
และค่าอาจปรับถึงสองเดือนหลังเผยแพร่ครั้งแรก; ปัจจุบัน official monitoring ใช้ RONI
ดังนั้น Niño 3.4 monthly anomaly, ONI และ RONI ไม่ใช่ตัวแปรเดียวกัน
ห้ามต่อ series/threshold probabilities ข้ามนิยามโดยไม่บันทึก product regime

ตัวอย่าง archive ENSO: [IRI Jan 2010 update](https://iri.columbia.edu/our-expertise/climate/forecasts/enso/archive/201001/update.html)
กับ [Jan 2010 probability table](https://iri.columbia.edu/our-expertise/climate/forecasts/enso/archive/201001/figure3.html)
และ [IRI Jan 2017](https://iri.columbia.edu/our-expertise/climate/forecasts/enso/2017-January-quick-look/?enso_tab=enso-sst_table)
มีวัน/ฤดูและตาราง probability ให้จับคู่กัน แต่ CPC consensus กับ IRI plume ออกคนละวัน
ต้องเลือกผลิตภัณฑ์ล่วงหน้า ไม่สลับตามคะแนนหรือเลือกอันที่มั่นใจที่สุดภายหลัง

[CPC Jan 2017](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_disc_jan2017/ensodisc.shtml)
ลงวันที่ 12 Jan 2017; [CPC Jan 2025](https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_disc_jan2025/ensodisc.shtml)
ลงวันที่ 9 Jan 2025 และบันทึกค่า weekly Niño 3.4 กับ outlook ที่ทราบขณะนั้น
เป็นหลักฐานที่ดีกว่าตารางดัชนีปรับปรุงปี 2026 แต่ตัวอย่างสองเดือนนี้ไม่พิสูจน์ coverage ทั้ง 45 keys

[NMME guide](https://www.cpc.ncep.noaa.gov/products/NMME/users_guide.html)
แยก hindcasts/realtime และกำหนดรอบเผยแพร่ nominal หลังต้นเดือน
catalog/archive บอกว่ามีข้อมูล ไม่พิสูจน์ bytes รุ่นเดิมทุกไฟล์
ตรวจ [Jan 2017 files](https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/ENSMEAN/2017010800/)
พบ prate/tmp2m และ timestamp 9 Jan 2017;
[parent index](https://ftp.cpc.ncep.noaa.gov/NMME/realtime_anom/ENSMEAN/)
กลับมี directory timestamp 1 May 2017 — ห้ามใช้ directory mtime แทน release
ยังไม่ดาวน์โหลด/ตรวจ GRIB metadata หรือยืนยัน bytes ว่าไม่เคยถูกเปลี่ยน
data-library link บางเส้นทาง redirect ให้ login; public CPC file listings เปิดอ่านได้

[C3S catalog](https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels?tab=overview)
มีกริด 1° และ ensembles, release schedule ปัจจุบัน 6th/10th 12 UTC ตาม provider
catalog publication date 2018-06-14 ไม่ใช่ release date ของทุก run ตั้งแต่ 2017
ต้องตรวจ release/version ของรันเก่าเป็นรายผลิตภัณฑ์ ไม่เอาตาราง schedule ปัจจุบันย้อนรับรองทั้งหมด

TMD: [seasonal service](https://weather.tmd.go.th/seasonal/index.html)
และ [three-month forecast listing](https://www5.tmd.go.th/forecast/threemonthcountry?page=1&show=10)
หน้ารายการหลังเปิดผ่านเครื่องมือไม่สำเร็จในรอบนี้ แม้ค้นพบรายการจาก search
จึงไม่อ้างว่าข้อมูลไม่มี หรือครบ; หากเลือกทางนี้ต้องขอ/ตรวจ archive เพิ่ม

## 3. ตัวแปรใดทราบจริง ณ issue date

| สิ่งที่เสนอ | ใช้ได้เมื่อ | ห้ามใช้แทน |
|---|---|---|
| Niño 3.4 ล่าสุด | ค่าจาก bulletin/product รุ่นลงวันที่ก่อน issue; observation period/นิยามชัด | ค่า final/revised ของเดือนเดียวกันในไฟล์ปี 2026 |
| ENSO outlook | issued_at/released_at <= issue และ valid season ตรง window ที่ล็อก | ENSO phase ที่สรุปภายหลังทั้งปีหรือ outlook ฉบับปัจจุบันย้อนหลัง |
| Seasonal rain/temp | forecast run ที่เผยแพร่ก่อน issue พร้อม valid period/model version | observed future weather, reanalysis หรือ hindcast ที่ผลิตภายหลัง |
| Climatology | prior-year data และ calibration ตาม cutoff policy | future-year normals หรือ recalibration จาก test targets |

Forecast valid dates อยู่หลัง issue เป็นสิ่งที่ถูกต้อง ไม่ใช่ leakage หาก issuance ทัน cutoff
ส่วน observed ค่าเฉลี่ยที่รวมวันหลัง issue เป็น leakage แม้ชื่อ season ใช้เดือนกลางก่อน issue
ENSO ไม่ควรติดป้ายเป็นประเภทปีเดียว เพราะสถานะเปลี่ยนระหว่างเดือน/ฤดูได้
ให้ใช้ probability/index ตาม valid window ไม่บังคับ heat/fruit age/yield penalties

## 4. ความเหมาะสมกับ 5 จังหวัด / 9 ปีทดสอบ

คง 22 จันทบุรี, 33 ศรีสะเกษ, 53 อุตรดิตถ์, 84 สุราษฎร์ธานี, 86 ชุมพร
anchors 04/05/06/07/07-01, Lead 60, Outer 2017–2025, train เริ่ม 2010

- 45 Outer keys แต่มีเพียง 36 distinct provincial issue dates เพราะ 84/86 ออกวันเดียวกัน
  ต้องเตรียมครบ 80 input keys และ 64 distinct issue dates ของ 2010–2025
  Inner 2014–2024 อยู่ภายในช่วงนี้ ห้ามตรวจเฉพาะ Outer inputs
- Issue ช่วง Jan31/Feb1, Mar2, Apr2 และ May2 (leap year เปลี่ยนเฉพาะ issue ของ anchor Apr1)
  forecasts ต้นเดือนที่ยังไม่เผยแพร่ในวันนั้นต้องถอยใช้รันล่าสุดที่เผยแพร่แล้ว
  ตัวอย่าง Chumphon May2 ใช้ May6/May9 ไม่ได้ แม้ initialize May1
- Shared Fit Cutoff ยังคง issue แรกสุดในปีนั้น เวลา 00:00 +07:00
  training sources ต้องพร้อม ณ cutoff นี้; forecast ของจังหวัดที่ออกภายหลังอาจใช้
  release ภายหลัง fit ได้เฉพาะเป็น input ของการพยากรณ์จังหวัดนั้น ไม่ย้อนเปลี่ยน selection/model
- Lead 60 ถึงเริ่มฤดู ไม่ได้เท่ากับ lead 2 เดือนของผลิตภัณฑ์ทุกตัว:
  ต้องจับคู่ valid months/window จริง (รวม 3 เดือนฤดู) กับ lead ของ run
- ENSO เป็นสัญญาณระดับแปซิฟิก ไม่ใช่ฝนจังหวัดหรือสวน และค่าที่แชร์กันไม่เพิ่มจำนวนปีอิสระ
  ผลสัมพันธ์เฉพาะภูมิภาคต้องทดลอง ไม่สันนิษฐานว่าฝน/ผลผลิตต้องลดทุกจังหวัด
- Monthly/seasonal forecast เหมาะกับแนวโน้ม rain/temp มากกว่าวัน extreme
  ไม่สร้าง daily heat counts/dry spells/VPD p90 จาก monthly mean เสมือนเป็นข้อมูลจริง
  ระยะนี้เสนอเพิ่ม low-dimensional features แยก ไม่แทน weather 7 ตัวทั้งหมด

## 5. Leakage / Overfitting ที่ต้องป้องกัน

1. Revised ENSO/updated anomaly baseline, ยืนยัน season จบอย่างเดียวไม่พอ
2. Hindcast/reforecast ของโมเดลสมัยใหม่ไม่ใช่ operational run ของปีนั้น
3. Initialization date, publication date, valid dates, retrieved_at และ HTTP mtime ต้องแยก
4. Probability link/image อาจชี้ latest; ต้อง snapshot ตรวจวันที่ในเนื้อหาและ valid seasons
5. Historical ensemble composition และ bias adjustment เปลี่ยนได้; ไม่ใช้สมาชิกปัจจุบัน
   ย้อนสร้าง ensemble เก่าโดยอ้างว่าทราบแล้วในอดีต
6. Calibration/spatial sampling/window/feature normalization ต้อง frozen หรือ fitted ใน training
   ไม่ใช้ค่า weather/target ของ Outer ปีเดียวกันจูน source/threshold/model/lead
7. 9 ปี/45 targets กับสัญญาณ ENSO ร่วมกันมีข้อมูลอิสระจำกัด;
   ไม่เพิ่ม dozens of lags/season probabilities/province interactions/model ensembles พร้อมกัน
8. OAE training/selection label vintages และ POWER baseline ยัง unverified
   แม้ climate features verified ก็ไม่ทำให้ระบบทั้งหมด PIT-certified
9. Outer years ถูกเห็นจากหลาย phase แล้ว: ผลเป็น exploratory ไม่ใช่ holdout ใหม่

## 6. แผนแบบมี gate และจำนวนการทดลอง

### Gate 1 — Archive Inventory เท่านั้น (เสนอทำถัดไป; 0 model fits)

สร้าง source/vintage inventory ครบ 80 province-year input keys / 64 issue dates
รวมหลักฐาน bulletin family, SST/index definition, issued_at/released_at,
valid_start/end, initialization, source version/hash และ availability status
เลือกหนึ่ง family ที่มีต่อเนื่องก่อนดูคะแนน เช่น IRI model-based probabilities
ตรวจความต่อเนื่องจริงก่อนล็อก — ไม่ถือว่าตัวอย่าง Jan 2010 และ 2017 เท่ากับครบทั้ง series
latest-as-of join ต้องจำกัด released_at <= issue; date-only ใช้ conservative end-of-day
ใน source timezone ถ้าทราบ; หาก timezone/time ไม่ทราบและวันตรง cutoff ให้ unverified
เดือนอย่างเดียวต้องไม่สร้าง issued_day จากการเดา

เสนอ output หลังอนุมัติ: `docs/DURIAN_CLIMATE_VINTAGE_INVENTORY.csv`
fields: province_code,target_year,issue_date,fold_role,use_cutoff,product_family,
index_definition,source_version,issued_at,released_at,issuance_precision,
initialization_date,valid_start,valid_end,source_url,source_sha256,
retrieved_at,publication_evidence,availability_status,missing_reason
ไม่จัดทำไฟล์นี้ในรอบนี้เพราะยังไม่ได้ตรวจ records ครบ

### Gate 2 — ENSO minimal ablation หลังอนุมัติ implementation/training แยก

แนะนำเริ่มเพียง **2 แขน** บน old 45 keys:
control = CatBoost With Weather เดิม; treatment = control + outlook contrast
`P(El Niño) - P(La Niña)` สำหรับ 3 เดือน main-season ของจังหวัดนั้น
เก็บ probabilities ทั้งสามใน provenance แต่ไม่ใส่สามค่าที่รวมกันเท่ากับ 1 พร้อมกัน
ไม่คัด valid season ด้วย Outer scores; 1 feature เป็นการลดมิติ ไม่อ้างว่าแทน intensity ได้
ถ้า forecast ไม่มี main-season window/ผลิตภัณฑ์นิยามไม่ต่อเนื่อง ให้หยุด ไม่เติมจาก future outlook

Depth 2/3 จาก Inner 3 ปีก่อนแยกแขน; seed42/grid/cutoffs/features อื่นคงเดิม
ใช้ 36 nested contexts ต่อแขน ไม่มี cross-family Auto Select
With cache ที่ถูกต้องมี unique fits สูงสุดตามรูปแบบเดิม 23 ต่อแขน = 46 fits
หากไม่มี cache อาจมากกว่า; fit count ไม่ใช่จำนวนสมมติฐานทดลองอิสระ
optional observed Niño3.4 arm เป็นอีก 1 comparison/23 cached fits เฉพาะได้รับอนุมัติ
และนิยาม/coverage ผ่าน — ไม่เพิ่มในรอบแรกตามผล Outer
ไม่รัน Province Expansion พร้อมกัน เพื่อไม่ให้เปลี่ยนสองปัจจัย

### Gate 3 — Seasonal rain/temp (ยังไม่เสนอให้ implement ทันที)

ต้องแก้โจทย์ปีฝึก 2010 ก่อน: NMME realtime ไม่ครอบคลุม และ C3S pre2017 เป็น hindcast
ทางเลือกคือหา archived realtime family ที่ครอบคลุมจริง หรือขออนุมัติ protocol ใหม่ที่แยก
hindcast-derived training ว่า exploratory และสร้าง control ใหม่บน sample/cutoff เดียวกัน
ไม่ลด training start หรือผสม historical/reforecast โดยเงียบ ๆ
เมื่อผ่านจึงเสนอ control vs control + rain/temp anomaly bundle (2 features) เพียง 1 comparison
เก็บ model-run version/lead/bias-correction product และ grid weights; ไม่เริ่มทั้ง NMME/C3S/TMD แข่งกัน

## 7. ความคุ้มค่าและต้นทุนที่คาด

เป็นการประเมินงานวิศวกรรม ไม่ใช่ runtime benchmark/ราคาเสนอหรือรับประกันลด MAE

| ทางเลือก | ประโยชน์ที่ทดสอบ | งานใหม่หลัก | ต้นทุนสัมพัทธ์ | งบทดลองเริ่มต้น |
|---|---|---|---|---|
| ENSO Outlook | slow climate state ที่คาดไว้ก่อนฤดู ช่วยเพิ่ม signal หรือไม่ | archive parser + PIT joins/definition audit + 1 feature | ต่ำ–กลาง; เสี่ยง manual vintage cleanup | 2 arms / 1 comparison / ประมาณ 46 cached fits |
| Province Expansion | เพิ่ม training geography/ตัวอย่างช่วย old 5 หรือไม่ | 5 daily caches + generic cohort runner + 2×2 tests | กลาง; annual readiness ดีกว่า | 4 arms / 2 expansion contrasts / ประมาณ 92 cached fits |
| Seasonal rain/temp | local future climate ช่วยมากกว่า normals หรือไม่ | GRIB/NetCDF, spatial/lead extraction, calibration/version/vintage audit | สูง; training-era coverage gap สำคัญ | 2 arms / 1 comparison หลังผ่าน gate |

ENSO ดึงเอกสารขนาดเล็ก ไม่จำเป็นต้องใช้ GPU/บริการเสียเงินเพื่อ pilot;
Seasonal products ต้องตรวจ access terms/account/storage/library เพิ่ม
ไม่ประมาณค่าเงิน/วันทำงานตายตัวก่อน inventory เพราะความครบของ vintage ยังไม่ทราบ
งบที่ควบคุมได้คือ source family เดียว, 1–2 climate features, 1 comparison ต่อ gate
ไม่ไล่ source/grid/season window จากคะแนน

คำแนะนำ: ทำ ENSO archive completeness gate ก่อนเพื่อได้คำตอบด้วยต้นทุนต่ำ
หากผ่านค่อยขออนุมัติ minimal ablation; หากไม่ผ่านให้กลับ Province Expansion ตามแผนเดิม
ยังไม่มีเหตุผลให้ลงทุน seasonal ensemble ingestion เต็มระบบก่อนแก้ vintage/training-year gaps
ไม่อ้างว่า ENSO หรือเพิ่มจังหวัดจะได้ MAE ต่ำลงจนกว่าจะมี paired results จริง

## 8. ใช้งานปีใหม่และเกณฑ์ก่อนทดลอง

สามารถใช้ได้เชิงกลไกเมื่อ provider เผยแพร่ bulletin/run ก่อน issue และ schema/นิยามต่อเนื่อง
เก็บ immutable snapshots ตั้งแต่วันนี้เพื่อ prospective evaluation ปีใหม่
ไม่เติมค่าอนาคตเมื่อ service ช้า/ข้อมูลขาด; ติดป้าย signal unavailable และใช้ control เดิม
policy นี้ต้องกำหนดก่อนรันย้อนหลัง ไม่ใช้ fallback เพื่อซ่อน missing test samples
RONI vs ONI/product-version transition ต้องผ่าน compatibility audit ไม่ auto-migrate
ช่วงฤดูผลผลิตและข้อมูลสวนจริงยังเป็นคนละ resolution กับ provincial annual targets

Tests ที่เสนอหลังอนุมัติ: latest-as-of release boundary/timezone/date precision,
future/revised values poisoning, no forecast-valid/issued-date confusion,
probability sums/ranges, definition/version changes, exact 80/45 keys,
all Outer/Inner cutoff/labels, derived dependency isolation, missing-vintage fail-fast,
reference-control parity, cache/source hashes และ exclusive artifacts/production protection
รายงาน MAE/RMSE/Bias/paired errors รายปี/จังหวัด รวม worst AE และ depth stability
uncertainty แบบ year-block descriptive; ไม่อ้าง causal effect หรือ PIT certified

รอบนี้เพิ่มเฉพาะรายงานนี้ ไม่แก้โค้ด ไม่รัน training ไม่ดาวน์โหลด binary climate datasets
ไม่รัน full unit suite เพราะไม่มี implementation change; hash-check code/production/artifacts
และ expansion plan ก่อน/หลัง 284 ไฟล์: ไม่เปลี่ยน ตรวจ unique issues ได้ 36 Outer / 64 inputs ตามแผน
Production SHA256:
`b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680`

ข้อจำกัด audit: ตรวจหน้าแหล่งข้อมูล/ตัวอย่าง archive ไม่ได้ certify ทุก vintage/ทุก field
ยังไม่ได้อ่าน GRIB/NetCDF หรือตรวจ skill rain/temp ของกริดไทยจริง
ไม่มีหลักฐานว่าระบบผลผลิตทั้งหมด PIT-correct; หยุดรออนุมัติ Gate 1
