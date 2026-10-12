"""Phase 10C read-only persisted-geometry diagnosis; no GIS overlay/network/fix.

Reproduce the one fragment: python -B tools/diagnose_tha_mai_geometry.py --fixture <minimal_inputs.json>
Audit and scan persisted fragments: python -B -m tools.diagnose_tha_mai_geometry
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("research_data/internal_research/tha_mai_spatial")
PILOT = BASE / "phase10b_20261012_v1"
FAILED = BASE / "phase10b_20261012_failed_validation_v1"
OUT = BASE / "phase10c_20261012_diagnosis_v1"
FID = "cti_2568_25042_2203_0"
QC_RAI = .1  # Existing QC contract; never changed here.


def sha(path):
    with Path(path).open("rb") as f:
        h = hashlib.file_digest(f, "sha256")
    return h.hexdigest()


def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def polygons(g):
    if g.geom_type == "Polygon": return [g]
    return [p for x in getattr(g, "geoms", []) for p in polygons(x)]


def geometry_hash(g):
    return hashlib.sha256(shapely.to_wkb(shapely.normalize(g))).hexdigest()


def describe(g):
    rings = []
    for poly in polygons(g):
        for kind, ring in [("exterior", poly.exterior)] + [("hole", r) for r in poly.interiors]:
            coords = list(ring.coords)
            rings.append({"role": kind, "is_ccw": ring.is_ccw, "coordinates": len(coords),
                          "ring_enclosed_area_rai": Polygon(ring).area / 1600,
                          "minimum_nonzero_axis_spacing_m": min((abs(a-b) for axis in [0,1]
                              for a,b in zip(sorted({c[axis] for c in coords}), sorted({c[axis] for c in coords})[1:])
                              if a != b), default=None)})
    return {"type": g.geom_type, "is_valid": g.is_valid, "validity_reason": shapely.is_valid_reason(g),
            "is_empty": g.is_empty, "area_m2": g.area, "area_rai": g.area / 1600,
            "bounds": list(g.bounds) if not g.is_empty else None,
            "polygon_count": len(polygons(g)), "hole_count": sum(len(p.interiors) for p in polygons(g)),
            "geometry_sha256": geometry_hash(g), "coordinate_count": int(shapely.get_num_coordinates(g)),
            "precision_model_grid_size_m": float(shapely.get_precision(g)), "rings": rings}


def tolerance_m2(*geoms):
    # Diagnostic roundoff bound, not a replacement for area-allocation QC tolerance.
    return max(1e-6, 64 * math.ulp(max([g.area for g in geoms] + [1.])))


def operation(name, fn, upper=None):
    try:
        g = fn(); row = {"operation": name, **describe(g)}
        if upper is not None:
            excess = g.area - upper
            row.update({"upper_bound_m2": upper, "excess_m2": excess,
                        "excess_rai": excess / 1600,
                        "invariant_numeric_tolerance_m2": max(1e-6, 64*math.ulp(max(upper,1))),
                        "upper_bound_failed": excess > max(1e-6, 64*math.ulp(max(upper,1)))})
        return row, g
    except Exception as exc:
        return {"operation": name, "error": repr(exc)}, None


def load_fixture(fixture):
    return (shapely.from_wkt(fixture["G"]["geometry_wkt"]),
            [shapely.from_wkt(x["geometry_wkt"]) for x in fixture["soil_cuts"]],
            [shapely.from_wkt(x["geometry_wkt"]) for x in fixture["uncovered_pieces"]])


def diagnose(fixture):
    g, cuts, missing = load_fixture(fixture)
    c, m = shapely.union_all(cuts), shapely.union_all(missing)
    rows = []; geometries = {}
    def add(name, fn, upper=None):
        row, geom = operation(name, fn, upper); rows.append(row); geometries[name] = geom
    add("C.union(M)", lambda: c.union(m), c.area+m.area)
    add("M.union(C)", lambda: m.union(c), c.area+m.area)
    add("union_all([C,M])", lambda: shapely.union_all([c,m]), c.area+m.area)
    add("union_all([M,C])", lambda: shapely.union_all([m,c]), c.area+m.area)
    add("unary_union([C,M])", lambda: unary_union([c,m]), c.area+m.area)
    add("union_all(cuts+missing)", lambda: shapely.union_all(cuts+missing), sum(x.area for x in cuts+missing))
    add("union_all(reversed(cuts+missing))", lambda: shapely.union_all(list(reversed(cuts+missing))), sum(x.area for x in cuts+missing))
    add("G.union(M)", lambda: g.union(m), g.area+m.area)
    add("G.difference(C)", lambda: g.difference(c), g.area)
    add("C.difference(G)", lambda: c.difference(g), c.area)
    add("G.intersection(C)", lambda: g.intersection(c), min(g.area,c.area))
    add("C.intersection(M)", lambda: c.intersection(m), min(c.area,m.area))
    add("G.symmetric_difference(C)", lambda: g.symmetric_difference(c), g.area+c.area)
    add("M.difference(G.difference(C))", lambda: m.difference(g.difference(c)), m.area)
    add("G.difference(C).difference(M)", lambda: g.difference(c).difference(m), g.area)
    add("G.symmetric_difference(C.union(M))", lambda: g.symmetric_difference(c.union(m)))
    add("G.difference(C.union(M))", lambda: g.difference(c.union(m)))
    add("C.union(M).difference(G)", lambda: c.union(m).difference(g))
    # Serialization changes neither coordinates nor geometry hashes; compare independent encodings.
    for label, fn in [("WKT", lambda x: shapely.from_wkt(shapely.to_wkt(x, rounding_precision=-1))),
                      ("WKB", lambda x: shapely.from_wkb(shapely.to_wkb(x)))]:
        cc, mm = fn(c), fn(m)
        add(f"{label}_roundtrip_C.union(M)", lambda cc=cc,mm=mm: cc.union(mm), cc.area+mm.area)
    serialization = []
    for row, geom in [(fixture["G"],g)] + list(zip(fixture["soil_cuts"],cuts)) + list(zip(fixture["uncovered_pieces"],missing)):
        serialization.append({"id": row.get("fragment_id",row.get("intersection_id",row.get("uncovered_id"))),
            "stored_geometry_hash_matches": geometry_hash(geom) == row["geometry_sha256"],
            "stored_area_residual_m2": geom.area-row["area_m2"],
            "wkt_roundtrip_hash_matches": geometry_hash(shapely.from_wkt(shapely.to_wkt(geom,rounding_precision=-1))) == geometry_hash(geom),
            "wkb_roundtrip_hash_matches": geometry_hash(shapely.from_wkb(shapely.to_wkb(geom))) == geometry_hash(geom)})
    hole_matches = []
    result = geometries["C.union(M)"]
    for i, poly in enumerate(polygons(g)):
        for j, ring in enumerate(poly.interiors):
            hole = Polygon(ring)
            hole_matches.append({"polygon": i, "hole": j, "hole_area_rai": hole.area/1600,
                "covered_in_C_rai": hole.intersection(c).area/1600,
                "covered_in_M_rai": hole.intersection(m).area/1600,
                "covered_after_C_union_M_rai": hole.intersection(result).area/1600})
    return {"versions": {"python": platform.python_version(), "shapely": shapely.__version__,
                         "geos": shapely.geos_version_string, "platform": platform.platform()},
            "inputs": {"G":describe(g), "C":describe(c), "M":describe(m),
                       "cuts":[describe(x) for x in cuts], "uncovered_pieces":[describe(x) for x in missing]},
            "operations": rows, "serialization": serialization, "original_hole_tracking":hole_matches,
            "numeric_tolerance_m2": tolerance_m2(g,c,m), "qc_tolerance_rai_unchanged":QC_RAI}


def scan(tables):
    hits, missing = defaultdict(list), defaultdict(list)
    for x in tables["soil_intersections"]: hits[x["fragment_id"]].append(x)
    for x in tables["uncovered"]: missing[x["fragment_id"]].append(x)
    rows=[]; hash_mismatches=[]; totals=defaultdict(float); exported=defaultdict(float)
    for row in tables["soil_intersections"]: exported[row["soil_unit"]]+=row["area_rai"]
    for fragment in tables["district_fragments"]:
        if fragment["kind"] != "pure": continue
        fid=fragment["fragment_id"]; inputs=[fragment]+hits[fid]+missing[fid]
        for rec in inputs:
            geom=shapely.from_wkt(rec["geometry_wkt"])
            if geometry_hash(geom)!=rec["geometry_sha256"] or abs(geom.area-rec["area_m2"])>tolerance_m2(geom):
                hash_mismatches.append({"fragment_id":fid,"id":rec.get("intersection_id",rec.get("uncovered_id",fid))})
        g=shapely.from_wkt(fragment["geometry_wkt"])
        cuts=[shapely.from_wkt(x["geometry_wkt"]) for x in hits[fid]]
        misses=[shapely.from_wkt(x["geometry_wkt"]) for x in missing[fid]]
        for x,cut in zip(hits[fid],cuts): totals[x["soil_unit"]]+=cut.area/1600
        c=shapely.union_all(cuts); m=shapely.union_all(misses)
        try:
            combined=c.union(m)
            row={"fragment_id":fid,"g_rai":g.area/1600,"c_rai":c.area/1600,"m_rai":m.area/1600,
                "union_excess_rai":(combined.area-c.area-m.area)/1600,
                "review_partition_residual_rai":g.symmetric_difference(combined).area/1600,
                "soil_sum_minus_covered_rai":(sum(x.area for x in cuts)-c.area)/1600,
                "g_minus_c_rai":g.difference(c).area/1600,"c_minus_g_rai":c.difference(g).area/1600,
                "m_minus_directed_missing_rai":m.difference(g.difference(c)).area/1600,
                "directed_missing_minus_m_rai":g.difference(c).difference(m).area/1600,
                "numeric_tolerance_rai":tolerance_m2(g,c,m)/1600}
            row["union_invariant_failed"]=row["union_excess_rai"]>row["numeric_tolerance_rai"]
            row["review_qc_failed"]=row["review_partition_residual_rai"]>QC_RAI
            rows.append(row)
        except Exception as error: rows.append({"fragment_id":fid,"operation_error":repr(error)})
    summaries={x["soil_unit"]:x["area_rai"] for x in tables["soil_composition"] if x["soil_unit"]!="UNCOVERED"}
    differences=[{"soil_unit":k,"persisted_geometry_sum_rai":v,"exported_pair_sum_rai":exported[k],
                  "summary_area_rai":summaries[k],"summary_residual_rai":v-summaries[k]} for k,v in sorted(totals.items())]
    return {"fragment_results":rows,"hash_or_area_mismatches":hash_mismatches,"soil_area_composition_recheck":differences,
            "pure_fragments_scanned":len(rows),"union_invariant_failures":sum(x.get("union_invariant_failed",False) for x in rows),
            "review_qc_failures":sum(x.get("review_qc_failed",False) for x in rows),
            "operation_errors":sum("operation_error" in x for x in rows)}


def audit():
    from tools import build_tha_mai_spatial_pilot as pilot
    out=ROOT/OUT
    if out.exists(): raise FileExistsError("Diagnostic artifacts already exist; overwrite refused")
    pilot.previous.verify_seal(ROOT,PILOT); pilot.previous.verify_seal(ROOT,FAILED)
    status=read(ROOT/FAILED/"STATUS.json")
    assert status["status"]=="failed" and status["public_release"]=="HOLD"
    assert sha(ROOT/PILOT/"dataset.json")==status["dataset_sha256"]
    before=pilot.snapshot(ROOT)
    for name in ["tools/build_tha_mai_spatial_pilot.py","tools/review_tha_mai_spatial_pilot.py",
                 "tests/test_tha_mai_spatial_pilot.py","tests/test_tha_mai_spatial_review.py","docs/DURIAN_THA_MAI_SPATIAL_PILOT_TH.md"]:
        before[name]=sha(ROOT/name)
    tables=read(ROOT/PILOT/"dataset.json")["tables"]
    selected=[x for x in tables["district_fragments"] if x["fragment_id"]==FID]
    assert len(selected)==1
    fixture={"fragment_id":FID,"dataset_sha256":status["dataset_sha256"],"G":selected[0],
             "soil_cuts":[x for x in tables["soil_intersections"] if x["fragment_id"]==FID],
             "uncovered_pieces":[x for x in tables["uncovered"] if x["fragment_id"]==FID]}
    single=diagnose(fixture); population=scan(tables)
    after={k:sha(ROOT/k) for k in before}
    assert before==after, "Protected hash mismatch"
    out.mkdir(parents=True,exist_ok=False)
    (out/".gitignore").write_text("*\n",encoding="utf-8")
    write(out/"minimal_inputs.json",fixture); write(out/"operations.json",single); write(out/"fragment_scan.json",population)
    write(out/"protected_hashes.json",{"before":before,"after":after,"changed":[],"status":"pass"})
    write(out/"reproducibility.json",{"code_sha256":sha(Path(__file__)),"dataset_sha256":status["dataset_sha256"],
         "quarantine_status_sha256":sha(ROOT/FAILED/"STATUS.json"),"versions":single["versions"],
         "input_precision_changed":False,"qc_status":"FAILED unchanged","public_release":"HOLD",
         "command":"python -B -m tools.diagnose_tha_mai_geometry"})
    report=["# Geometry Operations (diagnostic, not acceptance)","", "| Operation | Area rai | Holes | Valid | Union upper-bound excess rai |", "|---|---:|---:|---|---:|"]
    for r in single["operations"]:
        report.append(f"| {r['operation']} | {r.get('area_rai','ERROR')} | {r.get('hole_count','')} | {r.get('is_valid','')} | {r.get('excess_rai','—')} |")
    (out/"OPERATIONS.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    files={x.name:sha(x) for x in sorted(out.iterdir()) if x.is_file()}
    write(out/"output_manifest.json",{"files":files,"manifest_payload_sha256":digest(files)})
    print(json.dumps({"versions":single["versions"],"holes":single["original_hole_tracking"],
         "scan":{k:v for k,v in population.items() if k not in ["fragment_results","soil_area_composition_recheck"]},
         "protected_files":len(before),"output":str(out)},ensure_ascii=False))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fixture",type=Path); args=parser.parse_args()
    if args.fixture: print(json.dumps(diagnose(read(args.fixture)),ensure_ascii=False,indent=2))
    else: audit()


if __name__=="__main__": main()
