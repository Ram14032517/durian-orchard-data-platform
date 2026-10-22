"""Presentation contracts: a map-first layout must not hide the data semantics."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class OrchardStudioTests(unittest.TestCase):
    def test_theme_is_last_and_built_locally(self):
        template=(ROOT/'web/templates/unified_orchard_map.html').read_text(encoding='utf-8')
        self.assertLess(template.index('__MONTHLY_STYLE__'),template.index('__STUDIO_STYLE__'))
        self.assertLess(template.index('__GAP_STYLE__'),template.index('__STUDIO_STYLE__'))
        self.assertIn('id="orchard-studio"',template)
        self.assertIn('__MAP_MOTION_CODE__',template)
        self.assertLess(template.index('__MAP_MOTION_CODE__'),template.index("const map=L.map"))

    def test_full_height_map_and_sidebar_are_separate_from_advanced_editor(self):
        script=(ROOT/'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertIn("atlasStage.append(mapPanel)",script)
        self.assertIn("atlasSidebar.append($('gap-orchard-controls'),soilPicker,atlasSoilDetails)",script)
        self.assertNotIn('soilPicker.append(soilPickerSummary,mapPanel',script)
        self.assertIn("soilPicker.open=false",script)
        self.assertIn("gapAdvancedSummary.textContent='ตัวกรองเพิ่มเติม'",(ROOT/'web/templates/unified_orchard_map.html').read_text(encoding='utf-8'))

    def test_responsive_motion_focus_and_source_caveats_remain(self):
        css=(ROOT/'web/assets/css/orchard_studio.css').read_text(encoding='utf-8')
        for text in ('atlas-side-panel','atlas-map-stage','minmax(0, 1fr) 344px','overflow: auto','prefers-reduced-motion','focus-visible'):
            self.assertIn(text,css)
        self.assertEqual(css.count('{'),css.count('}'))
        script=(ROOT/'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertIn('ยังไม่ยืนยันภาคสนาม',script)
        self.assertIn('สีหมุดไม่ใช่ความเสี่ยงโรค',script)

    def test_map_focus_mode_does_not_require_browser_fullscreen_permission(self):
        script=(ROOT/'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertIn('atlas-focus-mode',script)
        self.assertIn("event.key==='Escape'",script)
        self.assertIn("atlasFullscreen.setAttribute('aria-pressed',String(expanded))",script)
        self.assertNotIn('atlasStage.requestFullscreen',script)


if __name__=='__main__':unittest.main()
