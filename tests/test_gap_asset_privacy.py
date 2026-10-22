"""Local preview must not expose source evidence or exploratory registry joins."""
import unittest
from unittest.mock import Mock
from tools.serve_orchard_analysis import Handler, ROOT


class GapAssetPrivacyTests(unittest.TestCase):
    def test_private_source_and_preparation_paths_are_blocked_before_static_serving(self):
        for relative in ('research_data/gap_public_sources/2026-10-20/README.md',
                         'research_data/five_province_history/gap_spatial_experiment/gap_spatial_prep_20261021_verified/manifest.json',
                         'research_data/five_province_history/gap_orchards/',
                         'research_data/five_province_history/point_weather_cache/a.json'):
            handler=object.__new__(Handler)
            handler.path='/'+relative
            handler.translate_path=Mock(return_value=str(ROOT/relative))
            handler.send_error=Mock()
            self.assertIsNone(handler.send_head())
            handler.send_error.assert_called_once_with(404)


if __name__=='__main__':unittest.main()
