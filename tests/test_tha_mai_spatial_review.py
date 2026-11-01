import copy
import unittest
from tools import build_tha_mai_spatial_pilot as p
from tools import review_tha_mai_spatial_pilot as r
from tests.research_support import require_files


class PersistedThaMaiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        require_files(p.ROOT / p.DEFAULT / 'dataset.json')
        cls.dataset = p.read_json(p.ROOT / p.DEFAULT / "dataset.json")

    def test_full_persisted_geometry_reconciliation(self):
        self.assertEqual(r.verify(self.dataset)["status"], "pass")

    def test_seal_and_builder_match(self):
        p.previous.verify_seal(p.ROOT, p.DEFAULT)
        self.assertEqual(p.sha(p.ROOT/"tools/build_tha_mai_spatial_pilot.py"),
                         p.read_json(p.ROOT/p.DEFAULT/"reproducibility.json")["code_sha256"])

    def test_persisted_geometry_tampering_rejected(self):
        d = copy.deepcopy(self.dataset)
        d["tables"]["parents"][0]["geometry_sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "geometry hash"): r.verify(d)

    def test_missing_mixed_exclusion_rejected(self):
        d = copy.deepcopy(self.dataset); d["tables"]["mixed_exclusions"].pop()
        with self.assertRaisesRegex(ValueError, "mixed exclusions"): r.verify(d)

    def test_sc_w_not_omitted(self):
        units = {row["soil_unit"] for row in self.dataset["tables"]["soil_composition"]}
        self.assertTrue({"SC", "W", "UNCOVERED"}.issubset(units))

    def test_denominator_cannot_exclude_sc_w(self):
        d = copy.deepcopy(self.dataset)
        d["tables"]["soil_composition"][0]["denominator_pure_rai"] -= 100
        with self.assertRaisesRegex(ValueError, "denominator"): r.verify(d)


if __name__ == "__main__": unittest.main()
