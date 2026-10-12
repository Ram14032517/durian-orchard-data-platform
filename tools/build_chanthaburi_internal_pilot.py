"""Phase 9C: cache-only internal export. No network, GIS overlay, or ML imports.

CSV files are machine-readable dataset tables, not spreadsheet workbooks.
All validation happens before reserving a new output directory.
"""
from __future__ import annotations

import argparse
import calendar
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
YEARS = tuple(range(2006, 2026))
REGIONAL = "research_data/regional_orchards"
POWER = "research_data/external/power_orchards_2026-09-18"
OAE = "research_data/external/oae_2026-09-17/durian_province.xlsx"
MODEL = "research_data/five_province_history/training/ridge_vpd_final_model.json"
OAE_HASH = "6a3ae44026b5ef8037a8bb091852281d890168a8d795c9c44d5cde9a48613d4c"
MODEL_HASH = "b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680"
PARAMS = {"T2M": "C", "RH2M": "%", "PRECTOTCORR": "mm/day",
          "ALLSKY_SFC_SW_DWN": "MJ/m^2/day"}
WEATHER = {"T2M": "weather_t2m_mean_c", "RH2M": "weather_rh2m_mean_pct",
           "ALLSKY_SFC_SW_DWN": "weather_solar_mean_mj_m2_day"}
ITEMS = {"ผลผลิตต่อเนื้อที่ให้ผล": ("yield_kg_per_rai", "กิโลกรัมต่อไร่"),
         "เนื้อที่ให้ผล": ("bearing_area_rai", "ไร่"),
         "เนื้อที่ยืนต้น": ("planted_area_rai", "ไร่"),
         "ผลผลิต": ("production_tonnes", "ตัน")}
BASE_FLAGS = ["retrospective_fixed_footprint", "survey_date_unverified",
              "oae_revised_reference", "publication_date_unverified", "license_pending",
              "annual_calendar_not_phenology", "time_standard_review"]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode("utf-8")).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def number(value):
    if value is None or str(value).strip() == "" or pd.isna(value):
        return None
    result = float(value)
    require(math.isfinite(result), "Non-finite input")
    return result


def close(actual, expected, label, tolerance=1e-7):
    a, b = number(actual), number(expected)
    require((a is None and b is None) or
            (a is not None and b is not None and abs(a - b) <= tolerance),
            f"{label}: mismatch {a} / {b}")


def keyed(rows, keys, label):
    output = {}
    for row in rows:
        key = tuple(str(row[k]) for k in keys)
        require(key not in output, f"{label}: duplicate key {key}")
        output[key] = row
    return output


def csv_rows(root, filename, province=True):
    with (root / REGIONAL / filename).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, row in enumerate(rows, 2):
        row["_csv_row"] = i
    return [r for r in rows if r.get("province_code") == "22"] if province else rows


def aggregate(values, weights):
    require(len(values) == len(weights), "Unequal weights and values")
    coverage = math.fsum(w for v, w in zip(values, weights) if v is not None)
    # Same availability rule as the existing spatial builder; no missing-strata fallback.
    return (math.fsum(v * w for v, w in zip(values, weights) if v is not None) / coverage
            if abs(coverage - 1) < 1e-7 else None), coverage


def annual(months):
    require(len(months) == 12 and {m["month"] for m in months} == set(range(1, 13)),
            "Incomplete or duplicate monthly keys")
    result = {}
    for parameter, field in WEATHER.items():
        vals = [m[parameter] for m in months]
        result[field] = (math.fsum(v * m["days"] for v, m in zip(vals, months)) /
                         sum(m["days"] for m in months)) if None not in vals else None
    rain = [m["rain_mm_month"] for m in months]
    result["weather_precip_total_mm"] = math.fsum(rain) if None not in rain else None
    result["complete_weather_months"] = sum(all(m[p] is not None for p in PARAMS) for m in months)
    return result


def oae_records(frame):
    frame = frame[frame.province_name.astype(str).str.strip().eq("จันทบุรี")]
    result, refs, coverage = {}, {}, []
    for year in YEARS:
        values, anchors = {}, []
        for item, (field, unit) in ITEMS.items():
            found = frame[(pd.to_numeric(frame.year) == year + 543) & frame.item.eq(item)]
            require(len(found) <= 1, f"Duplicate OAE {year}/{item}")
            values[field] = None
            if len(found):
                index, row = next(found.iterrows())
                require(str(row.unit).strip() == unit, f"OAE unit conflict {year}/{item}")
                require(int(row.crop_year) == int(row.year), f"OAE crop/year conflict {year}")
                require(str(row.commodity).strip() == "ทุเรียน", "Unexpected OAE commodity")
                values[field] = number(row.data)
                require(values[field] is None or values[field] >= 0, "Negative OAE value")
                anchors.append({"field": field, "excel_row": int(index) + 2,
                                "item": item, "unit": unit,
                                "data_date": str(row.data_date), "crop_year_be": int(row.crop_year)})
        result[year], refs[year] = values, anchors
        coverage.append({"province_code": "22", "year_ce": year,
                         "yield_status": "present_in_workbook" if values["yield_kg_per_rai"] is not None else "missing",
                         "yield_kg_per_rai": values["yield_kg_per_rai"],
                         "oae_measures_present": sum(v is not None for v in values.values()),
                         "historical_publication_status": "unverified"})
    return result, refs, coverage


