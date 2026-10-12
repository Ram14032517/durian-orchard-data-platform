"""Phase 9D cache-only expansion, preserving the sealed Phase 9C exporter.
QC arithmetic and thresholds are copied from Phase 9C; no network/GIS/ML execution.
"""
from __future__ import annotations
import argparse
import calendar
import csv
import hashlib
import importlib.metadata
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import sys
import pandas as pd
from tools import build_chanthaburi_internal_pilot as pilot
from tools.build_chanthaburi_internal_pilot import (
    ROOT, YEARS, REGIONAL, POWER, OAE, MODEL, OAE_HASH, MODEL_HASH,
    PARAMS, WEATHER, ITEMS, BASE_FLAGS, KEYS, require, sha, digest,
    read_json, number, close, keyed, aggregate, annual, write_json, write_csv,
)
PILOT = "research_data/internal_research/chanthaburi_pilot/phase9c_20261012_v1"
CONFIGS = (
    ("22", "จันทบุรี", "cti", 2568, 8512, 16),
    ("86", "ชุมพร", "cpn", 2564, 3897, 17),
    ("33", "ศรีสะเกษ", "ssk", 2565, 1234, 17),
    ("53", "อุตรดิตถ์", "utt", 2563, 71, 9),
)

def province_csv(root, filename, code):
    with (root / REGIONAL / filename).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for i, row in enumerate(rows, 2):
        row["_csv_row"] = i
    return [r for r in rows if r.get("province_code") == code]


def province_oae(frame, code, name):
    frame = frame[frame.province_name.astype(str).str.strip().eq(name)]
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
        coverage.append({"province_code": code, "year_ce": year,
                         "yield_status": "present_in_workbook" if values["yield_kg_per_rai"] is not None else "missing",
                         "yield_kg_per_rai": values["yield_kg_per_rai"],
                         "oae_measures_present": sum(v is not None for v in values.values()),
                         "historical_publication_status": "unverified"})
    return result, refs, coverage


