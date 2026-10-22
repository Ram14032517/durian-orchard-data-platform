"""UI rebuilds must not silently recollect or change the saved historical data."""
import json
from pathlib import Path
import tempfile
import unittest
from tools.build_unified_orchard_map import bundled_payload, script_json


class GapMapBuildTests(unittest.TestCase):
    def payload(self):
        return dict(provinces=[{'province_code':code} for code in ('22','33','53','84','86')],
                    districts=[],boundaries={},annual=[],harvest=[],monthly_weather=[],
                    phenology={},soil_properties=[],district_exploration=[])

    def test_script_json_cannot_close_script_or_introduce_html(self):
        value={'district':'</script><script>alert(1)</script>&\u2028\u2029'}
        serialized=script_json(value)
        self.assertNotIn('<',serialized)
        self.assertNotIn('&',serialized)
        self.assertEqual(json.loads(serialized),value)

    def test_payload_reuse_preserves_data_values_without_executing_javascript(self):
        value=self.payload();value['districts']=[{'name':'";throw Error("not JSON execution");'}]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'map.html'
            path.write_text('<script>const DATA='+script_json(value)+', $=id=>null;</script>',encoding='utf-8')
            self.assertEqual(bundled_payload(path),value)

    def test_reuse_rejects_incomplete_or_wrong_province_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'map.html'
            for value in ({},dict(self.payload(),provinces=[{'province_code':'00'}])):
                path.write_text('const DATA='+json.dumps(value)+';',encoding='utf-8')
                with self.assertRaises(ValueError):bundled_payload(path)


if __name__=='__main__':unittest.main()
