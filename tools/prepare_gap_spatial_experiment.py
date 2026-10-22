"""Prepare a bounded GAP spatial experiment, never download, fit, or predict.

The registry is a current sampling frame, not historical orchard outcomes. The
result is deliberately train-ineligible until feature and vintage review.
Only the standard library is used so this command cannot import an estimator.
"""
import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "research_data/five_province_history"
LAYER = DATA / "gap_orchards"
OUTPUT = DATA / "gap_spatial_experiment"
PROVINCES = ("22", "33", "53", "84", "86")
ANCHORS = {"22": "04-01", "33": "05-01", "53": "06-01", "84": "07-01", "86": "07-01"}
YEARS = tuple(range(2010, 2026))
PARAMETERS = ("T2M", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "WS2M")
TARGET = "yield_kg_per_rai_calculated"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid " + label) from error
    if not math.isfinite(number):
        raise ValueError("Nonfinite " + label)
    return number


def coordinates(lat, lon):
    lat, lon = finite(lat, "latitude"), finite(lon, "longitude")
    # A second fail-closed check, not a replacement for the layer's boundary audit.
    if not 5 <= lat <= 21 or not 97 <= lon <= 106:
        raise ValueError("Coordinate outside broad Thailand bounds")
    return lat, lon


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_layer(layer):
    layer = Path(layer)
    manifest_path = layer / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported GAP layer schema")
    date.fromisoformat(manifest["snapshot_date"])
    entries = manifest["provinces"]
    code_of = lambda row: str(row.get("province_code", row.get("code", "")))
    if len(entries) != 5 or {code_of(row) for row in entries} != set(PROVINCES):
        raise ValueError("GAP layer must cover all five provinces exactly once")
    points, inventory, hashes, ids = {}, {}, {"manifest.json": digest(manifest_path)}, set()
    for entry in entries:
        code = code_of(entry)
        filename = entry["file"]
        if Path(filename).name != filename or not filename.endswith(".geojson"):
            raise ValueError("Unsafe province GeoJSON path")
        path = layer / filename
        if path.resolve().parent != layer.resolve():
            raise ValueError("GeoJSON path escapes layer")
        if entry.get("sha256") and entry["sha256"] != digest(path):
            raise ValueError("GeoJSON bytes differ from layer manifest hash")
        body = json.loads(path.read_text(encoding="utf-8"))
        if body.get("type") != "FeatureCollection":
            raise ValueError("Require a GeoJSON FeatureCollection")
        selected = []
        for feature in body["features"]:
            props, geometry = feature["properties"], feature["geometry"]
            identifier = feature.get("id", props.get("id"))
            if (not isinstance(identifier, str) or not identifier or identifier in ids
                    or (props.get("id") is not None and props["id"] != identifier)
                    or str(props["province_code"]) != code or geometry["type"] != "Point"
                    or len(geometry["coordinates"]) != 2):
                raise ValueError("Duplicate/invalid feature identity or geometry")
            if props.get("field_verified") is True:
                raise ValueError("This preparation does not authorize field-verification claims")
            if "registry_gps_unverified" not in props.get("quality_flags", []):
                raise ValueError("Missing explicit unverified registry GPS flag")
            if props.get("coordinate_quality") not in (None, "inside_province_display_boundary_unverified"):
                raise ValueError("Unsupported coordinate quality")
            if (props.get("coordinate_quality") is None
                    and props.get("quality") not in ("province_checked", "registry_unverified")):
                raise ValueError("Missing or unsupported coordinate screening status")
            lat, lon = coordinates(geometry["coordinates"][1], geometry["coordinates"][0])
            selected.append(dict(id=identifier, province_code=code, latitude=lat, longitude=lon))
            ids.add(identifier)
        expected = entry.get("displayed_features", entry.get("display_points"))
        if expected != len(selected) or not selected:
            raise ValueError("Missing province points or layer count mismatch")
        source_rows = entry["source_rows"]
        coordinate_rows = entry.get("parseable_coordinate_rows", entry.get("coordinate_rows"))
        if (not isinstance(source_rows, int) or not isinstance(coordinate_rows, int)
                or not 0 < len(selected) <= coordinate_rows <= source_rows):
            raise ValueError("Invalid coverage denominator")
        inventory[code] = dict(province_code=code,
            province_name=entry.get("province_name", entry.get("name", code)),
            source_rows=source_rows, parseable_coordinate_rows=coordinate_rows,
            accepted_unique_registry_points=len(selected),
            parseable_coordinate_row_share=coordinate_rows / source_rows,
            accepted_points_per_source_row=len(selected) / source_rows)
        points[code] = sorted(selected, key=lambda point: point["id"])
        hashes[filename] = digest(path)
    return manifest, points, inventory, hashes


