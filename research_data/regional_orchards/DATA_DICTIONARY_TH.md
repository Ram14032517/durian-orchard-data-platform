# Data dictionary / หน่วยข้อมูล

| ไฟล์ | grain / key | ความหมาย |
|---|---|---|
| soil_series_comparison.csv | province_code + soil_code | พื้นที่ซ้อนทับ A403/mixed กับหน่วยดิน |
| orchard_weather_samples.csv | sample_id | จุดใน A403 ต่อกรอบแบ่งชั้น 0.25° |
| sample_weather_monthly.csv | sample_id + year_ce + month | response NASA จัดรูป 14,160 แถว |
| orchard_weather_monthly.csv | province_code + year_ce + month | spatial weighted weather 960 แถว |
| orchard_weather_annual.csv | province_code + year_ce | อากาศรายปี 80 แถว |
| regional_province_year_panel.csv | province_code + year_ce | อากาศ join ผลผลิต 80 แถว |
| baseline_predictions.csv | province_code + year_ce | outcome + prediction แบบใช้ปีก่อน/5 ปีก่อน; 60 แถว |
| reference_point_comparison_2021_2025.csv | province_code + year_ce | เปรียบเทียบขอบเขตเชิงพื้นที่สองวิธี; 20 แถว |
| model_readiness.csv | province_code + landuse_year_be | พื้นที่ LDD เทียบ OAE ปีเดียวกัน, รายละเอียดหน่วยดิน, ปีข้อมูลก่อน footprint |
| landuse_code_inventory.csv | province_code + landuse_code + source_description_th | จำนวนระเบียนและพื้นที่ attribute จาก DBF เพื่อย้อนตรวจ A403/รหัสผสม |
| soil_resolution_review.csv | province_code + soil_code | soil summary เดิมเพิ่มป้ายสอบทานประเภทหน่วยดินที่เราคำนวณ |

## คอลัมน์สำคัญ

- province_code: รหัสจังหวัด 2 ตัว เก็บ string; year_ce: ค.ศ.; landuse_year_be/soil_year_be: พ.ศ.
- pure_rai: polygon LU_CODE=A403 ตรงตัว; mixed_rai: polygon ที่มี A403 ร่วมรหัสอื่นทั้งหมด ไม่ใช่ไร่ทุเรียนจริงในสวนผสม
- soil_name/soil_code: ค่าจาก DBF; SC/ES/W เป็นประเภทหน่วยแผนที่ ไม่ใช่ชื่อชุดดินละเอียดทั้งหมด
- share_of_A403_pct: pure_rai ซ้อนหน่วยนั้น ÷ A403 ทั้งจังหวัดรวมส่วนซ้อนไม่ได้ ×100
- textures/ph/fertility: คำบรรยายแผนที่ อาจหลายค่า; ไม่ใช่ผลตรวจแปลงปัจจุบัน ไม่แปลง pH คำบรรยายเป็นตัวเลขเอง
- longitude/latitude: WGS84 degrees จุดสาธารณะจาก LDD; API request ปัด 7 ตำแหน่ง ตรวจยังอยู่ใน A403
- A403_area_rai: พื้นที่ A403 ภายในกรอบ; weight: สัดส่วนต่อ A403 ทั้งจังหวัด; ผลรวม 1; ไม่ใช่ sampling probability ของต้น/สวน
- T2M / temperature_c: อุณหภูมิเฉลี่ย C; RH2M / humidity_pct: ความชื้นอากาศ %
- PRECTOTCORR: ฝนเฉลี่ย mm/day; rain_mm_month = rate×วันเดือน; rain_mm_year = รวมครบ 12 เดือน
- ALLSKY_SFC_SW_DWN / solar_mj_m2_day: รังสีอาทิตย์ MJ/m²/day ไม่ใช่ lux/PAR/NDVI
- *_area_coverage: ผลรวมน้ำหนักพื้นที่ของจุดที่มีตัวแปรนั้น; ไม่ครบ 1 ให้ค่าเฉลี่ย missing ไม่ renormalize กลบ
- complete_weather_months: จำนวนเดือนที่ทุกตัวแปรครบ; ตัวแปรเฉลี่ยรายปีถ่วงวันและต้องมี 12 เดือน
- fixed_snapshot_retrospective: true; footprint ปลูกคงที่จากปีไฟล์ ใช้มองอากาศย้อนหลัง ไม่ใช่พื้นที่ปลูกจริงทุกปี
- production_tonnes: ผลผลิตจังหวัดตัน; bearing_rai: เนื้อที่ให้ผลไร่; planted_rai: เนื้อที่ยืนต้นไร่
- yield_kg_per_rai_source: สถิติต้นฉบับ กก./ไร่; calculated: ตัน×1000/เนื้อที่ให้ผล แยกเพื่อไม่แก้ต้นฉบับ
- *_difference: orchard_weighted − province_point; ไม่ใช่ error เทียบ station ground truth
- previous_year / trailing_5yr_mean: prediction จากปีก่อนเป้าหมายเท่านั้น; MAE/RMSE เป็น กก./ไร่ ไม่ใช่เปอร์เซ็นต์ความแม่นยำ

