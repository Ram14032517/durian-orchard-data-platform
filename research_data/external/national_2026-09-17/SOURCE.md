# National comparison source snapshot — 2026-09-17

Local research snapshot. Download bytes are preserved. Every fetched file has a
`*.source.json` containing the exact URL/parameters, UTC retrieval timestamp,
SHA-256, byte count, and HTTP Last-Modified where available. The latter is NOT a survey date.

## Province boundaries and regions

- Selected geometry: https://gistdaportal.gistda.or.th/arcgis/rest/services/ข้อมูลเขตการปกครอง/MapServer/2
- 77 features, including Bangkok and Satun. Source_Nam attribute: DOPA. Inspect
  Source_dat in the raw response; snapshot timestamp 1388361600000 = 2013-12-30 UTC.
- Query returns EPSG:4326, server-generalized at maxAllowableOffset=0.002 degrees,
  geometryPrecision=5, then display simplification 0.005 degrees. NOT for cadastral
  decisions or area calculation. Weather reference points are representative_point
  inside the server-returned geometry, not an orchard centroid or province average.
- Six geometries repaired with Shapely make_valid for rendering/point selection:
  81, 92, 23, 33, 91, 32. No agricultural areas calculated from these boundaries.
- First candidate DPM layer returned only 76 provinces (Satun absent), confirmed by
  count query. It was NOT used as the final boundary map.
  https://gis-portal.disaster.go.th/arcgis/rest/services/MapDX/DPM_TH_Boundary/FeatureServer/1
- Region lookup follows DPM REGION_6 for its 76 records, with explicit manual supplement
  Satun (91) = ภาคใต้. This is not OAE's official regional tabulation. Counts: central22,
  northeast20, south14, north9, east7, west5. Original source geometry/metadata retained.
- Empty layer copyright/description do not constitute a publication license. Confirm
  redistribution terms and appropriate vintage before public dataset release.

## Production

- OAE catalog: https://catalog.oae.go.th/dataset/durian_product
- Provincial workbook is the unchanged snapshot in `../oae_2026-09-17/` with its SOURCE.md.
  4,428 rows → 1,107 province-years, 67 distinct provinces, 1997–2025, four measures.
- National workbook downloaded independently:
  https://catalog.oae.go.th/dataset/4810d4a3-669b-4e54-ba46-050e730d34c8/resource/b87d403d-16b4-4b1e-9454-18ef4981724c/download/durian_wholecountry.xlsx
- Provincial sum agrees exactly with national production in 2021–2023. Differences
  retained: 2024 provincial sum minus national = −0.77 tonne; 2025 = −0.31 tonne.
  Different displayed precision is consistent with these gaps; cause not confirmed.
- Source yield values retained; weighted regional/national yield is calculated from
  summed production and bearing area. Not an average of provincial yield values.
- Missing province records remain missing, not zero. No Monthong-only cultivar filter.
- Production coverage by year in this panel: 2021=49, 2022=59, 2023=59, 2024=67,
  2025=67 provinces. A newly reported province is not automatically newly planted.
  Ten absent provinces applies to 2025, not all years. Source yield differs from
  production/area by >1 kg/rai in24 of the1,107 source province-years; keep both columns.
- Catalog license metadata: CC Attribution Non-Commercial, unspecified version.

## NASA POWER (77 points × 60 months)

- Endpoint: https://power.larc.nasa.gov/api/temporal/monthly/point
- Documentation: https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
- Methodology: https://power.larc.nasa.gov/docs/methodology/meteorology/
- Each request: community=AG, start=2021, end=2025, format=JSON, point from province_lookup.csv.
- Returned API version v2.10.0; sources MERRA2, SYN1DEG, POWER; time standard LST.
- T2M = C; RH2M = %; PRECTOTCORR = mm/day; ALLSKY_SFC_SW_DWN = MJ/m^2/day.
- Meteorology is assimilation/reanalysis grid data (generally 0.5°×0.625°), not
  direct orchard measurements. Solar field is irradiance/energy, not lux or NDVI.
- Fill value −999 → missing. Months01–12 only; month13 source annual summary excluded.
- Rain annual estimate = sum(monthly mean mm/day × days in month); other fields are
  day-weighted means. Require12 valid months per metric. Monthly rounding retained.
- Country/region weather summaries, where displayed, are equally weighted province
  point averages. They are NOT spatial, orchard-area-weighted, or station averages.
- All77 requests succeeded and all4 measures have60 monthly values in this snapshot.
- Public NASA service accessed without accounts/tokens; retain NASA/source acknowledgements.

## Soil

Only the existing Chanthaburi LDD analysis is joined as an available evidence layer.
Its source provenance and license caveat are in `../ldd_chanthaburi_2026-09-17/SOURCE.md`.
No soil type is invented for other provinces. LDD's non-commercial/no-derivatives
metadata requires clarification before public redistribution of derived overlays.
