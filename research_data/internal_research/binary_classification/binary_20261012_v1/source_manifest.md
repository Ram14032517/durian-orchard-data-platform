# Source / Provenance

ทุกไฟล์ที่ใช้พร้อมSHA256อยู่ source_manifest.json อ้างต่อ manifestsealedรุ่นเดิม ไม่ดาวน์โหลดใหม่

- OAE: research_data/external/oae_2026-09-17/durian_province.xlsx ผ่านPhase9D province_year.csv พร้อมoae_observation_id ปีข้อมูล2006–2025 สถานะRevision/PublicationDateยังไม่ยืนยัน ไม่ถือdownloaddateเป็นpublication
- NASA POWER: Phase9D weather_profile_month.csv และ sampling_points/manifestเดิม ข้อมูลT/RHday-weighted,ฝนsumรายเดือน ไม่ใช่WeatherForecastVintage
- ERA5-Land: raw_vpd/*.json.gz ในintegrated release เก็บresponseSHAและunits VPDคำนวณจากT/Tdew เป็นReanalysisผ่านOpen-Meteo ไม่ใช่HistoricalForecast
- NDVI: Landsat8ในresults/ndvi_monthly_profile.csv และrecordlineageเดิม >=6actualmonthsสองpixels/province ไม่blendSensors ไม่อ้างprovincearea mean
- LDD: Soil/GIScontextจากPhase9D mapvintages ไม่เป็นHistoricalFootprint ไม่มีPublishDerivedGIS สิทธิ์ยังPublicHOLDตามRegistryเดิม

preflight.json/final_verification.jsonยืนยันProtected1288filesและsealsเดิม ก่อน/หลัง ไม่รับรองHistoricalPIT ไม่มี2026Forecast
