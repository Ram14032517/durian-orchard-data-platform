"""Phase 10F: primary invariants gate acceptance; impossible binary union is diagnostic."""
from collections import defaultdict
import math
import shapely
from shapely.geometry import Polygon
from tools import build_tha_mai_spatial_pilot as p

ALGORITHM = "directed_partition_holes_onepass_upper_bound_warning_v2"


class ReviewError(ValueError):
    def __init__(self, status, details):
        self.status, self.details = status, details
        super().__init__(f"Geometry review {status}: {details}")


def geometry(g):
    p.require(g.geom_type in ("Polygon", "MultiPolygon") and g.is_valid and not g.is_empty
              and math.isfinite(g.area), "Invalid persisted geometry")
    p.require(shapely.get_precision(g) == 0, "Changed precision model")


def holes(g):
    polygons = [g] if g.geom_type == "Polygon" else list(g.geoms)
    return [Polygon(ring) for poly in polygons for ring in poly.interiors]


def partition(g, cuts, missing, label):
    """No input mutation, geometry repair, precision change or fragment-specific waiver."""
    for x in [g] + cuts + missing: geometry(x)
    checks, contradictions = [], []
    def zero(name, area):
        value = area / 1600
        checks.append({"check":name,"value_rai":value,"pass":abs(value)<=p.TOL_RAI})
    def conflict(name, area):
        value = area / 1600
        contradictions.append({"check":name,"value_rai":value,"material":abs(value)>p.TOL_RAI})
    try:
        c = shapely.union_all(cuts); m = shapely.union_all(missing)
        one = shapely.union_all(cuts + missing)
        for name,x in [("covered",c),("uncovered",m),("onepass",one)]:
            p.require(x.is_valid and math.isfinite(x.area), f"Invalid aggregate {name}")
        complement = g.difference(c)
        zero("soil cuts double counting", sum(x.area for x in cuts)-c.area)
        zero("uncovered pieces double counting", sum(x.area for x in missing)-m.area)
        for name, pieces in [("soil",cuts),("uncovered",missing)]:
            zero(name+" pairwise overlap", sum(a.intersection(b).area
                 for i,a in enumerate(pieces) for b in pieces[i+1:]))
        zero("covered outside G", c.difference(g).area)
        zero("uncovered outside G", m.difference(g).area)
        zero("covered-uncovered overlap", c.intersection(m).area)
        zero("directed missing not represented by M", complement.difference(m).area)
        zero("M not contained in directed missing", m.difference(complement).area)
        zero("area partition", c.area+m.area-g.area)
        zero("onepass missing from G", g.difference(one).area)
        zero("onepass outside G", one.difference(g).area)
        zero("onepass area reconciliation", one.area-g.area)
        zero("onepass upper bound", max(0.,one.area-sum(x.area for x in cuts+missing)))
        zero("onepass covered lower bound", max(0.,c.area-one.area))
        zero("onepass uncovered lower bound", max(0.,m.area-one.area))
        zero("onepass excludes covered input", c.difference(one).area)
        zero("onepass excludes uncovered input", m.difference(one).area)
        # Both pair-level and aggregate tests: holes are not checked by count alone.
        outside_sum = sum(x.difference(g).area for x in cuts+missing)
        zero("all original pieces outside G", outside_sum)
        ring_reports = []
        for index,hole in enumerate(holes(g)):
            measures={"hole_index":index,"hole_area_rai":hole.area/1600,
                      "original_pieces_in_hole_rai":sum(x.intersection(hole).area for x in cuts+missing)/1600,
                      "covered_in_hole_rai":c.intersection(hole).area/1600,
                      "uncovered_in_hole_rai":m.intersection(hole).area/1600,
                      "onepass_in_hole_rai":one.intersection(hole).area/1600}
            for name in ["original_pieces_in_hole_rai","covered_in_hole_rai","uncovered_in_hole_rai","onepass_in_hole_rai"]:
                zero(f"hole {index}: {name}", measures[name]*1600)
            ring_reports.append(measures)
        # Keep the impossible operation visible; only primary invariants certify partition.
        binary = c.union(m)
        conflict("two-stage union upper bound", max(0.,binary.area-c.area-m.area))
        conflict("two-stage versus onepass: binary excess", binary.difference(one).area)
        conflict("two-stage versus onepass: binary missing", one.difference(binary).area)
        conflict("two-stage union outside G", binary.difference(g).area)
        conflict("two-stage union missing from G", g.difference(binary).area)
        for index,hole in enumerate(holes(g)):
            value=binary.intersection(hole).area
            ring_reports[index]["two_stage_in_hole_rai"]=value/1600
            conflict(f"two-stage fills original hole {index}",value)
        bad=[x for x in checks if not x["pass"]]
        material=[x for x in contradictions if x["material"]]
        upper_bound_failed=contradictions[0]["material"]
        warnings=[{"kind":"kernel_operation_upper_bound_violation", "label":label,
                   "geos_version":shapely.geos_version_string,
                   "area_difference_rai":contradictions[0]["value_rai"],
                   "operation":"C.union(M)", "diagnostics":material}] if upper_bound_failed else []
        # Other unexplained contradictions still fail closed; no ID-specific exceptions.
        status="failed" if bad else ("inconclusive" if material and not upper_bound_failed else "pass")
        return {"label":label,"status":status,"tolerance_rai":p.TOL_RAI,
                "checks":checks,"operation_conflicts":contradictions,"diagnostic_warnings":warnings,
                "holes":ring_reports,
                "areas_rai":{"G":g.area/1600,"C":c.area/1600,"M":m.area/1600,
                             "onepass":one.area/1600,"two_stage":binary.area/1600}}
    except Exception as exc:
        return {"label":label,"status":"inconclusive","error":repr(exc),"checks":checks,
                "operation_conflicts":contradictions,"tolerance_rai":p.TOL_RAI}