def prepare_province(root, config):
    CODE, NAME, SHORT, MAP_BE, POLYGONS, POINTS = config
    csv_rows = lambda root, name: province_csv(root, name, CODE)
    root = Path(root)
    require(sha(root / MODEL) == MODEL_HASH, "Production model hash mismatch")
    require(sha(root / OAE) == OAE_HASH, "OAE input hash mismatch")
    design = root / "docs/DURIAN_GEOSPATIAL_DATASET_DESIGN_TH.md"
    require(design.exists() and "Public release: HOLD" in design.read_text(encoding="utf-8"),
            "Missing Phase 9B / license hold")
    s = read_json(root / REGIONAL / f"{SHORT}_analysis.json")
    require(s["province_code"] == CODE and s["summary"]["pure"]["records"] == POLYGONS
            and s["sample_points"] == POINTS, "GIS cohort mismatch")
    require(s["landuse_year_be"] == MAP_BE and s["soil_year_be"] == 2561,
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
    ld = root / f"research_data/external/ldd_regions_2026-09-18/{SHORT}"
    for name in [f"sr_{SHORT}.rar", f"Landuse_{SHORT}.zip"]:
        meta_path = ld / (name + ".source.json")
        meta = read_json(meta_path)
        raw_gis.append(source(ld / name, "LDD", "raw_archive", meta["sha256"], meta))
        source(meta_path, "project", "retrieval_sidecar")
    artifact_ids = {}
    artifact_names = [f"{SHORT}_analysis.json", "orchard_weather_samples.csv", "sample_weather_monthly.csv",
                      "orchard_weather_monthly.csv", "orchard_weather_annual.csv", "regional_province_year_panel.csv",
                      "soil_series_comparison.csv", "soil_resolution_review.csv", f"{SHORT}_polygon_audit.csv",
                      "sample_response_signatures.csv", "landuse_code_inventory.csv"]
    for name in artifact_names:
        artifact_ids[name] = source(root / REGIONAL / name, "project", "existing_derived")
    source(design, "project", "design_and_license_evidence")
    for path in [root / "research_data/external/ldd_regions_2026-09-18/SOURCE.md", root / "research_data/external/oae_2026-09-17/SOURCE.md",
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
    require(len(ps) == POINTS, "Expected POINTS sample points")
    weights = [number(p["weight"]) for p in points]
    require(all(w is not None and w > 0 for w in weights), "Invalid sampling weights")
    close(math.fsum(weights), 1, "Weight sum", 1e-7)
    for p in points:
        require(p["inside_A403"] == "True" and p["landuse_year_be"] == str(MAP_BE), "Point lineage conflict")
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
    map_id = "map_" + digest([raw_gis, artifact_ids[f"{SHORT}_analysis.json"]])[:24]
    monthly = []
    for y in YEARS:
        for m in range(1, 13):
            saved = monthly_saved[(str(y), str(m))]
            row = {"province_code": CODE, "year_ce": y, "month": m,
                   "weather_profile_id": profile_id, "days": calendar.monthrange(y, m)[1]}
            require(int(saved["days"]) == row["days"] and int(saved["sample_points_total"]) == POINTS, "Monthly metadata conflict")
            for parameter in PARAMS:
                row[parameter], coverage = aggregate([raw_values[(p["sample_id"], str(y), str(m))][parameter] for p in points], weights)
                row[parameter + "_area_coverage"] = coverage
                close(row[parameter], saved[parameter], "Spatial monthly aggregation")
                close(coverage, saved[parameter + "_area_coverage"], "Saved coverage", 1e-12)
            row["rain_mm_month"] = row["PRECTOTCORR"] * row["days"] if row["PRECTOTCORR"] is not None else None
            close(row["rain_mm_month"], saved["rain_mm_month"], "Rain conversion")
            monthly.append(row)
    workbook = pd.read_excel(root / OAE, sheet_name="durian")
    oae, oae_refs, coverage = province_oae(workbook, CODE, NAME)
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
        wr = {"province_code": CODE, "year_ce": y, "weather_profile_id": profile_id, **agg}
        weather_rows.append(wr)
        obs_id = "oae_" + digest([oae_id, CODE, y, oae_refs[y]])[:24] if oae_refs[y] else None
        panel.append({**wr, "province_name": NAME, "soil_map_pair_id": map_id,
                      "oae_observation_id": obs_id, **oae[y], "landuse_map_year_be": MAP_BE,
                      "soil_production_year_be": 2561, "survey_date": None, "survey_date_status": "unverified",
                      "quality_flags": ";".join(BASE_FLAGS + (["weather_year_before_map"] if y < MAP_BE - 543 else []) +
                                             (["yield_missing"] if oae[y]["yield_kg_per_rai"] is None else []))})
        coverage[y - 2006].update(weather_months=agg["complete_weather_months"],
                                  sampled_points=POINTS, landuse_map_year_ce=MAP_BE - 543)
    soils = csv_rows(root, "soil_series_comparison.csv")
    reviews = keyed(csv_rows(root, "soil_resolution_review.csv"), ["soil_code"], "soil review")
    keyed(soils, ["soil_code"], "soil composition")
    require(set(reviews) == {(r["soil_code"],) for r in soils}, "Soil classification coverage conflict")
    composition = []
    pure = s["summary"]["pure"]
    for r in soils:
        require(r["soil_year_be"] == "2561" and r["landuse_year_be"] == str(MAP_BE), "Soil table vintage conflict")
        value = float(r["pure_rai"])
        share = value / pure["rai"] * 100
        close(share, r["share_of_A403_pct"], "Soil denominator", 1e-9)
        review = reviews[(r["soil_code"],)]
        close(review["pure_rai"], value, "Soil review values")
        composition.append({"soil_map_pair_id": map_id, "province_code": CODE, "soil_map_code": r["soil_code"],
                            "soil_name_source": r["soil_name"], "map_unit_class": review["resolution_review_tag"],
                            "classification_status": "project_interpretation_not_official",
                            "pure_intersection_rai": value, "mixed_intersection_rai": float(r["mixed_rai"]),
                            "share_of_pure_A403_pct": share})
    audits = csv_rows(root, f"{SHORT}_polygon_audit.csv")
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
        mixed.append({"soil_map_pair_id": map_id, "province_code": CODE, "landuse_code": code,
                      "source_description_th": inventory[(code,)]["source_description_th"], "polygon_count": len(rows),
                      "full_polygon_area_rai": math.fsum(float(r["geometry_rai"]) for r in rows),
                      "exclusion_reason": "unknown_durian_fraction; excluded_from_pure_denominator"})
    close(sum(r["full_polygon_area_rai"] for r in mixed), s["summary"]["mixed"]["rai"], "Mixed exclusion sum", .1)
    summary = {"soil_map_pair_id": map_id, "province_code": CODE, "landuse_map_year_be": MAP_BE,
               "soil_production_year_be": 2561, "survey_date": None, "survey_date_status": "unverified",
               "soil_crs": s["soil_source_crs"], "landuse_crs": s["landuse_source_crs"],
               "pure_A403_total_rai": pure["rai"], "covered_rai": pure["covered_rai"],
               "uncovered_rai": pure["uncovered_rai"], "uncovered_pct": pure["uncovered_rai"] / pure["rai"] * 100,
               "SC_rai": sum(r["pure_intersection_rai"] for r in composition if r["soil_map_code"] == "SC"),
               "W_rai": sum(r["pure_intersection_rai"] for r in composition if r["soil_map_code"] == "W"),
               "mixed_excluded_rai": s["summary"]["mixed"]["rai"], "pure_polygons": POLYGONS,
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
        key = f"{CODE}/{row['year_ce']}/{row['month']}"
        for p in points:
            trace("weather_profile_month", key, list(PARAMS), power_ids[p["sample_id"]],
                  f"properties.parameter.*.{row['year_ce']}{row['month']:02}", "sum(valid value * weight)/coverage; missing if coverage not 1")
        trace("weather_profile_month", key, ["weights", "weather_profile_id"], artifact_ids["orchard_weather_samples.csv"],
              f"province_code={CODE}; sample_id=" + ",".join(p["sample_id"] for p in points), "weights and footprint linkage")
    for y in YEARS:
        for table in ["province_year", "weather_profile_year", "coverage"]:
            trace(table, f"{CODE}/{y}", list(WEATHER.values()) + ["weather_precip_total_mm"], artifact_ids["orchard_weather_monthly.csv"],
                  f"province_code={CODE}/year_ce={y}/months=1..12", "verified against raw cache; means weighted by days; rainfall rate * days summed")
            for ref in oae_refs[y] if table != "weather_profile_year" else []:
                trace(table, f"{CODE}/{y}", [ref["field"]], oae_id, f"durian!row={ref['excel_row']};item={ref['item']};column=data", "direct reported value; no interpolation")
            if not oae_refs[y] and table != "weather_profile_year":
                trace(table, f"{CODE}/{y}", list(oae[y]), oae_id, f"durian/province_name={NAME}/year={y+543}: no rows", "missing stays null")
    for r in composition:
        trace("soil_composition", f"{map_id}/{r['soil_map_code']}", list(r), artifact_ids["soil_series_comparison.csv"],
              f"province_code={CODE}/soil_code={r['soil_map_code']}", f"copy intersections; share=100*pure_rai/{SHORT}_analysis.summary.pure.rai")
        trace("soil_composition", f"{map_id}/{r['soil_map_code']}", ["map_unit_class"], artifact_ids["soil_resolution_review.csv"],
              f"province_code={CODE}/soil_code={r['soil_map_code']}", "project interpretation copied, not LDD official class")
    for r in mixed:
        trace("mixed_use_exclusions", f"{map_id}/{r['landuse_code']}", list(r), artifact_ids[f"{SHORT}_polygon_audit.csv"],
              "source_record=" + ",".join(r2["source_record"] for r2 in audits if r2["landuse_code"] == r["landuse_code"]), "group full geometry area; no durian allocation")
        trace("mixed_use_exclusions", f"{map_id}/{r['landuse_code']}", ["source_description_th"], artifact_ids["landuse_code_inventory.csv"],
              f"province_code={CODE}/landuse_code={r['landuse_code']}", "copy source description")
    trace("soil_map_vintage", map_id, list(summary), artifact_ids[f"{SHORT}_analysis.json"], "summary.pure,summary.mixed,qa,input_manifest", "copy summary; SC/W from composition; no overlay rerun")
    trace("soil_map_vintage", map_id, ["SC_rai", "W_rai"], artifact_ids["soil_series_comparison.csv"],
          f"province_code={CODE};soil_code=SC/W", "diagnostic subtotals already in covered area")
    for p in points:
        trace("sampling_points", p["sample_id"], list(p), artifact_ids["orchard_weather_samples.csv"], f"csv_row={p['_csv_row']}", "copy existing quadrature point/weight; not farm")
        trace("response_signatures", p["sample_id"], ["response_profile_sha256"], power_ids[p["sample_id"]], "properties.parameter", "SHA256(json.dumps(values,sort_keys=True))")
    for name in [f"{SHORT}_analysis.json", "soil_series_comparison.csv", f"{SHORT}_polygon_audit.csv", "orchard_weather_samples.csv"]:
        for sid in raw_gis + code_sources:
            trace("existing_artifact", artifact_ids[name], ["provenance"], sid, f"{SHORT}_analysis.input_manifest / existing builder", "existing artifact dependency; polygon-to-soil intersections not individually retained")
    for table, rows in tables.items():
        for row in rows:
            key = "/".join(str(row[k]) for k in KEYS[table])
            trace(table, key, ["structural_keys", "vintage_metadata", "quality_flags"], artifact_ids[f"{SHORT}_analysis.json"],
                  f"province_code={CODE}; landuse_year_be={MAP_BE}; soil_year_be=2561; fixed protocol years", "metadata only; not survey dates or new observations")
    return {"tables": tables, "source_manifest": list(sources.values()), "lineage": lineage,
            "qc": qc, "input_hashes": input_files, "oae_anchors": oae_refs,
            "unique_response_profiles": len({r["response_profile_sha256"] for r in signatures}),
            "geometry_QC": s["qa"], "raw_gis_sources": raw_gis, "code_sources": code_sources}

def verify_seal(root, folder):
    manifest = read_json(root / folder / "output_manifest.json")
    require(digest(manifest["files"]) == manifest["manifest_payload_sha256"], "Seal payload mismatch")
    for filename, expected in manifest["files"].items():
        require(sha(root / folder / filename) == expected, f"Sealed artifact mismatch: {filename}")
    return manifest


def protected_snapshot(root):
    result = pilot.protected_snapshot(root)
    for folder in ["research_data/external/ldd_regions_2026-09-18", PILOT]:
        for path in (root / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                require(not any(s in path.name.lower() for s in ["secret", ".env", "credential"]),
                        "Unexpected sensitive file in protected inventory")
                result[path.relative_to(root).as_posix()] = sha(path)
    for name in ["tools/build_chanthaburi_internal_pilot.py", "tests/test_chanthaburi_internal_pilot.py",
                 "docs/DURIAN_CHANTHABURI_INTERNAL_PILOT_TH.md"]:
        result[name] = sha(root / name)
    return dict(sorted(result.items()))


def validate_tables(tables, lineage, sources):
    for name, rows in tables.items():
        keyed(rows, KEYS[name], name)
    expected = {(code, y) for code, *_ in CONFIGS for y in YEARS}
    require({(r["province_code"], r["year_ce"]) for r in tables["province_year"]} == expected,
            "Missing/extra province-year keys")
    require({(r["province_code"], r["year_ce"]) for r in tables["coverage"]} == expected,
            "Missing coverage keys")
    weather = keyed(tables["weather_profile_year"], KEYS["weather_profile_year"], "weather FK")
    maps = keyed(tables["soil_map_vintage"], ["soil_map_pair_id"], "map FK")
    require(len(maps) == 4, "Missing map vintage")
    for row in tables["province_year"]:
        require((row["weather_profile_id"], str(row["year_ce"])) in weather, "Invalid weather join")
        require((row["soil_map_pair_id"],) in maps, "Invalid soil join")
        require(row["province_code"] == maps[(row["soil_map_pair_id"],)]["province_code"], "Cross-province soil join")
    for name in ["soil_composition", "mixed_use_exclusions"]:
        for row in tables[name]:
            require((row["soil_map_pair_id"],) in maps, "Orphan soil row")
    points = {r["sample_id"] for r in tables["sampling_points"]}
    require(len(points) == 59, "Missing sampling points")
    require({r["sample_id"] for r in tables["response_signatures"]} == points, "Missing signatures")
    source_ids = {s["source_id"] for s in sources}
    require(len(source_ids) == len(sources), "Duplicate manifest IDs")
    require(all(r["power_source_id"] in source_ids for r in tables["response_signatures"]), "Orphan POWER source")
    traces = {(r["table_name"], r["row_key"]) for r in lineage}
    require(all(r["source_id"] in source_ids for r in lineage), "Orphan lineage source")
    for name, rows in tables.items():
        for row in rows:
            key = "/".join(str(row[k]) for k in KEYS[name])
            require((name, key) in traces, f"Lineage missing: {name}/{key}")
    for code, _, _, _, _, count in CONFIGS:
        months = [r for r in tables["weather_profile_month"] if r["province_code"] == code]
        require({(r["year_ce"], r["month"]) for r in months} ==
                {(y, m) for y in YEARS for m in range(1, 13)}, "Missing monthly keys")
        require(sum(r["province_code"] == code for r in tables["sampling_points"]) == count, "Point cohort mismatch")


def prepare(root=ROOT):
    root = Path(root)
    verify_seal(root, Path(PILOT))
    reproduction = read_json(root / PILOT / "reproducibility.json")
    require(sha(root / "tools/build_chanthaburi_internal_pilot.py") == reproduction["export_code_sha256"],
            "Pilot exporter hash mismatch")
    require(read_json(root / PILOT / "qc_report.json")["status"] == "pass_with_limitations",
            "Pilot QC not accepted")
    for rel, expected in reproduction["input_hashes"].items():
        require(sha(root / rel) == expected, f"Pilot input hash mismatch: {rel}")
    data_by_province, failures = {}, []
    for config in CONFIGS:
        try:
            data_by_province[config[0]] = pilot.prepare(root) if config[0] == "22" else prepare_province(root, config)
        except (ValueError, KeyError, FileNotFoundError) as error:
            failures.append({"province_code": config[0], "province_name": config[1],
                             "status": "failed_not_accepted", "reason": str(error)})
    require(not failures, "Expansion preflight failed; no accepted release: " + json.dumps(failures, ensure_ascii=False))
    original = read_json(root / PILOT / "dataset.json")["tables"]
    for name, rows in data_by_province["22"]["tables"].items():
        expected = [{k: v for k, v in row.items() if k != "release_id"} for row in original[name]]
        require(rows == expected, f"Chanthaburi pilot equivalence failed: {name}")
    tables = {name: [row for data in data_by_province.values() for row in data["tables"][name]]
              for name in data_by_province["22"]["tables"]}
    sources, inputs, lineage = {}, {}, []
    for data in data_by_province.values():
        for source in data["source_manifest"]:
            require(source["source_id"] not in sources or source == sources[source["source_id"]],
                    "Conflicting shared source metadata")
            sources[source["source_id"]] = source
        for path, h in data["input_hashes"].items():
            require(path not in inputs or inputs[path] == h, "Conflicting shared input hashes")
            inputs[path] = h
        lineage.extend(data["lineage"])
    for path in (root / PILOT).iterdir():
        if path.is_file():
            inputs[path.relative_to(root).as_posix()] = sha(path)
    validate_tables(tables, lineage, list(sources.values()))
    return {"tables": tables, "source_manifest": list(sources.values()), "input_hashes": inputs,
            "lineage": lineage, "provinces": data_by_province, "pilot_equivalence": "exact_except_release_id"}


def output_path(root, output):
    output = Path(output).resolve()
    require(output.parent == (root / "research_data/internal_research/four_provinces").resolve(),
            "Output must be a new direct child of four_provinces")
    require(not output.exists(), "Artifact overwrite refused")
    return output


def export(root, output, data):
    root = Path(root).resolve()
    output = output_path(root, output)
    before = protected_snapshot(root)
    for path, expected in data["input_hashes"].items():
        require(sha(root / path) == expected, f"Input changed after preflight: {path}")
    validate_tables(data["tables"], data["lineage"], data["source_manifest"])
    old_schema = read_json(root / PILOT / "schema.json")
    for name, rows in data["tables"].items():
        require(all(["release_id", *row] == old_schema["tables"][name]["columns"] for row in rows),
                f"Schema conflict: {name}")
    code_hash = sha(root / "tools/build_four_province_internal_dataset.py")
    output.mkdir(parents=True, exist_ok=False)
    (output / ".gitignore").write_text("*\n", encoding="utf-8")
    release_id = output.name
    tables = {name: [{"release_id": release_id, **row} for row in rows] for name, rows in data["tables"].items()}
    flags = []
    for name, rows in tables.items():
        for row in rows:
            codes = row.get("quality_flags", "license_pending;survey_date_unverified").split(";")
            if name == "soil_composition" and row["soil_map_code"] in ["SC", "W"]:
                codes.append("SC_complex_unit" if row["soil_map_code"] == "SC" else "W_crop_overlay_review")
            for flag in codes:
                flags.append({"release_id": release_id, "table_name": name,
                              "row_key": "/".join(str(row[k]) for k in KEYS[name]),
                              "flag_code": flag, "severity": "warning", "review_status": "unresolved",
                              "evidence": "Phase 9B and source_manifest; not a PIT/legal certification"})
    tables["quality_flags"] = flags
    for name, rows in tables.items():
        require(list(rows[0]) == old_schema["tables"][name]["columns"], f"Schema conflict: {name}")
        keyed(rows, KEYS[name], name)
        write_csv(output / (name + ".csv"), rows)
    entries = pilot.dictionary(tables)
    for entry in entries:
        for k, value in entry.items():
            if isinstance(value, str):
                entry[k] = value.replace("2568 from file path", "province-specific land-use map label from source path").replace("cti_analysis", "<province>_analysis")
    write_csv(output / "data_dictionary.csv", entries)
    write_json(output / "dataset.json", {"release_id": release_id, "access": "internal_only", "tables": tables})
    schema = {**old_schema, "tables": {name: {**old_schema["tables"][name], "row_count": len(rows)}
                                      for name, rows in tables.items()}}
    write_json(output / "schema.json", schema)
    write_json(output / "source_manifest.json", {"release_id": release_id, "sources": data["source_manifest"],
        "license_review": "Phase 9B local evidence only; no new network access",
        "internal_use": "Local noncommercial research only; no redistribution permission asserted",
        "public_release": "HOLD", "historical_PIT": "not_certified"})
    design_source = next(s["source_id"] for s in data["source_manifest"] if s["role"] == "design_and_license_evidence")
    lineage = list(data["lineage"])
    for flag in flags:
        lineage.append({"table_name": "quality_flags", "row_key": "/".join(str(flag[k]) for k in KEYS["quality_flags"]),
                        "fields": list(flag), "source_id": design_source, "source_locator": "Phase 9B + parent record",
                        "calculation": "limitation metadata, not causal observations"})
    with (output / "field_lineage.jsonl").open("x", encoding="utf-8") as f:
        for row in lineage:
            f.write(json.dumps({"release_id": release_id, "transformation_code_sha256": code_hash, **row},
                               ensure_ascii=False, allow_nan=False) + "\n")
    qc_rows = []
    for config in CONFIGS:
        code, name, _, vintage, polygons, points = config
        province = data["provinces"][code]
        summary = province["tables"]["soil_map_vintage"][0]
        qc_rows.append({"province_code": code, "province_name": name, "status": "pass_with_limitations",
                        "weather_years": 20, "weather_months": len(province["tables"]["weather_profile_month"]),
                        "yield_years_present": sum(r["yield_status"] != "missing" for r in province["tables"]["coverage"]),
                        "landuse_map_year_be": vintage, "pure_polygons": polygons, "sampling_points": points,
                        "unique_response_profiles": province["unique_response_profiles"],
                        "pure_A403_rai": summary["pure_A403_total_rai"], "SC_rai": summary["SC_rai"],
                        "W_rai": summary["W_rai"], "uncovered_rai": summary["uncovered_rai"],
                        "mixed_excluded_rai": summary["mixed_excluded_rai"]})
    write_csv(output / "qc_summary.csv", qc_rows)
    matrix = []
    for y in YEARS:
        row = {"year_ce": y}
        for config in CONFIGS:
            code = config[0]
            c = next(r for r in tables["coverage"] if r["province_code"] == code and r["year_ce"] == y)
            row[code + "_yield_status"] = c["yield_status"]
            row[code + "_weather_months"] = c["weather_months"]
        matrix.append(row)
    write_csv(output / "coverage_matrix.csv", matrix)
    report = {"status": "pass_with_limitations", "accepted_provinces": [c[0] for c in CONFIGS],
              "failed_provinces": [], "province_qc": qc_rows,
              "checks": {code: d["qc"] for code, d in data["provinces"].items()},
              "geometry_QC_from_existing_overlay": {code: d["geometry_QC"] for code, d in data["provinces"].items()},
              "pilot_equivalence": data["pilot_equivalence"], "public_release": "HOLD",
              "historical_PIT": "not_certified", "overlay_rerun": False,
              "point_inside_geometry_independently_rechecked": False}
    write_json(output / "qc_report.json", report)
    write_json(output / "reproducibility.json", {"release_id": release_id,
        "created_utc": datetime.now(timezone.utc).isoformat(), "input_hashes": data["input_hashes"],
        "input_manifest_sha256": digest(data["input_hashes"]), "export_code_sha256": code_hash,
        "pilot_export_code_sha256": sha(root / "tools/build_chanthaburi_internal_pilot.py"),
        "python": sys.version, "dependencies": {n: importlib.metadata.version(n) for n in ["pandas", "numpy", "openpyxl"]},
        "protocol": {"cohort": CONFIGS, "years": YEARS, "network": False, "overlay": False,
                     "area_tolerance_rai": .1, "weight_tolerance": 1e-7, "weather_tolerance": 1e-6},
        "oae_source_row_anchors": {code: d["oae_anchors"] for code, d in data["provinces"].items()}})
    preview = ["# Four-province Internal Dataset Preview", "", "ใช้ภายในเท่านั้น • Public HOLD • ไม่รับรอง Historical PIT",
               "", "| จังหวัด | ปี | Yield กก./ไร่ | T °C | RH % | ฝน mm/ปี | รังสี MJ/m²/day |",
               "|---|---|---:|---:|---:|---:|---:|"]
    for row in tables["province_year"]:
        values = [row[k] for k in ["province_name", "year_ce", "yield_kg_per_rai", "weather_t2m_mean_c",
                                   "weather_rh2m_mean_pct", "weather_precip_total_mm", "weather_solar_mean_mj_m2_day"]]
        preview.append("| " + " | ".join("null" if v is None else f"{v:.2f}" if isinstance(v, float) else str(v) for v in values) + " |")
    preview += ["", "Preview ปัดเพื่ออ่าน; CSV/JSON เก็บความละเอียดเดิม ผลผลิตระดับจังหวัด ไม่ใช่รายสวน",
                "Footprint เป็นรุ่นแผนที่ต่างปี ไม่ใช่ Historical Orchard Footprint ทุกปี; soil ปีผลิต 2561 ไม่ใช่วันสำรวจ",
                "จันทบุรี: footprint 2025 ย้อนหลัง 19 ปี; ชุมพร: 2021 ย้อนหลัง 15 ปี; ศรีสะเกษ: 2022 ย้อนหลัง 16 ปี; อุตรดิตถ์: 2020 ย้อนหลัง 14 ปี",
                "อุตรดิตถ์มี pure A403 เพียง 71 polygon; mixed-use แยกทั้งหมด ห้ามจัดสรรเป็นทุเรียน",
                "OAE Revised Reference ไม่มี publication vintage ที่ยืนยัน; NASA POWER coarse grid และ LST documentation review",
                "SC/W ไม่ใช่ชุดดินยืนยัน; uncovered รวมในตัวหาร และอาจมี numerical residual เล็กน้อย",
                "Reuse QC geometry เดิม ไม่ตรวจ containment ใหม่; overlay lineage ระดับ aggregate ไม่มี individual intersections",
                "LDD/OAE สิทธิ์ derived distribution ยัง pending; ห้าม upload เผยแพร่ รวม geometry หรืออ้างเหตุและผล"]
    (output / "PREVIEW_TH.md").write_text("\n".join(preview) + "\n", encoding="utf-8")
    (output / "QC_REPORT_TH.md").write_text(
        "# Phase 9D QC Summary\n\nทุกจังหวัด pass_with_limitations ตาม QC Contract Phase 9C\n"
        "ดู qc_summary.csv, coverage_matrix.csv และ qc_report.json สำหรับตัวเลขแยกจังหวัด\n"
        "Schema/Units เดิม; จันทบุรีตรงกับ Pilot ทุกค่าก่อนเพิ่ม release_id\n"
        "ข้อจำกัดแยกจังหวัดและร่วมกันอยู่ท้าย PREVIEW_TH.md; Public HOLD\n", encoding="utf-8")
    after = protected_snapshot(root)
    require(before == after, "Protected assets changed: do not use release")
    write_json(output / "protected_verification.json", {"before": before, "after": after, "changed": [],
                                                       "production_sha256": sha(root / MODEL), "status": "pass"})
    files = {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    write_json(output / "output_manifest.json", {"files": files, "manifest_payload_sha256": digest(files),
                                                "note": "Self excluded; append/change requires new release"})
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = prepare()
    if args.preflight:
        print(json.dumps({"status": "ready_internal_only", "rows": {k: len(v) for k, v in data["tables"].items()},
                          "coverage": {c: len(d["tables"]["coverage"]) for c, d in data["provinces"].items()}}, ensure_ascii=False))
    else:
        require(args.output is not None, "Explicit new output required")
        print(json.dumps(export(ROOT, args.output, data), ensure_ascii=False))


if __name__ == "__main__":
    main()