def protected_snapshot(root):
    # Hash-only inventory: never copy secrets or private credentials into the snapshot.
    paths = set()
    old = root / "research_data/phase6b_before_protected_20261011.json"
    if old.exists():
        paths.update(root / p for p in read_json(old))
    for folder in [REGIONAL, "research_data/soil_evidence_chanthaburi",
                   "research_data/external/ldd_chanthaburi_2026-09-17", POWER,
                   "research_data/external/oae_2026-09-17"]:
        paths.update(p for p in (root / folder).rglob("*") if p.is_file())
    paths.add(root / MODEL)
    paths = {p for p in paths if p.is_file() and "__pycache__" not in p.parts
             and not any(s in p.name.lower() for s in ["secret", ".env", "credential"])}
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(paths)}


def prepare(root=ROOT):
    root = Path(root)
    require(sha(root / MODEL) == MODEL_HASH, "Production model hash mismatch")
    require(sha(root / OAE) == OAE_HASH, "OAE input hash mismatch")
    design = root / "docs/DURIAN_GEOSPATIAL_DATASET_DESIGN_TH.md"
    require(design.exists() and "Public release: HOLD" in design.read_text(encoding="utf-8"),
            "Missing Phase 9B / license hold")
    s = read_json(root / REGIONAL / "cti_analysis.json")
    require(s["province_code"] == "22" and s["summary"]["pure"]["records"] == 8512
            and s["sample_points"] == 16, "GIS cohort mismatch")
    require(s["landuse_year_be"] == 2568 and s["soil_year_be"] == 2561,
            "Map vintage mismatch")
    sources, input_files, qc = {}, {}, []

    def source(path, provider, role, expected=None, metadata=None):
        path = Path(path)
        rel = path.relative_to(root).as_posix()
        h = sha(path)
        require(expected is None or h == expected.lower(), f"Source hash mismatch: {rel}")
        sid = "src_" + digest([rel, h])[:24]
        sources[sid] = {"source_id": sid, "path": rel, "sha256": h, "bytes": path.stat().st_size,
                        "provider": provider, "role": role, "publication_time": None,
                        "publication_status": "unverified", "license_status": "pending",
                        "license_version": None, "metadata": metadata or {},
                        "retrieval_time": (metadata or {}).get("retrieved_utc"),
                        "retrieval_date_evidence": (metadata or {}).get("retrieval_date_from_SOURCE_md"),
                        "source_last_modified": (metadata or {}).get("last_modified_http"),
                        "source_version": (metadata or {}).get("header", {}).get("api", {}).get("version"),
                        "valid_period": {"start": "2006-01-01", "end": "2025-12-31"} if provider == "NASA POWER" else None,
                        "license_label": "Creative Commons Attribution Non-Commercial No-Derivs" if provider == "LDD"
                        else (metadata or {}).get("license_label"),
                        "availability_status": "unverified_historical_vintage"}
        input_files[rel] = h
        return sid

    raw_gis = []
    for entry in s["input_manifest"]:
        raw_gis.append(source(root / entry["path"], "LDD", "raw_gis_or_readme", entry["sha256"]))
    ld = root / "research_data/external/ldd_chanthaburi_2026-09-17"
    for name, expected in [("sr_cti.rar", "216d09529e8615111f3f3ed48b0597696729df66277f749d9fc07908b1e6d530"),
                           ("Landuse_cti.zip", "b82c6212b98578a2b1f1e5f6f3bec247f4275114e1ff058f53446435ba610bec")]:
        raw_gis.append(source(ld / name, "LDD", "raw_archive", expected))
    old = read_json(root / "research_data/soil_evidence_chanthaburi/analysis.json")
    close(s["summary"]["pure"]["rai"], old["summary"]["pure"]["rai"], "Two soil_result vintages", .1)
    artifact_ids = {}
    artifact_names = ["cti_analysis.json", "orchard_weather_samples.csv", "sample_weather_monthly.csv",
                      "orchard_weather_monthly.csv", "orchard_weather_annual.csv", "regional_province_year_panel.csv",
                      "soil_series_comparison.csv", "soil_resolution_review.csv", "cti_polygon_audit.csv",
                      "sample_response_signatures.csv", "landuse_code_inventory.csv"]
    for name in artifact_names:
        artifact_ids[name] = source(root / REGIONAL / name, "project", "existing_derived")
    source(design, "project", "design_and_license_evidence")
    for path in [ld / "SOURCE.md", root / "research_data/external/oae_2026-09-17/SOURCE.md",
                 root / REGIONAL / "SOURCE_TH.md", root / REGIONAL / "VALIDATION_TH.md"]:
        source(path, "project", "local_provenance_evidence")
    code_sources = [source(root / "tools" / name, "project", "transformation_code") for name in
                    ["prepare_regional_orchards.py", "fetch_orchard_weather.py", "prepare_national_comparison.py"]]
    oae_id = source(root / OAE, "OAE", "annual_provincial_workbook", OAE_HASH,
                    {"sheet": "durian", "license_label": "อื่นๆ / Creative Commons Attributions Non-Commercial",
                     "resource_url": "https://catalog.oae.go.th/dataset/durian_product/resource/3f9531b0-dc97-415a-a8d5-aa7c89f0c7b3",
                     "retrieval_date_from_SOURCE_md": "2026-09-17", "data_date_is_publication_evidence": False})
    points = csv_rows(root, "orchard_weather_samples.csv")
    ps = keyed(points, ["sample_id"], "points")
    require(len(ps) == 16, "Expected 16 sample points")
    weights = [number(p["weight"]) for p in points]
    require(all(w is not None and w > 0 for w in weights), "Invalid sampling weights")
    close(math.fsum(weights), 1, "Weight sum", 1e-7)
    for p in points:
        require(p["inside_A403"] == "True" and p["landuse_year_be"] == "2568", "Point lineage conflict")
        close(float(p["weight"]), float(p["A403_area_rai"]) / s["summary"]["pure"]["union_rai"], "Stratum area weight", 1e-7)
    sample_saved = keyed(csv_rows(root, "sample_weather_monthly.csv"), ["sample_id", "year_ce", "month"], "sample-month")
    monthly_saved = keyed(csv_rows(root, "orchard_weather_monthly.csv"), ["year_ce", "month"], "province-month")
    annual_saved = keyed(csv_rows(root, "orchard_weather_annual.csv"), ["year_ce"], "annual")
    panel_saved = keyed(csv_rows(root, "regional_province_year_panel.csv"), ["year_ce"], "panel")
    signatures_saved = keyed(csv_rows(root, "sample_response_signatures.csv"), ["sample_id"], "signature")
    expected_months = {(str(y), str(m)) for y in YEARS for m in range(1, 13)}
    require(set(monthly_saved) == expected_months, "Province monthly coverage conflict")
    require(set(annual_saved) == set(panel_saved) == {(str(y),) for y in YEARS}, "Annual coverage conflict")
    require(set(signatures_saved) == set(ps), "Missing response signatures")
    require(set(sample_saved) == {(sid[0], y, m) for sid in ps for y, m in expected_months}, "Sample monthly coverage conflict")
    raw_values, power_ids, signatures = {}, {}, []
    for p in points:
        sid = p["sample_id"]
        path = root / POWER / (sid + ".json")
        meta = read_json(path.with_name(path.name + ".source.json"))
        obj = read_json(path)
        require({k: obj["parameters"][k]["units"] for k in PARAMS} == PARAMS, "POWER unit conflict")
        require(obj["header"]["time_standard"] == "LST", "POWER header time standard conflict")
        from urllib.parse import parse_qs, urlparse
        query = parse_qs(urlparse(meta["url"]).query)
        require(query.get("start") == ["2006"] and query.get("end") == ["2025"], "POWER period conflict")
        close(query["longitude"][0], round(float(p["longitude"]), 7), "Request longitude")
        close(query["latitude"][0], round(float(p["latitude"]), 7), "Request latitude")
        power_ids[sid] = source(path, "NASA POWER", "cached_monthly_response", meta["sha256"],
                                {**meta, "header": obj["header"], "units": PARAMS})
        source(path.with_name(path.name + ".source.json"), "project", "retrieval_sidecar")
        values = obj["properties"]["parameter"]
        signature = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
        require(signature == signatures_saved[(sid,)]["response_profile_sha256"], "Profile signature conflict")
        signatures.append({"sample_id": sid, "response_profile_sha256": signature,
                           "power_source_id": power_ids[sid]})
        for y, m in expected_months:
            vals = {}
            for parameter in PARAMS:
                require(y + f"{int(m):02}" in values[parameter], f"Missing cache key {sid}/{y}/{m}/{parameter}")
                v = values[parameter][y + f"{int(m):02}"]
                vals[parameter] = None if v == obj["header"]["fill_value"] else number(v)
                close(vals[parameter], sample_saved[(sid, y, m)][parameter], "Raw/derived sample value")
            r = sample_saved[(sid, y, m)]
            require(int(r["days"]) == calendar.monthrange(int(y), int(m))[1], "Sample days conflict")
            close(r["weight"], p["weight"], "Saved sample weight", 1e-12)
            raw_values[(sid, y, m)] = vals
    profile_id = "profile_" + digest([raw_gis, artifact_ids["orchard_weather_samples.csv"], code_sources])[:24]
    map_id = "map_" + digest([raw_gis, artifact_ids["cti_analysis.json"]])[:24]
    monthly = []
    for y in YEARS:
        for m in range(1, 13):
            saved = monthly_saved[(str(y), str(m))]
            row = {"province_code": "22", "year_ce": y, "month": m,
                   "weather_profile_id": profile_id, "days": calendar.monthrange(y, m)[1]}
            require(int(saved["days"]) == row["days"] and int(saved["sample_points_total"]) == 16, "Monthly metadata conflict")
            for parameter in PARAMS:
                row[parameter], coverage = aggregate([raw_values[(p["sample_id"], str(y), str(m))][parameter] for p in points], weights)
                row[parameter + "_area_coverage"] = coverage
                close(row[parameter], saved[parameter], "Spatial monthly aggregation")
                close(coverage, saved[parameter + "_area_coverage"], "Saved coverage", 1e-12)
            row["rain_mm_month"] = row["PRECTOTCORR"] * row["days"] if row["PRECTOTCORR"] is not None else None
            close(row["rain_mm_month"], saved["rain_mm_month"], "Rain conversion")
            monthly.append(row)
    workbook = pd.read_excel(root / OAE, sheet_name="durian")
    oae, oae_refs, coverage = oae_records(workbook)
    weather_rows, panel = [], []
    mapping = {"temperature_c": "weather_t2m_mean_c", "humidity_pct": "weather_rh2m_mean_pct",
               "solar_mj_m2_day": "weather_solar_mean_mj_m2_day", "rain_mm_year": "weather_precip_total_mm"}
    for y in YEARS:
        agg = annual([m for m in monthly if m["year_ce"] == y])
        for oldfield, field in mapping.items():
            close(agg[field], annual_saved[(str(y),)][oldfield], "Annual recomputation", 1e-6)
            close(agg[field], panel_saved[(str(y),)][oldfield], "Panel weather", 1e-6)
        for sourcefield, field in [("yield_kg_per_rai_source", "yield_kg_per_rai"), ("bearing_rai", "bearing_area_rai"),
                                    ("planted_rai", "planted_area_rai"), ("production_tonnes", "production_tonnes")]:
            close(oae[y][field], panel_saved[(str(y),)][sourcefield], "OAE/derived coverage or value conflict")
        wr = {"province_code": "22", "year_ce": y, "weather_profile_id": profile_id, **agg}
        weather_rows.append(wr)
        obs_id = "oae_" + digest([oae_id, "22", y, oae_refs[y]])[:24] if oae_refs[y] else None
        panel.append({**wr, "province_name": "จันทบุรี", "soil_map_pair_id": map_id,
                      "oae_observation_id": obs_id, **oae[y], "landuse_map_year_be": 2568,
                      "soil_production_year_be": 2561, "survey_date": None, "survey_date_status": "unverified",
                      "quality_flags": ";".join(BASE_FLAGS + (["weather_year_before_map"] if y < 2025 else []) +
                                             (["yield_missing"] if oae[y]["yield_kg_per_rai"] is None else []))})
        coverage[y - 2006].update(weather_months=agg["complete_weather_months"],
                                  sampled_points=16, landuse_map_year_ce=2025)
    soils = csv_rows(root, "soil_series_comparison.csv")
    reviews = keyed(csv_rows(root, "soil_resolution_review.csv"), ["soil_code"], "soil review")
    keyed(soils, ["soil_code"], "soil composition")
    require(set(reviews) == {(r["soil_code"],) for r in soils}, "Soil classification coverage conflict")
    composition = []
    pure = s["summary"]["pure"]
    for r in soils:
        require(r["soil_year_be"] == "2561" and r["landuse_year_be"] == "2568", "Soil table vintage conflict")
        value = float(r["pure_rai"])
        share = value / pure["rai"] * 100
        close(share, r["share_of_A403_pct"], "Soil denominator", 1e-9)
        review = reviews[(r["soil_code"],)]
        close(review["pure_rai"], value, "Soil review values")
        composition.append({"soil_map_pair_id": map_id, "province_code": "22", "soil_map_code": r["soil_code"],
                            "soil_name_source": r["soil_name"], "map_unit_class": review["resolution_review_tag"],
                            "classification_status": "project_interpretation_not_official",
                            "pure_intersection_rai": value, "mixed_intersection_rai": float(r["mixed_rai"]),
                            "share_of_pure_A403_pct": share})
    audits = csv_rows(root, "cti_polygon_audit.csv")
    keyed(audits, ["source_record"], "polygon audit")
    for kind in ["pure", "mixed"]:
        rows = [r for r in audits if r["kind"] == kind]
        summary = s["summary"][kind]
        require(len(rows) == summary["records"], "Polygon audit count conflict")
        for r in rows:
            require((r["landuse_code"] == "A403") == (kind == "pure") and "A403" in r["landuse_code"].split("/"), "Crop classification conflict")
        close(math.fsum(float(r["geometry_rai"]) for r in rows), summary["rai"], "Polygon area", .1)
        close(math.fsum(float(r["covered_rai"]) for r in rows), summary["covered_rai"], "Covered area", .1)
        close(summary["covered_rai"] + summary["uncovered_rai"], summary["rai"], "Area reconciliation", .1)
        close(sum(r[kind + "_intersection_rai"] for r in composition), summary["covered_rai"], "Soil mapped sum", .1)
        require(summary["uncovered_rai"] >= -1e-7 and summary["soil_overlap_rai"] < .1
                and summary["landuse_overlap_rai"] < .1, "GIS overlap/uncovered conflict")
    require(s["cross_class_overlap_rai"] < .1, "Cross-class overlap")
    close(sum(r["share_of_pure_A403_pct"] for r in composition) + pure["uncovered_rai"] / pure["rai"] * 100,
          100, "Shares incl uncovered", .1 / pure["rai"] * 100 + 1e-9)
    mixed = []
    codes = sorted({r["landuse_code"] for r in audits if r["kind"] == "mixed"})
    inventory = keyed(csv_rows(root, "landuse_code_inventory.csv"), ["landuse_code"], "Code inventory")
    for code in codes:
        rows = [r for r in audits if r["landuse_code"] == code]
        require((code,) in inventory and int(inventory[(code,)]["records"]) == len(rows), "Mixed inventory conflict")
        mixed.append({"soil_map_pair_id": map_id, "province_code": "22", "landuse_code": code,
                      "source_description_th": inventory[(code,)]["source_description_th"], "polygon_count": len(rows),
                      "full_polygon_area_rai": math.fsum(float(r["geometry_rai"]) for r in rows),
                      "exclusion_reason": "unknown_durian_fraction; excluded_from_pure_denominator"})
    close(sum(r["full_polygon_area_rai"] for r in mixed), s["summary"]["mixed"]["rai"], "Mixed exclusion sum", .1)
    summary = {"soil_map_pair_id": map_id, "province_code": "22", "landuse_map_year_be": 2568,
               "soil_production_year_be": 2561, "survey_date": None, "survey_date_status": "unverified",
               "soil_crs": s["soil_source_crs"], "landuse_crs": s["landuse_source_crs"],
               "pure_A403_total_rai": pure["rai"], "covered_rai": pure["covered_rai"],
               "uncovered_rai": pure["uncovered_rai"], "uncovered_pct": pure["uncovered_rai"] / pure["rai"] * 100,
               "SC_rai": sum(r["pure_intersection_rai"] for r in composition if r["soil_map_code"] == "SC"),
               "W_rai": sum(r["pure_intersection_rai"] for r in composition if r["soil_map_code"] == "W"),
               "mixed_excluded_rai": s["summary"]["mixed"]["rai"], "pure_polygons": 8512,
               "denominator": "pure_A403_total_including_SC_W_uncovered_excluding_mixed"}
    qc = [{"check": name, "status": "pass"} for name in ["input_hashes", "OAE_per_year_units_and_join",
          "sampling_weights", "raw_monthly_values", "response_signatures", "monthly_spatial_aggregation",
          "annual_day_weighted_aggregation", "soil_area_shares_SC_W_uncovered", "mixed_exclusions", "unique_keys"]]
    typed_points = []
    for p in points:
        typed = {k: v for k, v in p.items() if k != "_csv_row"}
        for field in ["longitude", "latitude", "grid_size_degrees", "A403_area_rai", "weight"]:
            typed[field] = float(typed[field])
        for field in ["landuse_year_be", "grid_x", "grid_y"]:
            typed[field] = int(typed[field])
        typed["inside_A403"] = typed["inside_A403"] == "True"
        typed_points.append(typed)
    tables = {"province_year": panel, "weather_profile_year": weather_rows, "weather_profile_month": monthly,
              "soil_map_vintage": [summary], "soil_composition": composition, "mixed_use_exclusions": mixed,
              "coverage": coverage, "sampling_points": typed_points,
              "response_signatures": signatures}
    lineage = []

    def trace(table, key, fields, sid, locator, calc):
        lineage.append({"table_name": table, "row_key": key, "fields": fields, "source_id": sid,
                        "source_locator": locator, "calculation": calc})

    for row in monthly:
        key = f"22/{row['year_ce']}/{row['month']}"
        for p in points:
            trace("weather_profile_month", key, list(PARAMS), power_ids[p["sample_id"]],
                  f"properties.parameter.*.{row['year_ce']}{row['month']:02}", "sum(valid value * weight)/coverage; missing if coverage not 1")
        trace("weather_profile_month", key, ["weights", "weather_profile_id"], artifact_ids["orchard_weather_samples.csv"],
              "province_code=22; sample_id=" + ",".join(p["sample_id"] for p in points), "weights and footprint linkage")
    for y in YEARS:
        for table in ["province_year", "weather_profile_year", "coverage"]:
            trace(table, f"22/{y}", list(WEATHER.values()) + ["weather_precip_total_mm"], artifact_ids["orchard_weather_monthly.csv"],
                  f"province_code=22/year_ce={y}/months=1..12", "verified against raw cache; means weighted by days; rainfall rate * days summed")
            for ref in oae_refs[y] if table != "weather_profile_year" else []:
                trace(table, f"22/{y}", [ref["field"]], oae_id, f"durian!row={ref['excel_row']};item={ref['item']};column=data", "direct reported value; no interpolation")
            if not oae_refs[y] and table != "weather_profile_year":
                trace(table, f"22/{y}", list(oae[y]), oae_id, f"durian/province_name=จันทบุรี/year={y+543}: no rows", "missing stays null")
    for r in composition:
        trace("soil_composition", f"{map_id}/{r['soil_map_code']}", list(r), artifact_ids["soil_series_comparison.csv"],
              f"province_code=22/soil_code={r['soil_map_code']}", "copy intersections; share=100*pure_rai/cti_analysis.summary.pure.rai")
        trace("soil_composition", f"{map_id}/{r['soil_map_code']}", ["map_unit_class"], artifact_ids["soil_resolution_review.csv"],
              f"province_code=22/soil_code={r['soil_map_code']}", "project interpretation copied, not LDD official class")
    for r in mixed:
        trace("mixed_use_exclusions", f"{map_id}/{r['landuse_code']}", list(r), artifact_ids["cti_polygon_audit.csv"],
              "source_record=" + ",".join(r2["source_record"] for r2 in audits if r2["landuse_code"] == r["landuse_code"]), "group full geometry area; no durian allocation")
        trace("mixed_use_exclusions", f"{map_id}/{r['landuse_code']}", ["source_description_th"], artifact_ids["landuse_code_inventory.csv"],
              f"province_code=22/landuse_code={r['landuse_code']}", "copy source description")
    trace("soil_map_vintage", map_id, list(summary), artifact_ids["cti_analysis.json"], "summary.pure,summary.mixed,qa,input_manifest", "copy summary; SC/W from composition; no overlay rerun")
    trace("soil_map_vintage", map_id, ["SC_rai", "W_rai"], artifact_ids["soil_series_comparison.csv"],
          "province_code=22;soil_code=SC/W", "diagnostic subtotals already in covered area")
    for p in points:
        trace("sampling_points", p["sample_id"], list(p), artifact_ids["orchard_weather_samples.csv"], f"csv_row={p['_csv_row']}", "copy existing quadrature point/weight; not farm")
        trace("response_signatures", p["sample_id"], ["response_profile_sha256"], power_ids[p["sample_id"]], "properties.parameter", "SHA256(json.dumps(values,sort_keys=True))")
    for name in ["cti_analysis.json", "soil_series_comparison.csv", "cti_polygon_audit.csv", "orchard_weather_samples.csv"]:
        for sid in raw_gis + code_sources:
            trace("existing_artifact", artifact_ids[name], ["provenance"], sid, "cti_analysis.input_manifest / existing builder", "existing artifact dependency; polygon-to-soil intersections not individually retained")
    for table, rows in tables.items():
        for row in rows:
            key = "/".join(str(row[k]) for k in KEYS[table])
            trace(table, key, ["structural_keys", "vintage_metadata", "quality_flags"], artifact_ids["cti_analysis.json"],
                  "province_code=22; landuse_year_be=2568; soil_year_be=2561; fixed protocol years", "metadata only; not survey dates or new observations")
    return {"tables": tables, "source_manifest": list(sources.values()), "lineage": lineage,
            "qc": qc, "input_hashes": input_files, "oae_anchors": oae_refs,
            "unique_response_profiles": len({r["response_profile_sha256"] for r in signatures}),
            "geometry_QC": s["qa"], "raw_gis_sources": raw_gis, "code_sources": code_sources}