`overlay_summaries.json` มีแหล่ง, ปี, CRS, พื้นที่ดิบ/union/covered/uncovered/overlap, geometry-repair deltas และ input hashes
`*_polygon_audit.csv` เก็บ source_record แบบ zero-based ใน shapefile เพื่อย้อนตรวจทีละ polygon
ค่าคลาด floating point ที่ใกล้ศูนย์ (ระดับ 1e-11 ไร่) คงไว้ใน audit; ตารางอ่านใช้ 0 เมื่อเป็นค่าลบระดับนั้น

## ความพร้อมก่อนโมเดล

- matched_oae_year_ce = landuse_year_be −543; ใช้สถิติปีเดียวกัน ไม่ใช่ปีล่าสุดทุกจังหวัด
- pure_to_oae_planted_pct / all_codes_to_oae_planted_pct: อัตราส่วนพื้นที่สองนิยาม ไม่ใช่ coverage หรือ accuracy
- algebraic_mixed_fraction_to_match = (OAE planted − LDD pure)/LDD mixed; diagnostic ไม่ใช่ estimate สัดส่วนทุเรียนจริง
- match_possible_with_fraction_0_to_1: flag ว่า f อยู่ใน[0,1]หรือไม่ ไม่ใช่ผลรับรองว่าข้อมูลสองแหล่งสอดคล้องกันแล้ว
- source_attribute_pure_rai: ผลรวมช่องArea_Rai/RAI หรือArea_Sqm/Shape_Areaหาร1600ตาม schema
- geometry_minus_source_area_rai: พื้นที่ที่คำนวณจากรูปทรงลบพื้นที่ attribute ต้นฉบับ ไม่ปรับตัวเลขให้ตรงกัน
- historical_years_before_landuse_snapshot: จำนวนyear_ce < ปีแผนที่CE; ไม่ใช่จำนวนปีที่พิสูจน์ว่าไม่มีสวนอยู่จริง
- named_single_unit_candidate_pct: สัดส่วนA403ที่รหัส/ชื่อดูเป็นชุดดินเดี่ยวตามกฎสอบทาน ยังไม่ยืนยันจากพจนานุกรมรหัส LDD รายชื่อทั้งหมด
- complex_or_association_pct: รหัสมีขีด/ทับหรือชื่อมีเชิงซ้อน/สัมพันธ์; ไม่แจกพื้นที่เป็นชื่อชุดดินเดี่ยว
- terrain_misc_unit_pct: SC/ES/RL/RC/AC ตามป้ายต้นฉบับที่ตรวจ; แยกwater(W),unidentified,unmapped
- resolution_review_tag เป็นคอลัมน์ที่เราสร้าง ไม่ใช่ LDD field; สัดส่วนทุกกลุ่มรวมunmappedรวม100%ภายใต้floating tolerance