def review(dataset):
    """Structural/lineage/area checks precede geometry review; full pass is mandatory."""
    p.require(dataset["crs"]=="EPSG:32647","Unexpected dataset CRS")
    tables=dataset["tables"]; p.validate_tables(tables)
    row_geoms={}; fragments={r["fragment_id"]:r for r in tables["district_fragments"]}
    for name in ["parents","district_fragments","soil_intersections","uncovered","mixed_exclusions"]:
        for row in tables[name]:
            g=shapely.from_wkt(row["geometry_wkt"]); geometry(g)
            p.require(p.geom_hash(g)==row["geometry_sha256"],"Persisted geometry hash mismatch")
            p.near(g.area/1600,row["area_rai"],"persisted WKT area")
            p.near(g.area,row["area_m2"],"stored square metre area")
            row_geoms[id(row)]=g
    mixed_ids={r["fragment_id"] for r in fragments.values() if r["kind"]=="mixed"}
    exclusions=tables["mixed_exclusions"]
    p.require(len(exclusions)==len(mixed_ids) and {r["fragment_id"] for r in exclusions}==mixed_ids,
              "Incomplete/duplicate mixed exclusions")
    for row in exclusions:
        ref=fragments[row["fragment_id"]]
        p.require(row["durian_fraction"] is None,"Guessed mixed fraction")
        for field in ["parent_polygon_id","geometry_sha256","source_ids","code_sha256","area_rai","area_m2"]:
            p.require(row[field]==ref[field],"Altered mixed exclusion lineage/geometry")
    by_fragment,missing=defaultdict(list),defaultdict(list)
    areas=defaultdict(float)
    for row in tables["soil_intersections"]:
        p.require(fragments[row["fragment_id"]]["kind"]=="pure","Mixed allocated as pure soil")
        by_fragment[row["fragment_id"]].append(row_geoms[id(row)]); areas[row["soil_unit"]]+=row["area_rai"]
    for row in tables["uncovered"]:
        p.require(fragments[row["fragment_id"]]["kind"]=="pure","Mixed uncovered allocated as pure")
        missing[row["fragment_id"]].append(row_geoms[id(row)])
    areas["UNCOVERED"]=sum(r["area_rai"] for r in tables["uncovered"])
    composition=tables["soil_composition"]
    p.require(len({r["soil_unit"] for r in composition})==len(composition),"Duplicate soil composition key")
    denom=sum(r["area_rai"] for r in fragments.values() if r["kind"]=="pure")
    p.require(denom>0,"Missing pure denominator")
    for row in composition:
        p.near(row["denominator_pure_rai"],denom,"correct denominator includes SC/W/uncovered")
        p.require(row["soil_unit"] in areas,"Extra soil summary code")
        p.near(row["area_rai"],areas.pop(row["soil_unit"]),"soil summary area")
        p.require(abs(row["share_of_all_pure_pct"]-row["area_rai"]/denom*100)<=1e-9,"Share formula mismatch")
    p.require(not areas,"Missing soil summary codes")
    p.require(abs(sum(r["share_of_all_pure_pct"] for r in composition)-100)<=p.TOL_RAI/denom*100+1e-9,
              "Soil shares do not sum to 100")
    results=[]; fragments_by_parent=defaultdict(list)
    pure_geoms=[]; mixed_geoms=[]
    for row in fragments.values():
        g=row_geoms[id(row)]; fid=row["fragment_id"]
        fragments_by_parent[row["parent_polygon_id"]].append(g)
        (pure_geoms if row["kind"]=="pure" else mixed_geoms).append(g)
        if row["kind"]=="pure": results.append(partition(g,by_fragment[fid],missing[fid],fid))
    parents=[]
    for row in tables["parents"]:
        g=row_geoms[id(row)]
        remaining=shapely.from_wkt(row["remaining_wkt"])
        assigned=shapely.from_wkt(row["assigned_other_wkt"])
        unassigned=shapely.from_wkt(row["unassigned_wkt"])
        # Empty remainders are allowed, but no nonempty geometry may be discarded.
        for x in [remaining,assigned,unassigned]:
            if not x.is_empty: geometry(x)
        inside=fragments_by_parent[row["parent_polygon_id"]]
        p.near(sum(x.area for x in inside)/1600,row["inside_area_rai"],"parent inside area")
        for x,field in [(remaining,"remaining_area_rai"),(assigned,"assigned_other_area_rai"),(unassigned,"unassigned_area_rai")]:
            p.near(x.area/1600,row[field],"parent "+field)
        parents.append(partition(g,inside,[] if remaining.is_empty else [remaining],row["parent_polygon_id"]))
        if not remaining.is_empty:
            parents.append(partition(remaining,[] if assigned.is_empty else [assigned],
                                     [] if unassigned.is_empty else [unassigned],row["parent_polygon_id"]+"_remaining"))
    global_checks=[]
    for name,geoms in [("pure",pure_geoms),("mixed",mixed_geoms)]:
        merged=shapely.union_all(geoms)
        residual=(sum(x.area for x in geoms)-merged.area)/1600
        global_checks.append({"check":name+" fragment double counting","value_rai":residual,"pass":abs(residual)<=p.TOL_RAI})
    overlap=shapely.union_all(pure_geoms).intersection(shapely.union_all(mixed_geoms)).area/1600
    global_checks.append({"check":"pure-mixed overlap","value_rai":overlap,"pass":overlap<=p.TOL_RAI})
    all_reports=results+parents
    status="failed" if any(x["status"]=="failed" for x in all_reports) or any(not x["pass"] for x in global_checks) else (
        "inconclusive" if any(x["status"]=="inconclusive" for x in all_reports) else "pass")
    return {"status":status,"algorithm":ALGORITHM,"geos_version":shapely.geos_version_string,
            "shapely_version":shapely.__version__,"tolerance_rai":p.TOL_RAI,
            "pure_fragment_count":len(results),"pure_fragments":results,"parent_partitions":parents,
            "global_checks":global_checks,"dataset_digest_before_after":p.digest(dataset),
            "diagnostic_warnings":[w for x in all_reports for w in x.get("diagnostic_warnings",[])],
            "no_geometry_or_composition_mutation":True,"public_release":"HOLD"}
