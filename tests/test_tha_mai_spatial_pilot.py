"""Synthetic geometry regression tests; no raw overlay or training in unit tests."""
import copy
from pathlib import Path
import tempfile
import unittest
import shapely
from shapely.geometry import box, Polygon
from tools import build_tha_mai_spatial_pilot as p


class ThaMaiPilotTests(unittest.TestCase):
    def test_dissolve_two_records(self):
        d, other, q = p.dissolve([(4, {"AMPHOE_IDN": "2203"}, box(0, 0, 40, 40)),
                                 (5, {"AMPHOE_IDN": "2203"}, box(80, 0, 120, 40)),
                                 (6, {"AMPHOE_IDN": "2204"}, box(160, 0, 200, 40))], [])
        self.assertEqual(d.area / 1600, 2)
        self.assertEqual(q["district_records"], [4, 5])
        self.assertEqual(q["other_district_overlap_rai"], 0)

    def test_missing_district_record_fails(self):
        with self.assertRaises(ValueError):
            p.dissolve([(4, {"AMPHOE_IDN": "2203"}, box(0, 0, 40, 40))], [])

    def test_material_admin_overlap_fails(self):
        with self.assertRaises(ValueError):
            p.dissolve([(4, {"AMPHOE_IDN": "2203"}, box(0, 0, 40, 40)),
                        (5, {"AMPHOE_IDN": "2203"}, box(20, 0, 60, 40))], [])

    def test_boundary_crossing_not_centroid(self):
        inside, remaining, other, unassigned = p.allocate(box(0, 0, 80, 40),
                                                        box(0, 0, 20, 40), box(20, 0, 60, 40))
        self.assertEqual(inside.area / 1600, .5)
        self.assertEqual(remaining.area / 1600, 1.5)
        self.assertEqual(other.area / 1600, 1)
        self.assertEqual(unassigned.area / 1600, .5)

    def test_soil_sc_w_uncovered_once(self):
        soils = [(0, {"soilseries": "SC"}, box(0, 0, 20, 40)),
                 (1, {"soilseries": "W"}, box(20, 0, 30, 40))]
        hits, missing, overlap = p.cover(box(0, 0, 40, 40), soils, shapely.STRtree([x[2] for x in soils]))
        self.assertEqual([h[1]["soilseries"] for h in hits], ["SC", "W"])
        self.assertEqual(sum(g.area for _, _, g in hits) / 1600, .75)
        self.assertEqual(missing.area / 1600, .25)
        self.assertEqual(overlap, 0)

    def test_no_double_counting(self):
        soils = [(0, {}, box(0, 0, 40, 40)), (1, {}, box(0, 0, 40, 40))]
        with self.assertRaises(ValueError):
            p.cover(box(0, 0, 40, 40), soils, shapely.STRtree([x[2] for x in soils]))

    def test_no_soil_retains_all_uncovered(self):
        _, missing, overlap = p.cover(box(0, 0, 40, 40), [], shapely.STRtree([]))
        self.assertEqual(missing.area / 1600, 1)

    def test_geometry_hash_and_wkt_roundtrip(self):
        g = box(0, 0, 40, 40)
        row = p.geometry_fields(g)
        self.assertEqual(p.geom_hash(shapely.from_wkt(row["geometry_wkt"])), row["geometry_sha256"])
        self.assertEqual(row["area_m2"], row["area_rai"] * 1600)

    def test_polygon_holes_not_filled(self):
        g = Polygon([(0,0), (80,0), (80,80), (0,80)], [[(20,20), (20,60), (60,60), (60,20)]])
        hits, missing, overlap = p.cover(g, [(0, {}, box(0,0,80,80))], shapely.STRtree([box(0,0,80,80)]))
        self.assertEqual(hits[0][2].area, 4800)
        self.assertEqual(missing.area, 0)

    def tables(self):
        common = {"source_ids": ["s"], "code_sha256": "c"}
        return {"parents": [{**common, "parent_polygon_id": "p"}],
                "district_fragments": [{**common, "parent_polygon_id": "p", "fragment_id": "f"}],
                "soil_intersections": [{**common, "fragment_id": "f", "intersection_id": "i"}],
                "uncovered": [], "soil_composition": [], "mixed_exclusions": []}

    def test_referential_integrity(self):
        tables = self.tables(); p.validate_tables(tables)
        tables["soil_intersections"][0]["fragment_id"] = "absent"
        with self.assertRaises(ValueError): p.validate_tables(tables)

    def test_duplicate_keys_fail(self):
        tables = self.tables(); tables["parents"] *= 2
        with self.assertRaises(ValueError): p.validate_tables(tables)

    def test_missing_lineage_fails(self):
        tables = self.tables(); tables["parents"][0]["source_ids"] = []
        with self.assertRaises(ValueError): p.validate_tables(tables)

    def test_immutable_json(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "record.json"; p.write(path, {"a": 1})
            with self.assertRaises(FileExistsError): p.write(path, {"a": 2})
            self.assertEqual(p.read_json(path), {"a": 1})

    def test_existing_release_rejected_before_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / p.DEFAULT).mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                p.build(folder, p.DEFAULT)

    def test_output_cannot_escape(self):
        with self.assertRaisesRegex(ValueError, "namespace"):
            p.build(p.ROOT, Path("../bad"))

    def test_locked_threshold(self):
        self.assertEqual(p.TOL_RAI, .1)
        with self.assertRaises(ValueError): p.near(.101, 0, "test")


if __name__ == "__main__": unittest.main()
