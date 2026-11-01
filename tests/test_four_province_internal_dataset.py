"""Cache-only Phase 9D regression/QC tests; no ML fitting or live downloads."""
import copy
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from tools import build_four_province_internal_dataset as expansion
from tests.research_support import require_files


class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_files(expansion.ROOT / expansion.PILOT / 'output_manifest.json',
                      expansion.ROOT / expansion.OAE)
        cls.data = expansion.prepare()

    def validate(self, tables=None, lineage=None, sources=None):
        d = self.data
        expansion.validate_tables(tables if tables is not None else d["tables"],
                                  lineage if lineage is not None else d["lineage"],
                                  sources if sources is not None else d["source_manifest"])

    def test_complete_cohort(self):
        self.validate()
        self.assertEqual(len(self.data["tables"]["province_year"]), 80)
        self.assertEqual(len(self.data["tables"]["weather_profile_month"]), 960)
        self.assertEqual(sum(c[4] for c in expansion.CONFIGS), 13714)

    def test_pilot_exact_equivalence(self):
        original = expansion.read_json(expansion.ROOT / expansion.PILOT / "dataset.json")["tables"]
        for name, rows in self.data["provinces"]["22"]["tables"].items():
            self.assertEqual(rows, [{k: v for k, v in r.items() if k != "release_id"} for r in original[name]])

    def test_missing_province_year_fails(self):
        tables = copy.deepcopy(self.data["tables"])
        tables["province_year"].pop()
        with self.assertRaisesRegex(ValueError, "province-year"):
            self.validate(tables)

    def test_missing_month_fails(self):
        tables = copy.deepcopy(self.data["tables"])
        tables["weather_profile_month"].pop()
        with self.assertRaisesRegex(ValueError, "monthly keys"):
            self.validate(tables)

    def test_duplicate_key_fails(self):
        tables = copy.deepcopy(self.data["tables"])
        tables["coverage"].append(tables["coverage"][0])
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            self.validate(tables)

    def test_invalid_cross_province_join_fails(self):
        tables = copy.deepcopy(self.data["tables"])
        tables["province_year"][0]["soil_map_pair_id"] = tables["soil_map_vintage"][1]["soil_map_pair_id"]
        with self.assertRaisesRegex(ValueError, "Cross-province"):
            self.validate(tables)

    def test_missing_lineage_fails(self):
        traces = [r for r in self.data["lineage"] if not (r["table_name"] == "province_year" and r["row_key"] == "86/2006")]
        with self.assertRaisesRegex(ValueError, "Lineage missing"):
            self.validate(lineage=traces)

    def test_orphan_source_fails(self):
        with self.assertRaisesRegex(ValueError, "Orphan"):
            self.validate(sources=[])

    def test_actual_coverage_and_missingness(self):
        for code, data in self.data["provinces"].items():
            self.assertEqual({r["year_ce"] for r in data["tables"]["coverage"]}, set(expansion.YEARS))
            for row in data["tables"]["coverage"]:
                self.assertEqual(row["weather_months"], 12)
                self.assertEqual(row["oae_measures_present"], 4)
                self.assertEqual(row["yield_status"], "present_in_workbook")
                self.assertIsNotNone(row["yield_kg_per_rai"])

    def test_missing_oae_keeps_null(self):
        frame = pd.DataFrame(columns=["province_name", "year", "item"])
        data, anchors, coverage = expansion.province_oae(frame, "86", "ชุมพร")
        self.assertEqual(len(data), 20)
        self.assertTrue(all(r["yield_kg_per_rai"] is None for r in data.values()))
        self.assertTrue(all(r["yield_status"] == "missing" for r in coverage))
        self.assertTrue(all(not r for r in anchors.values()))

    def test_unit_conflict_fails(self):
        frame = pd.DataFrame([{"province_name": "ชุมพร", "year": 2549, "crop_year": 2549,
                               "item": "ผลผลิตต่อเนื้อที่ให้ผล", "unit": "tonnes", "commodity": "ทุเรียน", "data": 4}])
        with self.assertRaisesRegex(ValueError, "unit conflict"):
            expansion.province_oae(frame, "86", "ชุมพร")

    def test_no_missing_weight_renormalization(self):
        value, coverage = expansion.aggregate([2., None], [.5, .5])
        self.assertIsNone(value)
        self.assertEqual(coverage, .5)

    def test_vintages_and_area_contract(self):
        for code, _, _, vintage, count, points in expansion.CONFIGS:
            d = self.data["provinces"][code]
            s = d["tables"]["soil_map_vintage"][0]
            self.assertEqual(s["landuse_map_year_be"], vintage)
            self.assertEqual(s["pure_polygons"], count)
            self.assertIsNone(s["survey_date"])
            expansion.close(sum(r["pure_intersection_rai"] for r in d["tables"]["soil_composition"]) + s["uncovered_rai"], s["pure_A403_total_rai"], "area", .1)
            self.assertEqual(len(d["tables"]["sampling_points"]), points)
            expansion.close(sum(r["weight"] for r in d["tables"]["sampling_points"]), 1, "weights", 1e-7)

    def test_raw_and_cache_hashes(self):
        for source in self.data["source_manifest"]:
            self.assertEqual(expansion.sha(expansion.ROOT / source["path"]), source["sha256"])
        self.assertEqual(expansion.sha(expansion.ROOT / expansion.MODEL), expansion.MODEL_HASH)

    def test_artifact_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "research_data/internal_research/four_provinces/existing"
            output.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "overwrite refused"):
                expansion.output_path(root, output)

    def test_outside_output_refused(self):
        with self.assertRaisesRegex(ValueError, "direct child"):
            expansion.output_path(expansion.ROOT, expansion.ROOT / "production")

    def test_preflight_input_change_refused_before_mkdir(self):
        output = expansion.ROOT / "research_data/internal_research/four_provinces/unit_test_not_created"
        self.assertFalse(output.exists())
        bad = dict(self.data, input_hashes={expansion.OAE: "incorrect"})
        with self.assertRaisesRegex(ValueError, "Input changed"):
            expansion.export(expansion.ROOT, output, bad)
        self.assertFalse(output.exists())

    def test_failed_province_never_accepted(self):
        with patch.object(expansion, "prepare_province", side_effect=ValueError("unit conflict")):
            with self.assertRaisesRegex(ValueError, "failed_not_accepted"):
                expansion.prepare()

    def test_sealed_release_csv_json_and_schema_agree(self):
        folder = expansion.ROOT / "research_data/internal_research/four_provinces/phase9d_20261012_v1"
        if not folder.exists():
            self.skipTest("Release not yet exported; live-input contract covered separately")
        expansion.verify_seal(expansion.ROOT, folder)
        dataset = expansion.read_json(folder / "dataset.json")["tables"]
        schema = expansion.read_json(folder / "schema.json")
        for name, rows in dataset.items():
            with (folder / (name + ".csv")).open(encoding="utf-8-sig", newline="") as f:
                csv_data = list(csv.DictReader(f))
            self.assertEqual(len(rows), len(csv_data))
            self.assertEqual(list(rows[0]), schema["tables"][name]["columns"])
            self.assertEqual(len(rows), schema["tables"][name]["row_count"])
            for typed, text in zip(rows, csv_data):
                self.assertEqual({k: "" if v is None else str(v) for k, v in typed.items()}, text)

    def test_sealed_release_flags_and_references(self):
        folder = expansion.ROOT / "research_data/internal_research/four_provinces/phase9d_20261012_v1"
        if not folder.exists():
            self.skipTest("Release not yet exported")
        dataset = expansion.read_json(folder / "dataset.json")["tables"]
        traces = [expansion.json.loads(line) for line in (folder / "field_lineage.jsonl").read_text(encoding="utf-8").splitlines()]
        expansion.validate_tables({k: v for k, v in dataset.items() if k != "quality_flags"}, traces,
                                  expansion.read_json(folder / "source_manifest.json")["sources"])
        parent_keys = {(name, "/".join(str(r[k]) for k in expansion.KEYS[name]))
                       for name, rows in dataset.items() if name != "quality_flags" for r in rows}
        for flag in dataset["quality_flags"]:
            self.assertIn((flag["table_name"], flag["row_key"]), parent_keys)
        old = expansion.read_json(expansion.ROOT / expansion.PILOT / "dataset.json")["tables"]["quality_flags"]
        old_keys = {(r["table_name"], r["row_key"], r["flag_code"]) for r in old}
        got = [{k: v for k, v in r.items() if k != "release_id"} for r in dataset["quality_flags"]
               if (r["table_name"], r["row_key"], r["flag_code"]) in old_keys]
        self.assertEqual(got, [{k: v for k, v in r.items() if k != "release_id"} for r in old])

    def test_release_protected_and_hold(self):
        folder = expansion.ROOT / "research_data/internal_research/four_provinces/phase9d_20261012_v1"
        if not folder.exists():
            self.skipTest("Release not yet exported")
        manifest = expansion.read_json(folder / "source_manifest.json")
        self.assertEqual(manifest["public_release"], "HOLD")
        self.assertEqual(manifest["historical_PIT"], "not_certified")
        protected = expansion.read_json(folder / "protected_verification.json")
        self.assertEqual(protected["before"], protected["after"])
        for path, h in protected["before"].items():
            self.assertEqual(expansion.sha(expansion.ROOT / path), h)


if __name__ == "__main__":
    unittest.main()
