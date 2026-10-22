"""Synthetic, stdlib-only checks for bounded GAP spatial preparation; no fit/API."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import prepare_gap_spatial_experiment as gap


class GapSpatialPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.layer = self.root / "gap_orchards"
        self.layer.mkdir()
        entries = []
        for index, code in enumerate(gap.PROVINCES):
            features = []
            for number in range(5):
                identifier = f"gap-{code}-{number}"
                features.append(dict(type="Feature", id=identifier,
                    geometry=dict(type="Point", coordinates=[99. + number * .1, 9. + index]),
                    properties=dict(id=identifier, province_code=code, quality="province_checked",
                        quality_flags=["registry_gps_unverified"], field_verified=False)))
            filename = f"province_{code}.geojson"
            (self.layer / filename).write_text(json.dumps(dict(type="FeatureCollection", features=features)), encoding="utf-8")
            entries.append(dict(code=code, name="synthetic-" + code, file=filename,
                source_rows=10, coordinate_rows=7, display_points=5))
        self.manifest = dict(schema_version=1, snapshot_date="2026-10-20", provinces=entries)
        self.write_manifest()
        annual = [dict(province_code=code, province_name="synthetic-" + code, year_ce=year,
                       production_tonnes=100., bearing_rai=50., yield_kg_per_rai_calculated=2000.)
                  for code in gap.PROVINCES for year in range(2009, 2026)]
        self.annual = self.root / "annual.csv"
        gap.write_csv(self.annual, annual)
        self.controls = self.root / "controls.csv"
        gap.write_csv(self.controls, [dict(province_code=code, weather_latitude=9. + number, weather_longitude=99.)
                                     for number, code in enumerate(gap.PROVINCES)])

    def tearDown(self):
        self.temporary.cleanup()

    def write_manifest(self):
        self.layer.joinpath("manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def change_feature(self, change):
        path = self.layer / "province_22.geojson"
        data = json.loads(path.read_text())
        change(data["features"])
        path.write_text(json.dumps(data), encoding="utf-8")

    def prepare(self, run_id="synthetic"):
        return gap.prepare(self.layer, self.annual, self.controls, self.root / "results", run_id, maximum=2)

    def test_same_80_targets_never_plot_labels_and_no_training(self):
        destination, manifest = self.prepare()
        targets = gap.read_csv(destination / "matched_province_year_targets.csv")
        self.assertEqual(len(targets), 80)
        self.assertEqual(len({(row["province_code"], row["year_ce"]) for row in targets}), 80)
        self.assertFalse(any("registry_point_id" in row for row in targets))
        self.assertTrue(all(row["target_scope"] == "province_year_not_orchard" for row in targets))
        self.assertFalse(manifest["train_eligible"])
        self.assertEqual(manifest["experiment"]["fit_count"], 0)
        self.assertFalse(manifest["experiment"]["metrics_created"])
        self.assertEqual(manifest["gap_registry_points"], 25)

    def test_representatives_bounded_weighted_complete_and_deterministic(self):
        _, points, _, _ = gap.load_layer(self.layer)
        a, assignments = gap.representative_points(points["22"], 2)
        b, reverse_assignments = gap.representative_points(list(reversed(points["22"])), 2)
        self.assertEqual(a, b)
        self.assertEqual(assignments, reverse_assignments)
        self.assertEqual(len(a), 2)
        self.assertEqual(len(assignments), 5)
        self.assertEqual(sum(row["assigned_registry_points"] for row in a), 5)
        self.assertAlmostEqual(sum(row["registration_point_weight"] for row in a), 1.)
        self.assertTrue(all(not row["native_weather_cell_verified"] for row in a))

    def test_identical_coordinates_do_not_create_extra_requests(self):
        points = [dict(id=str(i), province_code="22", latitude=12., longitude=102.) for i in range(10)]
        selected, assignments = gap.representative_points(points, 8)
        self.assertEqual(len(selected), 1)
        self.assertEqual(len(assignments), 10)
        self.assertEqual(selected[0]["registration_point_weight"], 1.)

    def test_current_snapshot_historical_availability_blocked(self):
        destination, _ = self.prepare()
        audit = gap.read_csv(destination / "availability_audit.csv")
        self.assertEqual(len(audit), 80)
        self.assertTrue(all(row["snapshot_after_issue"] == "True" for row in audit))
        self.assertTrue(all(row["train_eligible"] == "False" for row in audit))
        self.assertTrue(all(row["historical_registry_vintage_verified"] == "False" for row in audit))

    def test_request_plan_is_bounded_not_executed_not_native_grid(self):
        destination, manifest = self.prepare()
        plan = json.loads((destination / "weather_request_plan.json").read_text())
        self.assertFalse(plan["execution_performed"])
        self.assertFalse(plan["grid_identity_verified"])
        self.assertEqual(plan["requested_years"], [2000, 2025])
        self.assertEqual(len(plan["jobs"]), (10 + 5) * 3)
        self.assertEqual(len(plan["jobs"]), manifest["planned_request_jobs"])
        self.assertEqual({row["province_code"] for row in plan["jobs"]}, set(gap.PROVINCES))
        self.assertTrue(all("yield" not in str(list(row)) for row in plan["jobs"]))

    def test_missing_province_duplicate_keys_or_invalid_coordinates_fail(self):
        original = deepcopy(self.manifest)
        self.manifest["provinces"].pop()
        self.write_manifest()
        with self.assertRaises(ValueError):
            gap.load_layer(self.layer)
        self.manifest = original
        self.write_manifest()
        self.change_feature(lambda rows: rows[0]["geometry"].update(coordinates=[0, 0]))
        with self.assertRaises(ValueError):
            gap.load_layer(self.layer)

    def test_duplicate_registry_point_id_fails_instead_of_silent_drop(self):
        self.change_feature(lambda rows: rows[1].update(id=rows[0]["id"]))
        with self.assertRaises(ValueError):
            gap.load_layer(self.layer)

    def test_unknown_or_field_verified_quality_claims_fail(self):
        self.change_feature(lambda rows: rows[0]["properties"].update(field_verified=True))
        with self.assertRaises(ValueError):
            gap.load_layer(self.layer)

    def test_declared_layer_hash_mismatch_fails(self):
        self.manifest["provinces"][0]["sha256"] = "0" * 64
        self.write_manifest()
        with self.assertRaises(ValueError):
            gap.load_layer(self.layer)

    def test_sampling_does_not_depend_on_province_yield_values(self):
        first, _ = self.prepare("before")
        rows = gap.read_csv(self.annual)
        for row in rows:
            row["production_tonnes"] = 200.
            row[gap.TARGET] = 4000.
        alternative = self.root / "alternative.csv"
        gap.write_csv(alternative, rows)
        second, _ = gap.prepare(self.layer, alternative, self.controls, self.root / "results", "after", maximum=2)
        self.assertEqual((first / "representative_points.csv").read_bytes(),
                         (second / "representative_points.csv").read_bytes())
        self.assertEqual((first / "weather_request_plan.json").read_bytes(),
                         (second / "weather_request_plan.json").read_bytes())

    def test_missing_duplicate_or_invalid_target_fails_no_imputation(self):
        rows = gap.read_csv(self.annual)
        for changed in (rows[:-1], rows + [rows[0]], [dict(row, bearing_rai="0") if index == 0 else row for index, row in enumerate(rows)]):
            path = self.root / "bad.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader(); writer.writerows(changed)
            with self.assertRaises(ValueError):
                gap.load_targets(path)

    def test_counts_and_source_hashes_do_not_change_inputs(self):
        original = gap.digest(self.annual)
        destination, manifest = self.prepare()
        self.assertEqual(gap.digest(self.annual), original)
        for filename, expected in manifest["artifact_sha256"].items():
            self.assertEqual(gap.digest(destination / filename), expected)
        self.assertEqual(len(gap.read_csv(destination / "province_coverage.csv")), 5)

    def test_exclusive_output_and_unsafe_run_id(self):
        self.prepare()
        with self.assertRaises(FileExistsError):
            self.prepare()
        with self.assertRaises(ValueError):
            self.prepare("../escape")
        with self.assertRaises(ValueError):
            gap.representative_points([dict(id="1")], 17)


if __name__ == "__main__":
    unittest.main()
