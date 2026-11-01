"""Cache-only Phase 9C QC plus failure-path regression tests. No GIS overlay."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import patch
from tests.research_support import require_files

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("chanthaburi_pilot", ROOT / "tools/build_chanthaburi_internal_pilot.py")
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_files(ROOT / pilot.OAE, ROOT / pilot.REGIONAL / 'cti_analysis.json',
                      ROOT / 'research_data/soil_evidence_chanthaburi/analysis.json')
        with patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
            cls.data = pilot.prepare(ROOT)

    def test_real_input_coverage(self):
        rows = self.data["tables"]["coverage"]
        self.assertEqual([r["year_ce"] for r in rows], list(range(2006, 2026)))
        self.assertTrue(all(r["yield_status"] == "present_in_workbook" for r in rows))
        self.assertTrue(all(r["weather_months"] == 12 for r in rows))

    def test_real_soil_and_sampling(self):
        s = self.data["tables"]["soil_map_vintage"][0]
        self.assertEqual(s["pure_polygons"], 8512)
        self.assertGreater(s["SC_rai"], 0)
        self.assertGreater(s["W_rai"], 0)
        self.assertGreater(s["uncovered_rai"], 0)
        self.assertAlmostEqual(sum(r["weight"] for r in self.data["tables"]["sampling_points"]), 1, places=7)
        self.assertEqual(self.data["unique_response_profiles"], 11)

    def test_missing_yield_stays_null_with_full_weather_years(self):
        frame = pd.read_excel(ROOT / pilot.OAE, sheet_name="durian")
        mask = (frame.year == 2549) & frame.item.eq("ผลผลิตต่อเนื้อที่ให้ผล") & frame.province_name.eq("จันทบุรี")
        values, refs, coverage = pilot.oae_records(frame.loc[~mask])
        self.assertIsNone(values[2006]["yield_kg_per_rai"])
        self.assertEqual(coverage[0]["yield_status"], "missing")
        self.assertEqual(len(coverage), 20)
        self.assertEqual(len(self.data["tables"]["weather_profile_year"]), 20)

    def test_duplicate_oae_fails(self):
        frame = pd.read_excel(ROOT / pilot.OAE, sheet_name="durian")
        one = frame[(frame.year == 2549) & frame.province_name.eq("จันทบุรี")].iloc[[0]]
        with self.assertRaisesRegex(ValueError, "Duplicate OAE"):
            pilot.oae_records(pd.concat([frame, one], ignore_index=True))

    def test_oae_unit_conflict_fails(self):
        frame = pd.read_excel(ROOT / pilot.OAE, sheet_name="durian")
        mask = (frame.year == 2549) & frame.province_name.eq("จันทบุรี")
        frame.loc[mask, "unit"] = "wrong unit"
        with self.assertRaisesRegex(ValueError, "unit conflict"):
            pilot.oae_records(frame)

    def test_missing_stratum_is_not_renormalized(self):
        val, coverage = pilot.aggregate([2, None], [.5, .5])
        self.assertIsNone(val)
        self.assertEqual(coverage, .5)

    def test_monthly_completeness_and_annual_units(self):
        months = [{"month": m, "days": 30, "T2M": 20, "RH2M": 70,
                   "ALLSKY_SFC_SW_DWN": 18, "PRECTOTCORR": 2, "rain_mm_month": 60}
                  for m in range(1, 13)]
        result = pilot.annual(months)
        self.assertEqual(result["weather_precip_total_mm"], 720)
        self.assertEqual(result["weather_solar_mean_mj_m2_day"], 18)
        months[0]["rain_mm_month"] = None
        self.assertIsNone(pilot.annual(months)["weather_precip_total_mm"])
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            pilot.annual(months[:-1])

    def test_duplicate_keys_and_nonfinite_values_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            pilot.keyed([{"year": 2006}, {"year": 2006}], ["year"], "test")
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            pilot.number(float("inf"))

    def test_every_dataset_row_has_resolvable_lineage(self):
        sources = {s["source_id"] for s in self.data["source_manifest"]}
        traced = {(r["table_name"], r["row_key"]) for r in self.data["lineage"]}
        self.assertTrue(all(r["source_id"] in sources for r in self.data["lineage"]))
        for table, rows in self.data["tables"].items():
            for row in rows:
                key = "/".join(str(row[k]) for k in pilot.KEYS[table])
                self.assertIn((table, key), traced)
        self.assertTrue(any("durian!row=" in r["source_locator"] for r in self.data["lineage"]))

    def test_no_publication_date_guesses(self):
        self.assertTrue(all(s["publication_time"] is None for s in self.data["source_manifest"]))
        self.assertTrue(all(r["survey_date"] is None for r in self.data["tables"]["province_year"]))
        self.assertTrue(all(s["availability_status"] == "unverified_historical_vintage" for s in self.data["source_manifest"]))

    def test_cache_hash_tamper_fails_without_network(self):
        original = pilot.read_json
        def altered(path):
            obj = original(path)
            if str(path).endswith("cti_406_52.json.source.json"):
                obj["sha256"] = "0" * 64
            return obj
        with patch.object(pilot, "read_json", side_effect=altered), patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
            with self.assertRaisesRegex(ValueError, "Source hash mismatch"):
                pilot.prepare(ROOT)

    def test_missing_cache_record_fails_without_future_or_network_fill(self):
        original = pilot.read_json
        def altered(path):
            obj = original(path)
            if str(path).endswith("cti_406_52.json"):
                obj["properties"]["parameter"]["T2M"].pop("200601")
            return obj
        with patch.object(pilot, "read_json", side_effect=altered), patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
            with self.assertRaisesRegex(ValueError, "Profile signature conflict"):
                pilot.prepare(ROOT)

    def test_input_mutation_blocks_export_before_writing(self):
        bad = copy.deepcopy(self.data)
        name = next(iter(bad["input_hashes"]))
        bad["input_hashes"][name] = "0" * 64
        output = ROOT / "research_data/internal_research/chanthaburi_pilot/not_created_fail_fast_test"
        with self.assertRaisesRegex(ValueError, "Input changed"):
            pilot.export(ROOT, output, bad)
        self.assertFalse(output.exists())

    def test_output_boundary_and_existing_artifact_protection(self):
        with self.assertRaisesRegex(ValueError, "Output must"):
            pilot.export(ROOT, ROOT / "research_data/regional_orchards/overwrite", self.data)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / "research_data/internal_research/chanthaburi_pilot/existing"
            out.mkdir(parents=True)
            marker = out / "keep.txt"
            marker.write_text("keep")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                pilot.export(root, out, self.data)
            self.assertEqual(marker.read_text(), "keep")

    def test_export_schema_dictionary_hash_seal_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tools").mkdir()
            shutil.copyfile(ROOT / "tools/build_chanthaburi_internal_pilot.py", root / "tools/build_chanthaburi_internal_pilot.py")
            (root / Path(pilot.MODEL).parent).mkdir(parents=True)
            shutil.copyfile(ROOT / pilot.MODEL, root / pilot.MODEL)
            data = copy.deepcopy(self.data)
            data["input_hashes"] = {}
            out = root / "research_data/internal_research/chanthaburi_pilot/test_release"
            with patch.object(pilot, "protected_snapshot", return_value={}), patch.object(socket, "socket", side_effect=AssertionError("Network forbidden")):
                report = pilot.export(root, out, data, {})
            self.assertEqual(report["status"], "pass_with_limitations")
            obj = pilot.read_json(out / "dataset.json")
            schema = pilot.read_json(out / "schema.json")
            for table, rows in obj["tables"].items():
                self.assertEqual(len(rows), schema["tables"][table]["row_count"])
            manifest = pilot.read_json(out / "output_manifest.json")
            self.assertTrue(all(pilot.sha(out / name) == h for name, h in manifest["files"].items()))
            self.assertEqual(pilot.digest(manifest["files"]), manifest["manifest_payload_sha256"])
            csv = pd.read_csv(out / "province_year.csv")
            self.assertEqual(len(csv), 20)
            self.assertEqual(csv.yield_kg_per_rai.iloc[0], obj["tables"]["province_year"][0]["yield_kg_per_rai"])
            self.assertTrue((out / "data_dictionary.csv").exists())
            self.assertEqual(pilot.read_json(out / "source_manifest.json")["public_release"], "HOLD")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                pilot.export(root, out, data, {})


if __name__ == "__main__":
    unittest.main()