def distance_km(a, b):
    """Great-circle distance; no weather-grid identity is inferred from distance."""
    lat1, lat2 = math.radians(a["latitude"]), math.radians(b["latitude"])
    dlat = lat2 - lat1
    dlon = math.radians(b["longitude"] - a["longitude"])
    square = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(min(1., max(0., square))))


def representative_points(points, maximum=8):
    """Deterministic farthest-point coverage, weighted by registry point counts.

    Start nearest the unweighted coordinate mean; choose farthest from the
    selected set. Equal-distance ties follow stable feature IDs. These are
    computational sampling strata, NOT verified NASA source cells.
    """
    if not 1 <= maximum <= 16 or not points:
        raise ValueError("Require nonempty points and 1..16 representatives")
    ordered = sorted(points, key=lambda point: point["id"])
    if len({point["id"] for point in ordered}) != len(ordered):
        raise ValueError("Duplicate registry point IDs")
    center = {key: sum(point[key] for point in ordered) / len(ordered) for key in ("latitude", "longitude")}
    first = min(range(len(ordered)), key=lambda index: (distance_km(ordered[index], center), ordered[index]["id"]))
    chosen = [first]
    nearest = [distance_km(point, ordered[first]) for point in ordered]
    while len(chosen) < maximum:
        farthest = min(range(len(ordered)), key=lambda index: (-nearest[index], ordered[index]["id"]))
        if nearest[farthest] <= 1e-9:
            break  # Identical coordinates do not create extra weather requests.
        chosen.append(farthest)
        nearest = [min(old, distance_km(point, ordered[farthest])) for point, old in zip(ordered, nearest)]
    representatives, assignments = [], []
    chosen = sorted(chosen, key=lambda index: ordered[index]["id"])
    for number, index in enumerate(chosen, 1):
        point = ordered[index]
        representatives.append(dict(sample_id=f"gap-{point['province_code']}-{number:02d}",
            province_code=point["province_code"], selected_registry_point_id=point["id"],
            latitude=point["latitude"], longitude=point["longitude"],
            assigned_registry_points=0, registration_point_weight=0., max_assignment_distance_km=0.,
            native_weather_cell_verified=False, stratum_kind="computational_nearest_representative_not_native_grid"))
    for point in ordered:
        representative = min(representatives, key=lambda rep: (distance_km(point, rep), rep["sample_id"]))
        distance = distance_km(point, representative)
        representative["assigned_registry_points"] += 1
        representative["max_assignment_distance_km"] = max(representative["max_assignment_distance_km"], distance)
        assignments.append(dict(registry_point_id=point["id"], province_code=point["province_code"],
            sample_id=representative["sample_id"], distance_km=distance))
    for representative in representatives:
        representative["registration_point_weight"] = representative["assigned_registry_points"] / len(ordered)
    if sum(rep["assigned_registry_points"] for rep in representatives) != len(ordered):
        raise ValueError("Sampling lost registry population")
    return representatives, assignments


