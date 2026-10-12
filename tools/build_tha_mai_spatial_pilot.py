"""Phase 10B: local-only, full-resolution Tha Mai soil pilot; never overwrites.

Tables are JSON with native EPSG:32647 WKT, not projected RFC7946 GeoJSON.
Only spatial-index candidates are loaded/intersected. No weather/ML/network.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys

import shapefile
import shapely
from shapely.geometry import shape, Polygon, box
from pyproj import CRS
from tools import build_four_province_internal_dataset as previous

ROOT = previous.ROOT
DISTRICT = "2203"
TOL_RAI = 0.1
FOUR = Path("research_data/internal_research/four_provinces/phase9d_20261012_v1")
RAW = Path("research_data/external/ldd_chanthaburi_2026-09-17")
LU = RAW / "landuse/Landuse_cti/จันทบุรี2568/การใช้ที่ดิน/LU_CTI_2568.shp"
SOIL = RAW / "soil/จันทบุรี/Soil_จ.จันทบุรี/Soil_จ.จันทบุรี.shp"
ADMIN = RAW / "landuse/Landuse_cti/จันทบุรี2568/ขอบเขตการปกครอง/จันทบุรี_Amp.shp"
PROVINCE = ADMIN.with_name("จันทบุรี_Pro.shp")
DEFAULT = Path("research_data/internal_research/tha_mai_spatial/phase10b_20261012_v1")
FLAGS = ["internal_only", "public_release_hold", "license_pending",
         "landuse_map_2568_not_historical_orchard_footprint", "survey_date_unverified",
         "boundary_effective_date_unverified", "soil_production_year_2561",
         "landuse_polygon_not_owner_orchard", "no_district_yield_or_weather"]
require, sha, digest, read_json = previous.require, previous.sha, previous.digest, previous.read_json


def write(path, obj):
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)


def polygonal(g):
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    return shapely.union_all([polygonal(p) for p in getattr(g, "geoms", [])])


def checked_geometry(g, role, record, repairs):
    require(not g.is_empty and math.isfinite(g.area), f"Empty/nonfinite {role}/{record}")
    raw_hash = geom_hash(g)
    if not g.is_valid:
        reason = shapely.is_valid_reason(g)
        fixed = polygonal(shapely.make_valid(g))
        change = abs(fixed.area - g.area) / 1600
        require(fixed.is_valid and not fixed.is_empty and change <= TOL_RAI,
                f"Material/invalid geometry repair {role}/{record}: {change} rai")
        repairs.append({"role": role, "source_record": record, "reason": reason,
                        "raw_geometry_sha256": raw_hash, "repaired_geometry_sha256": geom_hash(fixed),
                        "absolute_area_change_rai": change, "method": "shapely.make_valid; polygonal only"})
        return fixed
    return g


def geom_hash(g):
    return hashlib.sha256(shapely.to_wkb(shapely.normalize(g))).hexdigest()


def geometry_fields(g):
    return {"geometry_wkt": shapely.to_wkt(g, rounding_precision=-1),
            "geometry_sha256": geom_hash(g), "area_m2": g.area, "area_rai": g.area / 1600}


def parts(g):
    g = polygonal(g)
    if g.is_empty:
        return []
    result = [g] if g.geom_type == "Polygon" else list(g.geoms)
    return sorted([p for p in result if p.area > 0], key=geom_hash)


def near(actual, expected, name):
    require(math.isfinite(actual) and math.isfinite(expected) and abs(actual - expected) <= TOL_RAI,
            f"QC failed {name}: {actual} versus {expected} rai")


def dissolve(records, repairs):
    grouped = defaultdict(list)
    for index, attrs, g in records:
        code = str(attrs["AMPHOE_IDN"])
        grouped[code].append((index, checked_geometry(g, "admin", index, repairs)))
    require(len(grouped.get(DISTRICT, [])) == 2, "Tha Mai must contain exactly two source records")
    merged = {k: shapely.union_all([g for _, g in v]) for k, v in grouped.items()}
    district = merged[DISTRICT]
    internal = sum(g.area for _, g in grouped[DISTRICT]) / 1600 - district.area / 1600
    other = shapely.union_all([g for code, g in merged.items() if code != DISTRICT])
    overlap = district.intersection(other).area / 1600
    near(internal, 0, "district records overlap")
    near(overlap, 0, "district-other overlap")
    return district, other, {"district_records": [i for i, _ in grouped[DISTRICT]],
                             "internal_overlap_rai": internal, "other_district_overlap_rai": overlap}


def allocate(g, district, other):
    inside = polygonal(g.intersection(district))
    outside = polygonal(g.difference(district))
    unassigned = polygonal(outside.difference(other))
    assigned_other = polygonal(outside.intersection(other))
    near(g.area / 1600, (inside.area + outside.area) / 1600, "parent intersection + remaining")
    near(outside.area / 1600, (assigned_other.area + unassigned.area) / 1600, "outside allocation")
    return inside, outside, assigned_other, unassigned


def cover(g, soils, tree):
    hits = []
    for j in sorted(map(int, tree.query(g, predicate="intersects"))):
        record, attrs, soil = soils[j]
        cut = polygonal(g.intersection(soil))
        if cut.area > 0:
            hits.append((record, attrs, cut))
    union = shapely.union_all([cut for _, _, cut in hits])
    uncovered = polygonal(g.difference(union))
    overlap = (sum(cut.area for _, _, cut in hits) - union.area) / 1600
    near(overlap, 0, "soil double counting")
    near(g.area / 1600, (union.area + uncovered.area) / 1600, "soil coverage")
    return hits, uncovered, overlap


def validate_tables(tables):
    parent = {r["parent_polygon_id"] for r in tables["parents"]}
    fragments = {r["fragment_id"] for r in tables["district_fragments"]}
    for name, key in [("parents", "parent_polygon_id"), ("district_fragments", "fragment_id"),
                      ("soil_intersections", "intersection_id"), ("uncovered", "uncovered_id")]:
        require(len({r[key] for r in tables[name]}) == len(tables[name]), f"Duplicate {name} keys")
    require(parent and fragments, "Missing pilot parents/fragments")
    for r in tables["district_fragments"]:
        require(r["parent_polygon_id"] in parent, "Missing parent reference")
    for name in ["soil_intersections", "uncovered"]:
        for r in tables[name]:
            require(r["fragment_id"] in fragments, "Missing fragment reference")
    for rows in tables.values():
        for r in rows:
            require(r.get("source_ids") and r.get("code_sha256"), "Missing lineage")


def snapshot(root):
    result = previous.protected_snapshot(root)
    for directory in [FOUR, Path("research_data/internal_research/tha_mai_spatial")]:
        if (root / directory).exists():
            for p in (root / directory).rglob("*"):
                if p.is_file():
                    result[p.relative_to(root).as_posix()] = sha(p)
    for name in ["docs/DURIAN_CHANTHABURI_SPATIAL_FEASIBILITY_TH.md",
                 "docs/DURIAN_FOUR_PROVINCE_INTERNAL_DATASET_TH.md",
                 "tools/build_four_province_internal_dataset.py", "tests/test_four_province_internal_dataset.py"]:
        result[name] = sha(root / name)
    return dict(sorted(result.items()))


def load_records(path, encoding):
    reader = shapefile.Reader(str(path), encoding=encoding)
    return [(i, row.record.as_dict(), shape(row.shape.__geo_interface__))
            for i, row in enumerate(reader.iterShapeRecords())]


def build(root, relative):
    root, relative = Path(root), Path(relative)
    require(not relative.is_absolute() and ".." not in relative.parts and
            relative.parent == DEFAULT.parent, "Output outside pilot namespace")
    out = root / relative
    require(not out.exists(), "Artifact overwrite refused")
    previous.verify_seal(root, FOUR)
    previous.verify_seal(root, Path(previous.PILOT))
    before = snapshot(root)
    require(sha(root / previous.MODEL) == previous.MODEL_HASH, "Production hash mismatch")
    recorded = read_json(root / FOUR / "protected_verification.json")
    for path, expected in recorded["after"].items():
        require(sha(root / path) == expected, f"Prior protected hash mismatch {path}")
    analysis = read_json(root / "research_data/regional_orchards/cti_analysis.json")
    for item in analysis["input_manifest"]:
        require(sha(root / item["path"]) == item["sha256"], "Raw source hash mismatch")
    for path in [LU, SOIL, ADMIN, PROVINCE]:
        require(CRS.from_wkt((root / path.with_suffix(".prj")).read_text()).to_epsg() == 32647,
                f"Wrong CRS {path}")
    code_hash = sha(Path(__file__))
    sources = []
    for base, role in [(LU, "landuse"), (SOIL, "soil"), (ADMIN, "district"), (PROVINCE, "province")]:
        for suffix in [".shp", ".shx", ".dbf", ".prj", ".shp.xml"]:
            p = root / base.with_suffix(suffix)
            if p.exists():
                h = sha(p)
                sources.append({"source_id": role + suffix, "path": p.relative_to(root).as_posix(),
                                "sha256": h, "role": role, "license_status": "pending",
                                "survey_date": None, "boundary_effective_date": None})
    source_ids = {role: [s["source_id"] for s in sources if s["role"] == role]
                  for role in ["landuse", "soil", "district", "province"]}
    repairs = []
    district, other, topology = dissolve(load_records(root / ADMIN, "utf-8"), repairs)
    province = shapely.union_all([checked_geometry(g, "province", i, repairs)
                                 for i, _, g in load_records(root / PROVINCE, "utf-8")])
    topology["district_outside_province_rai"] = district.difference(province).area / 1600
    near(topology["district_outside_province_rai"], 0, "district-province gap")
    topology["province_admin_gap_rai_diagnostic"] = province.difference(district.union(other)).area / 1600
    # A gap elsewhere in the province is diagnostic; pilot allocation is checked below.
    soils = []
    raw_soils = shapefile.Reader(str(root / SOIL), encoding="cp874")
    for i, x in enumerate(raw_soils.iterShapeRecords()):
        if box(*x.shape.bbox).intersects(district):
            attrs = x.record.as_dict()
            require(str(attrs["soilseries"]).strip(), f"Missing soil code {i}")
            soils.append((i, attrs, checked_geometry(shape(x.shape.__geo_interface__), "soil", i, repairs)))
    soil_tree = shapely.STRtree([g for _, _, g in soils])
    landuse = shapefile.Reader(str(root / LU), encoding="utf-8")
    pure, mixed = [], []
    for i, attrs in enumerate(landuse.iterRecords()):
        code = str(attrs.as_dict()["LU_CODE"]).strip()
        if code == "A403":
            pure.append((i, code))
        elif "A403" in code.split("/"):
            mixed.append((i, code))
    require(len(pure) == 8512 and len(mixed) == 5364, "Raw LU cohort mismatch")
    all_records = pure + mixed
    bbox_tree = shapely.STRtree([box(*landuse.shape(i).bbox) for i, _ in all_records])
    candidate_indices = sorted(map(int, bbox_tree.query(district, predicate="intersects")))
    tables = {n: [] for n in ["parents", "district_fragments", "soil_intersections", "uncovered",
                              "mixed_exclusions", "soil_composition"]}
    base_lineage = {"code_sha256": code_hash, "quality_flags": FLAGS}
    pure_geoms, mixed_geoms, outside_geoms = [], [], []
    max_parent_residual = max_soil_overlap = 0.0
    for count, index in enumerate(candidate_indices):
        record, code = all_records[index]
        kind = "pure" if code == "A403" else "mixed"
        raw = shape(landuse.shape(record).__geo_interface__)
        g = checked_geometry(raw, "landuse", record, repairs)
        inside, outside, assigned, unassigned = allocate(g, district, other)
        if inside.area == 0:
            continue  # bbox false positive or boundary contact, no areal allocation.
        pid = "cti_2568_" + str(record)
        lineage = {**base_lineage, "source_ids": source_ids["landuse"] + source_ids["district"]}
        parent = {**lineage, "parent_polygon_id": pid, "source_record": record, "kind": kind,
                  "landuse_code": code, "raw_geometry_sha256": geom_hash(raw), **geometry_fields(g),
                  "inside_area_rai": inside.area / 1600, "remaining_area_rai": outside.area / 1600,
                  "assigned_other_area_rai": assigned.area / 1600, "unassigned_area_rai": unassigned.area / 1600,
                  "remaining_wkt": shapely.to_wkt(outside, rounding_precision=-1),
                  "assigned_other_wkt": shapely.to_wkt(assigned, rounding_precision=-1),
                  "unassigned_wkt": shapely.to_wkt(unassigned, rounding_precision=-1)}
        tables["parents"].append(parent)
        max_parent_residual = max(max_parent_residual, abs(g.area - inside.area - outside.area) / 1600)
        outside_geoms.extend(parts(outside))
        for part_no, fragment in enumerate(parts(inside)):
            fid = pid + "_2203_" + str(part_no)
            row = {**lineage, "parent_polygon_id": pid, "fragment_id": fid, "district_id": DISTRICT,
                   "kind": kind, **geometry_fields(fragment)}
            tables["district_fragments"].append(row)
            if kind == "mixed":
                tables["mixed_exclusions"].append({**row, "landuse_code": code,
                    "durian_fraction": None, "exclusion_reason": "mixed-use fraction unknown"})
                mixed_geoms.append(fragment)
                continue
            pure_geoms.append(fragment)
            hits, uncovered, overlap = cover(fragment, soils, soil_tree)
            max_soil_overlap = max(max_soil_overlap, overlap)
            for soil_record, attrs, cut in hits:
                for k, piece in enumerate(parts(cut)):
                    tables["soil_intersections"].append({**base_lineage,
                        "source_ids": lineage["source_ids"] + source_ids["soil"], "fragment_id": fid,
                        "intersection_id": f"{fid}_soil_{soil_record}_{k}",
                        "soil_source_record": soil_record, "soil_unit": str(attrs["soilseries"]).strip(),
                        "soil_name": str(attrs["soilserien"]).strip(), **geometry_fields(piece)})
            for k, piece in enumerate(parts(uncovered)):
                tables["uncovered"].append({**base_lineage,
                    "source_ids": lineage["source_ids"] + source_ids["soil"], "fragment_id": fid,
                    "uncovered_id": f"{fid}_uncovered_{k}", **geometry_fields(piece)})
        if count % 500 == 0:
            print(f"Spatial candidates processed {count}/{len(candidate_indices)}", flush=True)
    require(pure_geoms, "No Pure A403 inside Tha Mai")
    denom = sum(g.area for g in pure_geoms) / 1600
    pure_union = shapely.union_all(pure_geoms)
    near(denom, pure_union.area / 1600, "Pure polygon double counting")
    mixed_union = shapely.union_all(mixed_geoms)
    near(sum(g.area for g in mixed_geoms) / 1600, mixed_union.area / 1600, "Mixed polygon double counting")
    cross_overlap = pure_union.intersection(mixed_union).area / 1600
    near(cross_overlap, 0, "Pure-mixed overlap")
    totals = defaultdict(float)
    for row in tables["soil_intersections"]:
        totals[row["soil_unit"]] += row["area_rai"]
    uncovered_rai = sum(r["area_rai"] for r in tables["uncovered"])
    near(denom, sum(totals.values()) + uncovered_rai, "Pure = covered + uncovered")
    for soil, area in sorted(totals.items(), key=lambda x: (-x[1], x[0])) + [("UNCOVERED", uncovered_rai)]:
        tables["soil_composition"].append({**base_lineage, "source_ids": source_ids["landuse"] +
            source_ids["district"] + source_ids["soil"], "district_id": DISTRICT,
            "soil_unit": soil, "area_rai": area, "denominator_pure_rai": denom,
            "share_of_all_pure_pct": area / denom * 100, "landuse_map_year_be": 2568,
            "soil_production_year_be": 2561, "boundary_valid_date": None})
    share = sum(r["share_of_all_pure_pct"] for r in tables["soil_composition"])
    require(abs(share - 100) <= TOL_RAI / denom * 100 + 1e-9, "Shares do not sum to 100")
    validate_tables(tables)
    qc = {"status": "pass_with_limitations", "release_status": "accepted_internal_only", "public_release": "HOLD",
          "tolerance_rai": TOL_RAI, "share_tolerance_pct": TOL_RAI / denom * 100 + 1e-9,
          "topology": topology, "repairs": repairs,
          "counts": {n: len(r) for n, r in tables.items()}, "spatial_candidates": len(candidate_indices),
          "pure_area_rai": denom, "covered_rai": sum(totals.values()), "uncovered_rai": uncovered_rai,
          "mixed_excluded_rai": mixed_union.area / 1600, "pure_mixed_overlap_rai": cross_overlap,
          "share_sum_pct": share, "max_parent_residual_rai": max_parent_residual,
          "max_fragment_soil_overlap_rai": max_soil_overlap,
          "unassigned_parent_remainder_rai": sum(r["unassigned_area_rai"] for r in tables["parents"]),
          "flags": FLAGS}
    after = snapshot(root)
    require(before == after, "Protected files changed during overlay")
    out.mkdir(parents=True, exist_ok=False)
    (out / ".gitignore").write_text("*\n", encoding="utf-8")
    write(out / "dataset.json", {"schema_version": "phase10b_v1", "crs": "EPSG:32647",
        "geometry_format": "full-resolution WKT; metres; not RFC7946 GeoJSON", "tables": tables})
    write(out / "source_manifest.json", sources)
    write(out / "qc_report.json", qc)
    write(out / "protected_before.json", before)
    write(out / "protected_after.json", after)
    write(out / "reproducibility.json", {"code_sha256": code_hash, "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": f"python -B -m tools.build_tha_mai_spatial_pilot --output {relative.as_posix()}",
        "input_hashes": {s["path"]: s["sha256"] for s in sources},
        "dependencies": {x: importlib.metadata.version(x) for x in ["shapely", "pyshp", "pyproj", "matplotlib"]},
        "qc_contract": "Phase10A; 0.1 rai locked before overlay", "public_release": "HOLD"})
    draw_map(out / "map_preview.png", district, pure_geoms, mixed_geoms, outside_geoms, tables)
    preview = {"district_id": DISTRICT, "pure_area_rai": denom, "soil_composition": tables["soil_composition"],
               "sample_parent": [{k: v for k, v in r.items() if not k.endswith("wkt")} for r in tables["parents"][:3]],
               "qc": qc, "limitations": FLAGS}
    write(out / "dataset_preview.json", preview)
    files = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    write(out / "output_manifest.json", {"files": files, "manifest_payload_sha256": digest(files)})
    print(json.dumps({k: v for k, v in qc.items() if k not in ["repairs", "flags"]}, ensure_ascii=False), flush=True)
    return qc


def draw_map(path, district, pure, mixed, outside, tables):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch as Legend
    from matplotlib.collections import PatchCollection
    from shapely.plotting import patch_from_polygon
    def plot(ax, geometries, color, alpha=1):
        polygons = [patch_from_polygon(p) for g in geometries for p in parts(g)]
        if polygons:
            ax.add_collection(PatchCollection(polygons, facecolor=color, edgecolor="none", alpha=alpha))
    fig, axes = plt.subplots(1, 3, figsize=(17, 8), layout="constrained")
    bounds = district.bounds
    for ax in axes:
        ax.set_facecolor("#f1f5f4")
        for p in parts(district):
            ax.plot(*p.exterior.xy, color="#142f39", lw=.7, zorder=8)
        ax.set_xlim(bounds[0]-1800, bounds[2]+1800); ax.set_ylim(bounds[1]-1800, bounds[3]+1800)
        ax.set_aspect("equal"); ax.ticklabel_format(style="plain", useOffset=False)
        ax.tick_params(labelsize=7); ax.set_xlabel("UTM Easting (m)", fontsize=9)
    axes[0].set_ylabel("UTM Northing (m)", fontsize=9)
    plot(axes[0], outside, "#afbbc2", .7); plot(axes[0], pure, "#008a87")
    axes[0].set_title("1  District / Pure A403", loc="left", fontweight="bold")
    axes[0].legend(handles=[Legend(color="#008a87", label="Pure inside district"),
                            Legend(color="#afbbc2", label="Parent remainder (outside pilot)")], fontsize=8)
    units = [r["soil_unit"] for r in tables["soil_composition"] if r["area_rai"] > 0 and r["soil_unit"] != "UNCOVERED"]
    palette = plt.get_cmap("tab20")
    colors = {s: palette(i / max(1, len(units)-1)) for i, s in enumerate(units)}
    for s in units:
        plot(axes[1], [shapely.from_wkt(r["geometry_wkt"]) for r in tables["soil_intersections"] if r["soil_unit"] == s], colors[s])
    plot(axes[1], [shapely.from_wkt(r["geometry_wkt"]) for r in tables["uncovered"]], "#111111")
    axes[1].set_title("2  Soil units within Pure A403", loc="left", fontweight="bold")
    axes[1].legend(handles=[Legend(color=colors[s], label=s) for s in units] +
                   [Legend(color="#111111", label="Uncovered")], fontsize=7, ncol=3, loc="upper right")
    plot(axes[2], pure, "#008a87"); plot(axes[2], mixed, "#cf7833", .9)
    axes[2].set_title("3  Pure / excluded mixed-use", loc="left", fontweight="bold")
    axes[2].legend(handles=[Legend(color="#008a87", label="Pure A403"),
                            Legend(color="#cf7833", label="Mixed (unknown durian fraction)")], fontsize=8)
    fig.suptitle("THA MAI | 2203 | Internal spatial soil pilot", fontsize=18, fontweight="bold", color="#142f39")
    fig.supxlabel("LU map 2568 | Soil production 2561 | Boundary date unverified | EPSG:32647 | PUBLIC HOLD\n"
                  "Land-use polygons, not confirmed owner orchards. No district yield / weather / causal inference.", fontsize=10)
    fig.savefig(path, dpi=160); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=DEFAULT)
    args = parser.parse_args()
    try:
        build(ROOT, args.output)
    except Exception as error:
        print(f"FAILED — no accepted release: {error}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
