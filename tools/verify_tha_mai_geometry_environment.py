"""Phase 10E: diagnostic only, installed libraries and sealed fixture only.

Run with national-analysis-venv Python -I -B. No installation or GIS overlay.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "research_data/internal_research/tha_mai_spatial"
OUT = BASE / "phase10e_20261012_verification_v1"
FIXTURE = BASE / "phase10c_20261012_diagnosis_v1/minimal_inputs.json"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def worker(package_path):
    if package_path != "-":
        sys.path.insert(0, package_path)
    sys.path.insert(0, str(ROOT))
    import shapely
    from shapely.geometry import Polygon
    from tools import diagnose_tha_mai_geometry as d

    fixture = d.read(FIXTURE)
    result = d.diagnose(fixture)
    g, cuts, missing = d.load_fixture(fixture)
    c, m = shapely.union_all(cuts), shapely.union_all(missing)
    modes = {"one_pass": shapely.union_all(cuts + missing), "two_stage": c.union(m)}
    result["partition_comparison"] = {
        name: {"area_rai": geom.area / 1600,
               "symmetric_difference_G_rai": geom.symmetric_difference(g).area / 1600,
               "outside_G_rai": geom.difference(g).area / 1600,
               "missing_G_rai": g.difference(geom).area / 1600,
               "G_covers_result_boolean": g.covers(geom),
               "result_covers_G_boolean": geom.covers(g),
               "original_holes_filled_rai": [Polygon(ring).intersection(geom).area / 1600
                   for poly in d.polygons(g) for ring in poly.interiors]}
        for name, geom in modes.items()}
    library_dir = Path(shapely.__file__).resolve().parent.parent / "shapely.libs"
    result["runtime"] = {"executable": sys.executable,
        "shapely_module": shapely.__file__, "dependency_chain": "Python -> Shapely -> GEOS C API -> GEOS",
        "geos_dlls": {str(p): sha(p) for p in sorted(library_dir.glob("*geos*.dll"))}}
    result["fixture_sha256"] = sha(FIXTURE)
    assert len(cuts) == 11 and len(missing) == 10
    assert all(row["stored_geometry_hash_matches"] and row["wkb_roundtrip_hash_matches"]
               and row["wkt_roundtrip_hash_matches"] for row in result["serialization"])
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


def audit():
    sys.path.insert(0, str(ROOT))
    from tools import build_tha_mai_spatial_pilot as p
    from tools import diagnose_tha_mai_geometry as d
    before = p.read_json(OUT / "preflight_protected_hashes.json")
    assert not (OUT / "comparison.json").exists(), "Refuse overwrite"
    assert sha(FIXTURE) == "8fcb42f34be4ada1fd5d786730a2c765ffc06173d08df87a22f5ef08fb49eaeb"
    assert sha(ROOT / d.PILOT / "dataset.json") == "48bdbce32528719effbdea646db162e382a193c28972fd53054808d37223bb2a"
    environments = [
        ("national_analysis_venv", ROOT / ".build/national-analysis-venv/Scripts/python.exe", "-"),
        ("bundled_python_project_packages", Path(sys.base_prefix) / "python.exe", str(ROOT / ".build/python")),
        ("bundled_python_soil_packages", Path(sys.base_prefix) / "python.exe", str(ROOT / ".build/soil-map-packages"))]
    results = []
    for name, executable, packages in environments:
        run = subprocess.run([str(executable), "-I", "-B", str(Path(__file__).resolve()),
                              "--worker", packages], capture_output=True, text=True,
                             encoding="utf-8", check=True, timeout=60)
        result = json.loads(run.stdout)
        result["environment_name"] = name
        result["executable_sha256"] = sha(executable)
        p.write(OUT / f"{name}.json", result)
        results.append(result)
    # Diagnostic self-checks: compare identical installed kernel copies, not certify a release.
    assert len({r["fixture_sha256"] for r in results}) == 1
    assert all(r["partition_comparison"]["two_stage"]["outside_G_rai"] > .1 for r in results)
    assert all(r["partition_comparison"]["one_pass"]["symmetric_difference_G_rai"] < .1 for r in results)
    assert all(abs(r["partition_comparison"]["two_stage"]["original_holes_filled_rai"][0]
                   - 14.277753561022967) < 1e-8 for r in results)
    assert all(r["operations"] == results[0]["operations"] for r in results)
    summary = {"status": "diagnostic_only_independent_kernel_unavailable",
        "dataset_status": "QC_FAILED_QUARANTINED", "public_release": "HOLD",
        "qc_tolerance_rai": .1, "distinct_geos_versions": sorted({r["versions"]["geos"] for r in results}),
        "distinct_geos_dll_hash_sets": len({tuple(sorted(r["runtime"]["geos_dlls"].values())) for r in results}),
        "independent_kernel_tested": False, "self_checks": "passed",
        "results": [{"environment": r["environment_name"], "versions": r["versions"],
                     "comparison": r["partition_comparison"]} for r in results],
        "code_sha256": sha(__file__), "fixture_sha256": sha(FIXTURE)}
    p.write(OUT / "comparison.json", summary)
    changed = [name for name, expected in before.items() if not (ROOT / name).exists()
               or sha(ROOT / name) != expected]
    assert not changed, changed
    assert sha(ROOT / p.previous.MODEL) == p.previous.MODEL_HASH
    p.write(OUT / "protected_verification.json", {"checked": len(before), "changed": changed,
        "production_sha256": sha(ROOT / p.previous.MODEL), "all_unchanged": True})
    print(json.dumps({"environments": len(results), "geos_versions": summary["distinct_geos_versions"],
                      "protected_unchanged": len(before), "self_checks": "pass"}))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--worker"]:
        worker(sys.argv[2])
    else:
        audit()