def load_targets(path):
    """Keep one province-year evaluation reference, never one target per plot."""
    lookup = {}
    for row in read_csv(path):
        code = row["province_code"]
        if code not in PROVINCES:
            continue
        year = int(row["year_ce"])
        if year not in range(2009, 2026):
            continue
        key = code, year
        if key in lookup:
            raise ValueError("Duplicate province-year target")
        production, bearing, target = [finite(row[key], key) for key in ("production_tonnes", "bearing_rai", TARGET)]
        if (production < 0 or bearing <= 0 or target < 0
                or not math.isclose(target, production * 1000 / bearing, rel_tol=1e-10, abs_tol=1e-8)):
            raise ValueError("Invalid provincial target; no imputation or plot-label substitution")
        lookup[key] = dict(province_code=code, province_name=row["province_name"], year_ce=year,
            production_tonnes=production, bearing_rai=bearing, **{TARGET: target})
    if set(lookup) != {(p, y) for p in PROVINCES for y in range(2009, 2026)}:
        raise ValueError("Require all 85 province-years including the 2009 lag source")
    return [dict(**lookup[p, y], previous_yield_kg_rai=lookup[p, y-1][TARGET],
        target_scope="province_year_not_orchard", train_eligible=False) for p in PROVINCES for y in YEARS]


def load_controls(path):
    rows = read_csv(path)
    if len(rows) != 5 or {row["province_code"] for row in rows} != set(PROVINCES):
        raise ValueError("Require exactly five existing province reference controls")
    output = []
    for row in sorted(rows, key=lambda row: row["province_code"]):
        lat, lon = coordinates(row["weather_latitude"], row["weather_longitude"])
        output.append(dict(sample_id="control-" + row["province_code"], province_code=row["province_code"],
            latitude=lat, longitude=lon, role="original_province_reference_not_orchard",
            native_weather_cell_verified=False))
    return output


def availability_audit(targets, snapshot_date):
    snapshot = date.fromisoformat(snapshot_date)
    output = []
    for target in targets:
        code, year = target["province_code"], target["year_ce"]
        issue = date.fromisoformat(f"{year}-{ANCHORS[code]}") - timedelta(days=60)
        output.append(dict(province_code=code, year_ce=year, exploratory_issue_date=issue.isoformat(),
            registry_snapshot_date=snapshot.isoformat(), snapshot_after_issue=snapshot > issue,
            historical_registry_vintage_verified=False, historical_weather_vintage_verified=False,
            lag_and_training_label_publication_verified=False, train_eligible=False,
            status="blocked_for_training_exploratory_preparation_only"))
    return output


