"""Missing private fixtures are explicit skips, and strict audits fail closed."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.research_support import require_files


class ResearchSupportTests(unittest.TestCase):
    def test_missing_optional_evidence_is_not_counted_as_passing(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{},clear=True):
            with self.assertRaises(unittest.SkipTest):require_files(Path(directory)/'not_present.json')

    def test_strict_research_audit_does_not_skip_missing_evidence(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'ORCHARD_REQUIRE_RESEARCH_FIXTURES':'1'}):
            with self.assertRaises(FileNotFoundError):require_files(Path(directory)/'not_present.json')


if __name__=='__main__':unittest.main()
