"""Guard template contracts; real pointer/responsive checks are documented separately."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapUIContractTests(unittest.TestCase):
    def test_field_signal_has_readable_tokens_and_real_plot_controls(self):
        css = (ROOT / 'web/assets/css/orchard_monthly_report.css').read_text(encoding='utf-8')
        js = (ROOT / 'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertIn('--field-ink:#132d38', css)
        self.assertIn('--field-teal:#087f8c', css)
        self.assertIn('.weather-plot:fullscreen', css)
        self.assertIn("button.dataset.period=value", js)
        self.assertIn('panel.requestFullscreen()', js)
        self.assertIn('document.exitFullscreen()', js)

    def test_navigation_has_own_row_and_data_views_use_full_width(self):
        css = (ROOT / 'web/assets/css/orchard_monthly_report.css').read_text(encoding='utf-8')
        js = (ROOT / 'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertIn('document.body.dataset.workspace=id', js)
        self.assertIn("workspaceTop.append(document.querySelector('.quick-nav'),$('area-strip'))", js)
        self.assertIn('#workspace-tabs{display:flex;flex-direction:column;height:100%', css)
        self.assertIn('main,body.orchard-home main{grid-template-columns:minmax(0,1fr)}', css)
        self.assertIn('overscroll-behavior:contain', css)

    def test_orchard_theme_is_built_after_tailwind_and_logo_is_scoped(self):
        template = (ROOT / 'web/templates/unified_orchard_map.html').read_text(encoding='utf-8')
        css = (ROOT / 'web/assets/css/orchard_monthly_report.css').read_text(encoding='utf-8')
        self.assertLess(template.index('__TAILWIND_STYLE__'), template.index('__MONTHLY_STYLE__'))
        self.assertIn('class="orchard-mark"', template)
        self.assertIn('aria-hidden="true"', template)
        self.assertIn('.logout-link', css)
        self.assertIn('prefers-reduced-motion:reduce', css)
        self.assertIn('--brand:221 83% 53%', css)
        self.assertIn('hsl(var(--surface))', css)
        self.assertIn('<lumen-radio-group role="radiogroup"', template)
        self.assertIn('orchard_lumen.js', template)
        self.assertIn('orchard_lumen.css', template)

    def test_current_panel_does_not_capture_monthly_controls(self):
        js = (ROOT / 'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertNotIn("document.querySelector('.report-controls')", js)
        self.assertIn("$('report-section').querySelector('.report-controls')", js)
        self.assertIn("orchard.observations.v1", js)
        self.assertIn("currentRequest", js)

    def test_area_summary_does_not_float_over_scrolled_forms(self):
        css = (ROOT / 'web/assets/css/orchard_monthly_report.css').read_text(encoding='utf-8')
        rule = re.search(r'\.workspace-top\{([^}]+)\}', css).group(1)
        self.assertIn('position:relative', rule)
        self.assertNotIn('sticky', rule)
        self.assertNotIn('z-index', rule)
        self.assertNotIn('--workspace-top-height', css)
        self.assertNotIn('--mobile-workspace-height', css)
        js = (ROOT / 'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertNotIn('workspaceTop.offsetHeight', js)

    def test_tailwind_is_built_locally_without_map_reset(self):
        source = (ROOT / 'web/assets/css/orchard_tailwind.css').read_text(encoding='utf-8')
        generated = (ROOT / 'web/assets/css/orchard_tailwind.generated.css').read_text(encoding='utf-8')
        html = (ROOT / 'research_data/five_province_history/UNIFIED_MAP_CLASSIC.html').read_text(encoding='utf-8')
        self.assertIn('@apply', source)
        self.assertNotIn('preflight.css', source)
        self.assertIn('tailwindcss v4.3.3', generated)
        self.assertNotIn('@apply', generated)
        self.assertNotIn('__TAILWIND_STYLE__', html)
        self.assertIn('<style id="orchard-tailwind">', html)
        self.assertNotIn('cdn.tailwindcss.com', html)
        self.assertNotIn('@tailwindcss/browser', html)

    def test_area_colors_and_soil_legend_have_non_color_labels(self):
        html = (ROOT / 'web/templates/unified_orchard_map.html').read_text(encoding='utf-8')
        css = (ROOT / 'web/assets/css/orchard_monthly_report.css').read_text(encoding='utf-8')
        js = (ROOT / 'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertIn('--area-a:#2563eb', css)
        self.assertIn('--area-b:#b45309', css)
        self.assertIn('พื้นที่ A', html)
        self.assertIn('พื้นที่ B', html)
        self.assertTrue("className:'area-pin-icon area-'+which" in html)
        self.assertTrue("html:'<span><b>'+which+'</b></span>'" in html)
        self.assertIn('ไม่ใช่ระดับความเสี่ยง', html)
        self.assertIn("soilLegend.id='soil-legend'", js)
        self.assertNotIn('charCodeAt(0))%colors.length', html)

    def test_chart_css_does_not_override_leaflet_svg(self):
        for name in ['web/templates/unified_orchard_map.html', 'research_data/five_province_history/UNIFIED_MAP_CLASSIC.html']:
            html = (ROOT / name).read_text(encoding='utf-8')
            self.assertNotRegex(html, r'(?:^|[},])\s*svg\s*\{')
            self.assertIn('id="chart"', html)

    def test_map_contains_layers_at_all_breakpoints(self):
        css = (ROOT / 'web/assets/css/orchard_monthly_report.css').read_text(encoding='utf-8')
        rule = re.search(r'\.map-pane #map\{([^}]+)\}', css).group(1)
        for declaration in ['position:relative', 'overflow:hidden', 'min-width:0', 'min-height:180px']:
            self.assertIn(declaration, rule)
        self.assertIn('#chart{display:block;width:100%;height:210px}', css)

    def test_province_does_not_auto_select_a_district(self):
        html = (ROOT / 'web/templates/unified_orchard_map.html').read_text(encoding='utf-8')
        body = html.split('async function provinceChange', 1)[1].split('function districtChange', 1)[0]
        self.assertIn('เลือกอำเภอเพื่อดูชุดดิน', body)
        self.assertNotIn('districtChange(false)', body)
        self.assertIn("soil=areaControl('soil',which)", body)
        self.assertIn('soil.disabled=true', body)
        self.assertIn('window.createOrchardMapMotion.mapOptions', html)
        self.assertIn('motion:mapMotion', html)
        self.assertIn('ResizeObserver', html)

    def test_comparison_controls_are_separate_and_no_copy_a_to_b(self):
        html = (ROOT / 'web/templates/unified_orchard_map.html').read_text(encoding='utf-8')
        for control in ['province', 'province-b', 'district', 'district-b', 'soil', 'soil-b', 'clear-b', 'swap-areas']:
            self.assertEqual(html.count(f'id="{control}"'), 1)
        self.assertNotIn('id="pin-b"', html)
        self.assertIn('id="server-notice"', html)

    def test_optional_comparison_and_sidebar_leave_the_map_clear(self):
        html = (ROOT / 'web/templates/unified_orchard_map.html').read_text(encoding='utf-8')
        self.assertIn('<details id="comparison-controls">', html)
        self.assertLess(html.index('<aside>'), html.index('id="area-section"'))
        self.assertNotIn('.bindPopup(', html)
        js = (ROOT / 'web/assets/js/orchard_monthly_report.js').read_text(encoding='utf-8')
        self.assertIn("if(section.id==='area-section')return", js)

    def test_compact_editor_and_soil_information_are_separate(self):
        html = (ROOT / 'web/templates/unified_orchard_map.html').read_text(encoding='utf-8')
        self.assertIn('id="toggle-area-editor"', html)
        self.assertIn('id="apply-areas"', html)
        self.assertNotIn('id="selection-summary"', html)
        body = html.split('function selectFeature(', 1)[1].split('async function provinceChange', 1)[0]
        self.assertNotIn('scrollIntoView', body)
        self.assertNotIn('ปฏิกิริยาดิน:', body)
        self.assertIn('ข้อมูลดิน อากาศ และผลผลิตทุเรียน 5 จังหวัด', html)

    def test_weather_chart_switch_and_annual_model_present(self):
        for name in ['web/templates/unified_orchard_map.html', 'research_data/five_province_history/UNIFIED_MAP_CLASSIC.html']:
            html = (ROOT / name).read_text(encoding='utf-8')
            for metric in ['T2M', 'T2M_MAX', 'T2M_MIN', 'PRECTOTCORR',
                           'RH2M', 'ALLSKY_SFC_SW_DWN', 'WS2M']:
                self.assertIn(f'<option value="{metric}">', html)
            self.assertIn("$('chart-metric').onchange", html)
            self.assertIn('annual_yield_feature_comparison.json', html)
            self.assertIn('id="annual-year-context"', html)
            self.assertIn('id="weather-warning"', html)
            self.assertIn('ไฟล์สำรองจุดจังหวัด (ไม่ใช่พิกัด A/B)', html)
            self.assertIn('data.stale_cache', html)


if __name__ == '__main__':
    unittest.main()