def write_json(path, data):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def write_csv(path, rows):
    if not rows:
        raise ValueError("Refusing an empty artifact")
    with Path(path).open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def reserve(root, run_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", run_id):
        raise ValueError("Unsafe run ID")
    root = Path(root)
    if root.resolve() != root.absolute():
        raise ValueError("Output root may not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / run_id
    destination.mkdir(exist_ok=False)
    return destination


def prepare(layer=LAYER, annual=DATA / "production_annual.csv", controls=DATA / "reference_points.csv",
            output=OUTPUT, run_id=None, maximum=8):
    if not 1 <= maximum <= 16:
        raise ValueError("Maximum points per province must be 1..16")
    source, points, inventory, hashes = load_layer(layer)
    targets, references = load_targets(annual), load_controls(controls)
    samples, assignments, coverage = [], [], []
    for code in PROVINCES:
        selected, mapping = representative_points(points[code], maximum)
        samples.extend(selected)
        assignments.extend(mapping)
        coverage.append(dict(**inventory[code], representative_points=len(selected),
            assigned_registry_points=len(mapping),
            maximum_assignment_distance_km=max(rep["max_assignment_distance_km"] for rep in selected),
            weighting_basis="one_accepted_registry_point_not_area_or_production"))
    all_points = [dict(**point, role="gap_representative") for point in samples] + references
    first_year, last_year = min(row["year_ce"] for row in targets), max(row["year_ce"] for row in targets)
    # Existing issue-date features use ten prior years for normals. These years
    # are weather context only and do not increase the number of outcome labels.
    weather_first = first_year - 10
    chunks = [(f"{start}0101", f"{min(start + 9, last_year)}1231")
              for start in range(weather_first, last_year + 1, 10)]
    jobs = [dict(sample_id=point["sample_id"], province_code=point["province_code"],
                 latitude=point["latitude"], longitude=point["longitude"], role=point["role"],
                 start=start, end=end)
            for point in all_points
            for start, end in chunks]
    manifest = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
        status="preparation_complete_no_weather_download_no_training", train_eligible=False,
        historical_pit_certified=False, registry_snapshot_date=source["snapshot_date"],
        statistical_unit="province_year", target_unit="kg_per_rai", target_rows=len(targets),
        target_years=[first_year, last_year], provinces=list(PROVINCES), gap_registry_points=len(assignments),
        representative_points=len(samples), province_controls=len(references), planned_request_jobs=len(jobs),
        sampling=dict(method="deterministic_farthest_point_then_nearest_assignment", maximum_per_province=maximum,
            weights="accepted_registry_point_counts_not_area_not_bearing_area_not_production",
            certificate_population="all_accepted_coordinate_records_not_verified_active_certificates",
            native_weather_grid_mapping="unverified_no_cell_ids_inferred", field_verified=False),
        source_sha256=dict(gap_layer=hashes, annual=digest(annual), controls=digest(controls), code=digest(__file__)),
        experiment=dict(arms=["original_province_reference", "gap_registration_weighted_weather"],
            matched_population="same_80_province_years_2010_2025", feature_engineering="same_existing_issue_rule_and_windows",
            model_and_tuning="hold_identical_between_arms_freeze_before_new_outcomes",
            weather_unavailable="stop_and_report_no_silent_drop_or_fill", fit_count=0, predictions_created=0,
            metrics_created=False, no_improvement_claim=True),
        blockers=["2026 registry cannot certify which orchards/weights existed at historical issue dates",
            "Exact historical weather and lag/training-label publication vintages remain unverified",
            "Current point coverage is uneven and GAP is not all durian orchards",
            "No farm-level measured yield or confirmed dated disease labels in this preparation",
            "Representative sampling error and native weather-source grid mapping need separate review"],
        next_steps=["Review coordinates, exclusions and per-province coverage before requesting weather",
            "Authorize bounded downloads separately; retain raw bytes, units, source metadata and hashes",
            "Verify parameter-specific source grids from authoritative metadata; do not guess cell IDs or independent sample size",
            "Aggregate weather to the same province-year feature keys using registration weights; never replicate target labels per point",
            "Review historical-vintage limits; any retrospective trial remains exploratory, not a prospective accuracy claim"])
    destination = reserve(output, run_id or datetime.now(timezone.utc).strftime("prep_%Y%m%dT%H%M%S%fZ"))
    write_csv(destination / "representative_points.csv", samples)
    write_csv(destination / "registry_assignments.csv", assignments)
    write_csv(destination / "province_coverage.csv", coverage)
    write_csv(destination / "matched_province_year_targets.csv", targets)
    write_csv(destination / "availability_audit.csv", availability_audit(targets, source["snapshot_date"]))
    write_json(destination / "weather_request_plan.json", dict(execution_performed=False,
        endpoint="https://power.larc.nasa.gov/api/temporal/daily/point", community="AG", time_standard="LST",
        parameters=list(PARAMETERS), grid_identity_verified=False,
        requested_years=[weather_first, last_year], normals_context_years=10,
        note="Request coordinates are representative GAP points, not verified native source-grid centers. No HTTP calls are made.", jobs=jobs))
    manifest["artifact_sha256"] = {path.name: digest(path) for path in sorted(destination.iterdir())}
    write_json(destination / "manifest.json", manifest)
    return destination, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layer", type=Path, default=LAYER)
    parser.add_argument("--annual", type=Path, default=DATA / "production_annual.csv")
    parser.add_argument("--controls", type=Path, default=DATA / "reference_points.csv")
    parser.add_argument("--output-root", type=Path, default=OUTPUT)
    parser.add_argument("--run-id")
    parser.add_argument("--max-points-per-province", type=int, default=8)
    args = parser.parse_args()
    destination, manifest = prepare(args.layer, args.annual, args.controls, args.output_root,
                                    args.run_id, args.max_points_per_province)
    print(json.dumps(dict(output=str(destination), train_eligible=False, target_rows=manifest["target_rows"],
        representative_points=manifest["representative_points"], planned_request_jobs=manifest["planned_request_jobs"],
        fit_count=0), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
