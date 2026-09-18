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