KEYS = {"province_year": ["province_code", "year_ce"], "weather_profile_year": ["weather_profile_id", "year_ce"],
        "weather_profile_month": ["weather_profile_id", "year_ce", "month"], "soil_map_vintage": ["soil_map_pair_id"],
        "soil_composition": ["soil_map_pair_id", "soil_map_code"], "mixed_use_exclusions": ["soil_map_pair_id", "landuse_code"],
        "coverage": ["province_code", "year_ce"], "sampling_points": ["sample_id"], "response_signatures": ["sample_id"],
        "quality_flags": ["table_name", "row_key", "flag_code"]}


def write_json(path, obj):
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def write_csv(path, rows):
    require(bool(rows), f"Empty export {path.name}")
    with path.open("x", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def dictionary(tables):
    definitions = {
        "yield_kg_per_rai": ("kg/rai", "OAE reported provincial yield per bearing rai; not orchard yield", "direct reported value"),
        "bearing_area_rai": ("rai", "OAE provincial bearing area", "direct reported value"),
        "planted_area_rai": ("rai", "OAE provincial planted/standing area, distinct from bearing area", "direct reported value"),
        "production_tonnes": ("tonne", "OAE provincial production, not A403 production", "direct reported value"),
        "weather_t2m_mean_c": ("deg C", "Annual spatial profile mean air temperature", "monthly mean weighted by calendar days"),
        "weather_rh2m_mean_pct": ("percent", "Annual spatial profile mean relative humidity, not soil moisture", "monthly mean weighted by days"),
        "weather_solar_mean_mj_m2_day": ("MJ/m2/day", "Annual mean daily solar energy, not sunshine hours", "monthly mean weighted by days"),
        "weather_precip_total_mm": ("mm/year", "Annual precipitation depth", "sum monthly rate * days"),
        "share_of_pure_A403_pct": ("percent 0..100", "Pure intersection / all pure A403 incl SC W uncovered, excl mixed", "100*pure_intersection_rai/pure_A403_total_rai"),
        "survey_date": ("date", "Unconfirmed observation/survey date; map year is not a date", "null; no imputation"),
        "soil_production_year_be": ("BE year", "Soil production year from readme, not plot survey date", "2561 from source readme"),
        "landuse_map_year_be": ("BE year", "Land-use map label, not annual historical crop footprint", "2568 from file path"),
        "map_unit_class": ("category", "Project interpretation, not official LDD soil-series quality", "copy soil_resolution_review"),
        "SC_rai": ("rai", "SC diagnostic subtotal already included in covered area", "sum SC rows; do not add again"),
        "W_rai": ("rai", "Water diagnostic subtotal already included in covered area", "sum W rows; do not add again"),
        "uncovered_pct": ("percent 0..100", "Pure A403 without soil coverage", "100*uncovered_rai/pure_A403_total_rai"),
        "weight": ("fraction 0..1", "Stratum pure-A403 area / pure-A403 union area", "copy existing sampling artifact"),
        "T2M": ("deg C", "Monthly mean air temperature", "area weighted raw cached POWER values"),
        "RH2M": ("percent", "Monthly mean air humidity", "area weighted raw cached POWER values"),
        "PRECTOTCORR": ("mm/day", "Monthly mean daily precipitation", "area weighted raw cached POWER values"),
        "ALLSKY_SFC_SW_DWN": ("MJ/m2/day", "Monthly mean daily solar energy", "area weighted raw cached POWER values"),
        "rain_mm_month": ("mm/month", "Monthly precipitation depth", "PRECTOTCORR*days"),
        "quality_flags": ("semicolon-delimited codes", "Limitations visible per annual record", "fixed protocol plus evidence-based missing/footprint flags"),
        "pure_intersection_rai": ("rai", "Full-resolution existing overlay area of pure A403 within this soil map unit", "copy soil_series_comparison.pure_rai; no new overlay"),
        "mixed_intersection_rai": ("rai", "Full mixed-use polygon intersection, not allocated durian area", "copy soil_series_comparison.mixed_rai"),
        "mixed_excluded_rai": ("rai", "Entire mixed-use area excluded from pure denominator", "copy cti_analysis.summary.mixed.rai"),
        "full_polygon_area_rai": ("rai", "Entire mixed-use polygons grouped by source LU code", "sum geometry_rai from polygon audit"),
        "pure_A403_total_rai": ("rai", "All pure A403 geometry area including SC W and uncovered", "cti_analysis.summary.pure.rai"),
        "covered_rai": ("rai", "Pure area covered by existing soil overlay", "cti_analysis.summary.pure.covered_rai"),
        "uncovered_rai": ("rai", "Pure area without soil coverage", "cti_analysis.summary.pure.uncovered_rai"),
        "A403_area_rai": ("rai", "All pure crop area in sampling stratum", "copy existing sampling geometry-derived area"),
        "complete_weather_months": ("count 0..12", "Months with all four weather variables present", "count complete monthly rows; no month13"),
        "response_profile_sha256": ("SHA256", "Hash of full parameter-value profile, not bytes or independent station ID", "SHA256 sorted JSON parameter mapping"),
        "soil_name_source": ("text", "LDD name text retained including unresolved source spelling", "copy existing soil summary; no inferred corrections"),
        "inside_A403": ("boolean", "Containment assertion from original sampling builder", "copied; not independently retested in Phase9C"),
        "grid_size_degrees": ("degree", "Sampling stratum width, not POWER grid resolution", "0.25 from sampling artifact"),
        "landuse_year_be": ("BE year", "Map label in existing sampling artifact", "copy; not survey date"),
        "days": ("calendar days", "Number of days in year/month including leap years", "calendar.monthrange"),
        "year_ce": ("CE year", "Calendar label used for join; not a verified phenological season", "OAE year BE minus543; POWER calendar year"),
        "month": ("integer 1..12", "Calendar month; POWER annual month13 excluded", "POWER monthly key suffix"),
        "classification_status": ("category", "Soil unit grouping is project interpretation", "explicit project_interpretation_not_official"),
    }
    result = []
    for table, rows in tables.items():
        for field in rows[0]:
            vals = [r[field] for r in rows if r[field] is not None]
            kind = type(vals[0]).__name__ if vals else "nullable_date"
            unit, meaning, calculation = definitions.get(field, (
                "rai" if field.endswith("_rai") else "fraction 0..1" if field.endswith("_area_coverage") else
                "WGS84 degree" if field in ["longitude", "latitude"] else "CE year" if field == "year_ce" else "identifier/count/text",
                field.replace("_", " "), "copy source or deterministic QC metadata; see row lineage"))
            result.append({"table_name": table, "field": field, "type": kind, "unit": unit,
                           "definition": meaning, "source": "source_manifest + field_lineage.jsonl",
                           "calculation": calculation, "missing_values": "JSON null / CSV empty; never zero-filled",
                           "quality_flags": "quality_flags.csv and province_year.quality_flags"})
    return result


def export(root, output, prepared=None, before=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    allowed = root / "research_data/internal_research/chanthaburi_pilot"
    require(output.parent == allowed, "Output must be a new direct child of internal pilot directory")
    require(not output.exists(), "Artifact overwrite refused")
    data = prepared if prepared is not None else prepare(root)
    for rel, expected in data["input_hashes"].items():
        require(sha(root / rel) == expected, f"Input changed after preflight: {rel}")
    before = before if before is not None else protected_snapshot(root)
    script = root / "tools/build_chanthaburi_internal_pilot.py"
    code_hash = sha(script)
    output.mkdir(parents=True, exist_ok=False)
    (output / ".gitignore").write_text("*\n", encoding="utf-8")
    release_id = output.name
    tables = {name: [{"release_id": release_id, **row} for row in rows] for name, rows in data["tables"].items()}
    flags = []
    for name, rows in tables.items():
        for row in rows:
            key = "/".join(str(row[k]) for k in KEYS[name])
            codes = row.get("quality_flags", "license_pending;survey_date_unverified").split(";")
            if name == "soil_composition" and row["soil_map_code"] in ["SC", "W"]:
                codes.append("SC_complex_unit" if row["soil_map_code"] == "SC" else "W_crop_overlay_review")
            for code in codes:
                flags.append({"release_id": release_id, "table_name": name, "row_key": key,
                              "flag_code": code, "severity": "warning", "review_status": "unresolved",
                              "evidence": "Phase 9B and source_manifest; not a PIT/legal certification"})
    tables["quality_flags"] = flags
    for name, rows in tables.items():
        keyed(rows, KEYS[name], name)
        write_csv(output / (name + ".csv"), rows)
    write_csv(output / "data_dictionary.csv", dictionary(tables))
    write_json(output / "dataset.json", {"release_id": release_id, "access": "internal_only", "tables": tables})
    write_json(output / "schema.json", {"format": "UTF-8 BOM CSV / typed JSON", "null": "CSV empty / JSON null",
               "support_tables": {"source_manifest.json": {"primary_key": ["source_id"]},
                                  "field_lineage.jsonl": {"key": ["table_name", "row_key", "fields", "source_id"]}},
               "foreign_keys": {"province_year.weather_profile_id": "weather_profile_year.weather_profile_id (paired year)",
                                "province_year.soil_map_pair_id": "soil_map_vintage.soil_map_pair_id",
                                "soil_composition.soil_map_pair_id": "soil_map_vintage.soil_map_pair_id",
                                "response_signatures.power_source_id": "source_manifest.source_id"},
               "tables": {name: {"primary_key": ["release_id", *KEYS[name]], "columns": list(rows[0]),
                                  "row_count": len(rows)} for name, rows in tables.items()}})
    write_json(output / "source_manifest.json", {"release_id": release_id, "sources": data["source_manifest"],
                 "license_review": "Phase 9B local evidence only; not refreshed over network",
                 "internal_use": "Local noncommercial research only; no redistribution permission asserted",
                 "public_release": "HOLD", "historical_PIT": "not_certified"})
    with (output / "field_lineage.jsonl").open("x", encoding="utf-8") as f:
        for row in data["lineage"]:
            f.write(json.dumps({"release_id": release_id, "transformation_code_sha256": code_hash, **row},
                               ensure_ascii=False, allow_nan=False) + "\n")
        design_source = next(s["source_id"] for s in data["source_manifest"] if s["role"] == "design_and_license_evidence")
        for flag in flags:
            f.write(json.dumps({"release_id": release_id, "table_name": "quality_flags",
                               "row_key": "/".join(str(flag[k]) for k in KEYS["quality_flags"]),
                               "fields": list(flag), "source_id": design_source,
                               "source_locator": "Phase 9B limitations + parent record lineage",
                               "calculation": "metadata flags, not causal observations",
                               "transformation_code_sha256": code_hash}, ensure_ascii=False) + "\n")
    unique = data["unique_response_profiles"]
    report = {"status": "pass_with_limitations", "checks": data["qc"], "coverage": tables["coverage"],
              "sample_points": 16, "unique_response_profiles": unique, "soil_summary": tables["soil_map_vintage"][0],
              "geometry_QC_from_existing_overlay": data["geometry_QC"], "overlay_rerun": False,
              "point_inside_geometry_independently_rechecked": False, "historical_PIT": "not_certified",
              "public_release": "HOLD", "transformation_code_sha256": code_hash}
    write_json(output / "qc_report.json", report)
    lines = ["# จันทบุรี Internal Research Pilot — Phase 9C", "", "ใช้ภายในเท่านั้น • ห้ามเผยแพร่ • ไม่รับรอง Historical PIT", "",
             f"Weather 2006–2025: 20 ปี, 240 เดือน, 16 จุด, response profiles ไม่ซ้ำ {unique} ชุด",
             "OAE ตรวจทีละปีจาก workbook; data_date ไม่ใช่ publication date. ไม่มีการเติม yield ที่หาย", "",
             "| ปี | Yield จังหวัด กก./ไร่ | สถานะ OAE | เดือนอากาศครบ |", "|---|---:|---|---:|"]
    for r in tables["coverage"]:
        lines.append(f"| {r['year_ce']} | {r['yield_kg_per_rai'] if r['yield_kg_per_rai'] is not None else 'null'} | {r['yield_status']} | {r['weather_months']} |")
    ss = tables["soil_map_vintage"][0]
    lines += ["", "## QC", "", "Input hashes, keys, sampling weights, raw-to-monthly-to-annual weather และ soil reconciliation ผ่าน",
              f"Pure {ss['pure_A403_total_rai']:.6f} ไร่; uncovered {ss['uncovered_rai']:.6f}; SC {ss['SC_rai']:.6f}; W {ss['W_rai']:.6f}",
              f"Mixed {ss['mixed_excluded_rai']:.6f} ไร่แยกออก ไม่จัดสรรเป็นพื้นที่ทุเรียน", "",
              "## ข้อจำกัด", "", "Footprint ปี 2568 ใช้ย้อนหลังทุกปี; soil ปีผลิต 2561 ไม่ใช่วันสำรวจ; 19/20 weather years ก่อนปีแผนที่",
              "ข้อมูล OAE อาจปรับปรุงย้อนหลัง; publication date/vintage ยังไม่พิสูจน์; yield ระดับจังหวัดไม่ใช่รายสวน",
              "LDD NC-ND และสิทธิ์ derived redistribution ยัง pending. เก็บในเครื่อง ไม่ upload/push/share raw geometry",
              "POWER LST ตาม cached header; ยังมี time-standard documentation review. จุดอาจแชร์ coarse grid",
              "Reuse overlay QC เดิม ไม่ rerun geometry/independent point containment. Aggregate soil lineage ถึง derived row + raw map pair; ไม่มี individual intersection records",
              "", "## ไฟล์สำหรับตรวจ", "", "schema.json, coverage.csv, province_year.csv, soil_map_vintage.csv, soil_composition.csv, mixed_use_exclusions.csv",
              "data_dictionary.csv, source_manifest.json, field_lineage.jsonl, quality_flags.csv, qc_report.json, reproducibility.json และ protected_verification.json"]
    (output / "QC_REPORT_TH.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    preview = ["# Dataset Preview — จันทบุรี", "", "Internal only. Yield จังหวัด ไม่ใช่ yield รายสวน", "",
               "| ปี | Yield กก./ไร่ | อุณหภูมิ °C | RH % | ฝน mm/ปี | รังสี MJ/m²/day |", "|---|---:|---:|---:|---:|---:|"]
    for r in tables["province_year"]:
        vals = [r[k] for k in ["year_ce", "yield_kg_per_rai", "weather_t2m_mean_c", "weather_rh2m_mean_pct", "weather_precip_total_mm", "weather_solar_mean_mj_m2_day"]]
        preview.append("| " + " | ".join("null" if v is None else str(v) if isinstance(v, int) else f"{v:.2f}" for v in vals) + " |")
    preview += ["", "ค่าตาราง Preview ปัดแสดงผลเท่านั้น CSV/JSON เก็บค่าความละเอียดเดิม", "Weather weighted spatial profile บน footprint ปี 2025; ไม่มี inference เชิงสาเหตุหรือ historical PIT"]
    (output / "PREVIEW_TH.md").write_text("\n".join(preview) + "\n", encoding="utf-8")
    write_json(output / "reproducibility.json", {"release_id": release_id, "created_utc": datetime.now(timezone.utc).isoformat(),
               "input_hashes": data["input_hashes"], "input_manifest_sha256": digest(data["input_hashes"]),
               "export_code_sha256": code_hash, "python": sys.version, "dependencies":
               {name: importlib.metadata.version(name) for name in ["pandas", "numpy", "openpyxl"]},
               "protocol": {"province_code": "22", "years": YEARS, "landuse_year_be": 2568, "soil_year_be": 2561,
                            "source": "existing_cached_only", "network_fallback": False, "overlay": False,
                            "area_tolerance_rai": .1, "weight_tolerance": 1e-7, "weather_tolerance": 1e-6},
               "oae_source_row_anchors": data["oae_anchors"]})
    after = protected_snapshot(root)
    require(before == after, "Protected assets changed; release must not be used")
    write_json(output / "protected_verification.json", {"before": before, "after": after,
               "changed": [], "production_sha256": sha(root / MODEL), "status": "pass"})
    files = {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    write_json(output / "output_manifest.json", {"files": files, "manifest_payload_sha256": digest(files),
               "note": "Manifest excludes its own file; additions require new release"})
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = prepare()
    if args.preflight:
        print(json.dumps({"checks": data["qc"], "coverage": data["tables"]["coverage"],
                          "unique_response_profiles": data["unique_response_profiles"]}, ensure_ascii=False))
    else:
        require(args.output is not None, "Explicit new --output required")
        result = export(ROOT, args.output, data)
        print(json.dumps({"output": str(args.output), "status": result["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
