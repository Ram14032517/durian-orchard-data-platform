"""Independent persisted-geometry QC and readable map; never modifies pilot v1."""
from pathlib import Path
from collections import defaultdict
import json
import shapely
from tools import build_tha_mai_spatial_pilot as p

REVIEW = p.DEFAULT.with_name("phase10b_20261012_review_v1")


def verify(dataset):
    # Public caller contract remains fail-closed: a contradictory kernel result is not a pass.
    from tools.robust_tha_mai_geometry_review import review, ReviewError
    before = p.digest(dataset)
    report = review(dataset)
    p.require(before == p.digest(dataset), "Review mutated input")
    if report["status"] != "pass":
        conflicts = [{"label":r["label"], "status":r["status"]} for r in
                     report["pure_fragments"] + report["parent_partitions"] if r["status"] != "pass"]
        raise ReviewError(report["status"], conflicts)
    return {"status":"pass", "persisted_geometry_checks":True, "no_double_counting":True,
            "mixed_exclusions_complete":True, "sc_w_uncovered_in_denominator":True,
            "parent_count":len(dataset["tables"]["parents"]),
            "pure_fragment_count":report["pure_fragment_count"], "algorithm":report["algorithm"]}



def main():
    root = p.ROOT; out = root / REVIEW
    p.require(not out.exists(), "Review overwrite refused")
    p.previous.verify_seal(root, p.DEFAULT)
    before = p.snapshot(root)
    dataset = p.read_json(root / p.DEFAULT / "dataset.json")
    q = p.read_json(root / p.DEFAULT / "qc_report.json")
    r = verify(dataset); tables = dataset["tables"]
    p.require(p.sha(root / "tools/build_tha_mai_spatial_pilot.py") ==
              p.read_json(root / p.DEFAULT / "reproducibility.json")["code_sha256"], "Builder version changed")
    out.mkdir(parents=True, exist_ok=False)
    (out / ".gitignore").write_text("*\n", encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.collections import PatchCollection
    from shapely.plotting import patch_from_polygon
    district, _, _ = p.dissolve(p.load_records(root/p.ADMIN, "utf-8"), [])
    fig, axes = plt.subplots(1, 3, figsize=(18, 9))
    fig.subplots_adjust(left=.045, right=.99, top=.86, bottom=.17, wspace=.16)
    def paint(ax, geoms, color):
        patches = [patch_from_polygon(part) for g in geoms for part in p.parts(g)]
        if patches: ax.add_collection(PatchCollection(patches, facecolor=color, edgecolor="none"))
    pure = [shapely.from_wkt(r["geometry_wkt"]) for r in tables["district_fragments"] if r["kind"] == "pure"]
    mixed = [shapely.from_wkt(r["geometry_wkt"]) for r in tables["mixed_exclusions"]]
    outside = [shapely.from_wkt(r["remaining_wkt"]) for r in tables["parents"]]
    top = [r["soil_unit"] for r in tables["soil_composition"][:10]]
    palette = ["#087f8c", "#4477aa", "#ee6677", "#228833", "#ccbb44", "#aa3377",
               "#66ccee", "#b95b21", "#7775ad", "#59945a"]
    colors = dict(zip(top, palette)); colors.update({"SC": "#343b45", "W": "#1558ec", "Other units": "#ccd2d8", "Uncovered": "#000000"})
    for ax in axes:
        ax.set_facecolor("#f5f7f7")
        for part in p.parts(district): ax.plot(*part.exterior.xy, lw=.8, color="#183640", zorder=5)
        a,b,c,d = district.bounds
        ax.set_xlim(a-1000,c+1000); ax.set_ylim(b-1200,d+1200); ax.set_aspect("equal")
        ax.ticklabel_format(style="plain", useOffset=False); ax.tick_params(labelsize=8)
        ax.set_xlabel("UTM Easting (m)", fontsize=9)
    axes[0].set_ylabel("UTM Northing (m)", fontsize=9)
    paint(axes[0], outside, "#b9c4cc"); paint(axes[0], pure, "#008c87")
    paint(axes[2], pure, "#008c87"); paint(axes[2], mixed, "#cf7833")
    grouped = defaultdict(list)
    for row in tables["soil_intersections"]:
        unit = row["soil_unit"] if row["soil_unit"] in colors else "Other units"
        grouped[unit].append(shapely.from_wkt(row["geometry_wkt"]))
    for unit, geoms in grouped.items(): paint(axes[1], geoms, colors[unit])
    paint(axes[1], [shapely.from_wkt(r["geometry_wkt"]) for r in tables["uncovered"]], colors["Uncovered"])
    handles = [[Patch(color="#008c87",label="Pure A403 inside district"),Patch(color="#b9c4cc",label="Parent remainder outside pilot")],
               [Patch(color=c,label=s) for s,c in colors.items()],
               [Patch(color="#008c87",label="Pure A403"),Patch(color="#cf7833",label="Excluded mixed-use; fraction unknown")]]
    for ax, title, legend in zip(axes, ["1  District / Pure A403", "2  Soil units within Pure A403", "3  Pure vs mixed-use"], handles):
        ax.set_title(title, fontsize=13, fontweight="bold", loc="left", pad=12)
        ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(.5,-.06), ncol=3 if ax==axes[1] else 1, fontsize=8, frameon=False)
    fig.suptitle("THA MAI | Internal spatial soil pilot | PUBLIC HOLD", fontsize=21,fontweight="bold",color="#183640",y=.975)
    fig.text(.5,.915,f"Pure A403: {q['pure_area_rai']:,.2f} rai   |   Mixed excluded: {q['mixed_excluded_rai']:,.2f} rai",ha="center",fontsize=13)
    fig.text(.5,.016,"LU map 2568 | Soil production 2561 | Boundary date unverified | EPSG:32647\n"
             "Soil map: top 10 + SC/W; remaining 30 codes grouped for display only. Full 42 units retained in dataset.\n"
             "Not confirmed owner orchards; no district yield, district weather or causal inference.",ha="center",fontsize=9)
    fig.savefig(out/"map_preview.png",dpi=160); plt.close(fig)
    r.update({"source_output_manifest_sha256": p.sha(root/p.DEFAULT/"output_manifest.json"),
              "review_code_sha256": p.sha(Path(__file__)), "public_release": "HOLD"})
    p.write(out/"persisted_geometry_qc.json",r)
    p.write(out/"schema_and_dictionary.json",{"crs":"EPSG:32647", "area_m2":"planar area in square metres",
        "area_rai":"area_m2 / 1600", "geometry_wkt":"full resolution native projected WKT, not RFC7946",
        "source_record":"0-based record index in source SHP/DBF, bound to source manifest SHA256",
        "parent_polygon_id":"cti_2568_<source_record>", "fragment_id":"parent + district + deterministic part index",
        "intersection_id":"fragment + source soil record + deterministic part index",
        "remaining_wkt":"parent outside Tha Mai; retained, not dropped",
        "assigned_other_wkt":"remainder assigned to union of other districts, not other district-level allocation",
        "unassigned_wkt":"remainder outside union of all administrative district boundaries",
        "soil_unit":"raw soilseries map unit; SC/W are diagnostic categories, not validated soil series",
        "share_of_all_pure_pct":"100 * area_rai / all Pure A403 clipped to Tha Mai, including SC/W/uncovered",
        "durian_fraction":"null for all mixed-use: never inferred", "lineage":"source_ids + code_sha256 + geometry_sha256",
        "soil_map_year":"production 2561, not known survey date", "admin_date":"unverified; XML dates not survey/effective date"})
    after = {k:v for k,v in p.snapshot(root).items() if not k.startswith(REVIEW.as_posix()+"/")}
    p.require(before == after, "Protected files changed during review")
    p.write(out/"protected_verification.json",{"before":before,"after":after,"status":"pass","changed":[]})
    files = {x.name:p.sha(x) for x in sorted(out.iterdir()) if x.is_file()}
    p.write(out/"output_manifest.json",{"files":files,"manifest_payload_sha256":p.digest(files)})
    print(json.dumps(r))


if __name__ == "__main__": main()
