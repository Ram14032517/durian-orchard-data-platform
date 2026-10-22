"""GAP display transformation: privacy, denominators and conservative GPS gates."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gap_map_layer", ROOT / "tools/build_gap_map_layer.py")
gap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gap)


def polygon(x=98, y=6):
    return {"type": "Polygon", "coordinates": [[[x, y], [x+1, y], [x+1, y+1], [x, y+1], [x, y]]]}


def row(code="plot-a", **updates):
    result = {"province_code": "86", "plot_code": code, "latitude": 6.5,
        "longitude": 98.5, "gps_flag": "DD lat,lon อ่านได้", "district": "อำเภอทดสอบ",
        "tambon": "ตำบลทดสอบ", "crop_raw": "ทุเรียน", "status_raw": "ได้รับการรับรอง",
        "issued": "2025-01-01", "expired": "2028-01-01", "area_rai": 12.0,
        "source_id": "SAFE", "source_row": 1, "owner_name": "PRIVATE PERSON",
        "gps_raw": "DO NOT PUBLISH", "production_kg_reported": 999999}
    result.update(updates)
    return result


class GapMapLayerTests(unittest.TestCase):
    def setUp(self):
        self.boundaries = {code: polygon() for code in gap.PROVINCES}
        self.sources = {"SAFE": {"url": gap.GAP_URL, "title": "GAP public registry"}}

    def build(self, rows):
        return gap.build_layer(rows, self.boundaries, self.sources)

    def test_private_fields_omitted_and_not_a_verified_orchard(self):
        manifest, layers = self.build([row()])
        feature = layers["86"]["features"][0]
        self.assertEqual(set(feature["properties"]), gap.EXPOSED_PROPERTIES)
        serialized = json.dumps(layers)
        for secret in ("PRIVATE PERSON", "DO NOT PUBLISH", "plot-a", "999999"):
            self.assertNotIn(secret, serialized)
        self.assertFalse(feature["properties"]["field_verified"])
        self.assertIn("registry_gps_unverified", feature["properties"]["quality_flags"])
        self.assertEqual(manifest["totals"]["display_points"], 1)

    def test_duplicates_same_key_and_same_coordinate_collapse(self):
        manifest, layers = self.build([row(), row(source_row=2)])
        self.assertEqual(manifest["totals"]["source_rows"], 2)
        self.assertEqual(manifest["totals"]["distinct_registry_keys"], 1)
        self.assertEqual(manifest["totals"]["duplicate_rows_collapsed"], 1)
        self.assertEqual(layers["86"]["features"][0]["properties"]["registry_rows"], 2)

    def test_duplicate_conflicting_coordinates_quarantines_entire_key(self):
        manifest, _ = self.build([row(), row(latitude=6.6)])
        self.assertEqual(manifest["totals"]["display_points"], 0)
        self.assertEqual(manifest["excluded_counts"]["conflicting_coordinates_for_registry_key"], 2)

    def test_no_centroids_swapped_axes_or_third_value_repairs(self):
        rows = [row("a", latitude=None, longitude=None),
                row("b", gps_flag="DD lon,lat สลับแกนชัดเจน"),
                row("c", gps_flag="DD lat,lon อ่านได้; มีค่าที่สามไม่ตีความ"),
                row("d", latitude=7.5), row("e", latitude=100.0)]
        manifest, _ = self.build(rows)
        self.assertEqual(manifest["totals"]["display_points"], 0)
        self.assertEqual(manifest["totals"]["excluded_rows"], len(rows))
        self.assertEqual(manifest["totals"]["coordinate_rows"], 4)
        self.assertIn("outside_simplified_province_boundary", manifest["excluded_counts"])

    def test_id_stable_under_input_order_and_not_registry_literal(self):
        rows = [row("one"), row("two", longitude=98.6)]
        _, first = self.build(rows)
        _, second = self.build(list(reversed(rows)))
        self.assertEqual(first, second)
        self.assertNotEqual(first["86"]["features"][0]["id"], "one")

    def test_same_coordinate_different_keys_retained_but_flagged(self):
        manifest, layers = self.build([row("one"), row("two")])
        self.assertEqual(manifest["totals"]["display_points"], 2)
        for feature in layers["86"]["features"]:
            self.assertIn("shared_coordinate", feature["properties"]["quality_flags"])

    def test_date_status_does_not_overwrite_reported_status(self):
        manifest, layers = self.build([row("future", issued="2027-01-01"),
                                      row("old", expired="2025-02-01"),
                                      row("bad", issued="not a date")])
        states = {f["properties"]["date_status"] for f in layers["86"]["features"]}
        self.assertEqual(states, {"future_issue", "expired", "invalid_dates"})
        self.assertTrue(all(f["properties"]["status_reported"] == "ได้รับการรับรอง"
                            for f in layers["86"]["features"]))

    def test_point_in_polygon_holes_edges_and_multipart(self):
        geometry = polygon()
        geometry["coordinates"].append([[98.4,6.4],[98.6,6.4],[98.6,6.6],[98.4,6.6],[98.4,6.4]])
        self.assertFalse(gap.point_in_geometry(98.5,6.5,geometry))
        self.assertTrue(gap.point_in_geometry(98.4,6.5,geometry))
        self.assertTrue(gap.point_in_geometry(98,6,geometry))
        multi = {"type": "MultiPolygon", "coordinates": [geometry["coordinates"], polygon(100,9)["coordinates"]]}
        self.assertTrue(gap.point_in_geometry(100.5,9.5,multi))

    def test_nonfinite_missing_key_unknown_sources_and_non_target(self):
        manifest, _ = self.build([row(latitude=float("nan")), row("", latitude=6.5)])
        self.assertEqual(manifest["totals"]["excluded_rows"], 2)
        with self.assertRaises(ValueError):
            self.build([row(source_id="UNKNOWN")])
        with self.assertRaises(ValueError):
            self.build([row(province_code="10")])

    def test_source_link_allowlist(self):
        self.assertEqual(gap.safe_source_url(gap.GAP_URL+"?action=10&q=abc"), gap.GAP_URL+"?action=10&q=abc")
        for unsafe in ("javascript:alert(1)", "http://gap.doa.go.th/searchgap",
                       "https://evil.example/searchgap", "https://gap.doa.go.th/private",
                       "https://user:pass@gap.doa.go.th/searchgap"):
            with self.assertRaises(ValueError):
                gap.safe_source_url(unsafe)

    def test_boundary_fallback_extracts_json_without_evaluating_scripts(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/"existing.html"
            boundaries = {"type":"FeatureCollection", "features": [
                {"properties":{"province_code":code}, "geometry":polygon()}
                for code in gap.PROVINCES]}
            target.write_text("<script>const DATA="+json.dumps({"boundaries":boundaries})+",evil=1;</script>")
            selected, meta = gap.load_boundaries(None,target)
            self.assertEqual(set(selected),set(gap.PROVINCES))
            self.assertFalse(meta["field_verified"])

    def test_generated_snapshot_counts_hashes_and_allowlist(self):
        output = ROOT/"research_data/five_province_history/gap_orchards"
        path = output/"manifest.json"
        if not path.exists():
            self.skipTest("Generate the local GAP display snapshot to run integration checks")
        manifest = gap.read_json(path)
        self.assertEqual(manifest["totals"]["source_rows"],64215)
        self.assertEqual(manifest["totals"]["coordinate_rows"],34743)
        self.assertEqual(manifest["totals"]["distinct_registry_keys"],64214)
        all_ids = set()
        for province in manifest["provinces"]:
            data = (output/province["file"]).read_bytes()
            self.assertEqual(gap.digest(data),province["sha256"])
            layer = json.loads(data)
            self.assertEqual(len(layer["features"]),province["display_points"])
            self.assertEqual(province["source_rows"],province["display_points"]+
                             province["excluded_rows"]+province["duplicate_rows_collapsed"])
            for feature in layer["features"]:
                self.assertNotIn(feature["id"],all_ids)
                all_ids.add(feature["id"])
                self.assertEqual(set(feature["properties"]),gap.EXPOSED_PROPERTIES)
                self.assertFalse(feature["properties"]["field_verified"])
                self.assertTrue(all(sid in manifest["sources"] for sid in feature["properties"]["source_ids"]))
        self.assertEqual(len(all_ids),manifest["totals"]["display_points"])


if __name__ == "__main__":
    unittest.main()
