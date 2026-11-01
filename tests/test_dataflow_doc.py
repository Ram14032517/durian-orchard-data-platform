"""The dataflow reader is offline, reproducible and linked to real source paths."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from tools.build_dataflow_doc import ROOT,SOURCE,OUTPUT,render

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='a' and values.get('href'):self.links.append(values['href'])

class DataflowTests(unittest.TestCase):
    def test_reader_matches_markdown_without_scripts_or_live_frames(self):
        text=OUTPUT.read_text(encoding='utf-8')
        self.assertEqual(text,render(SOURCE.read_text(encoding='utf-8')))
        self.assertNotRegex(text.lower(),r'<(?:script|iframe)\b')
        self.assertIn('flow-title',text)
        for term in ['sensor_readings','/api/weather','/api/orchard-harvest','Open-Meteo','localStorage','point-in-time','ยังไม่ sync เข้า Supabase']:
            self.assertIn(term,text)

    def test_relative_links_point_to_existing_project_files_or_anchors(self):
        text=OUTPUT.read_text(encoding='utf-8');links=Links();links.feed(text)
        for link in links.links:
            if link.startswith('#'):
                self.assertIn('id="'+link[1:]+'"',text)
            elif '://' not in link:
                target=(SOURCE.parent/link.split('#')[0]).resolve()
                self.assertTrue(target.is_relative_to(ROOT))
                self.assertTrue(target.exists(),link)

if __name__=='__main__':unittest.main()
