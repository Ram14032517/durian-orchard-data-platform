"""Keep the start page, folder indexes and VS Code task instructions navigable."""
import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ['00_START_HERE_TH.md', 'README.md', 'data/README_TH.md',
          'research_data/README_TH.md', 'tools/README_TH.md', 'docs/README_TH.md',
          'docs/archive/README_TH.md']


class NavigationTests(unittest.TestCase):
    def test_local_guide_links_exist(self):
        for name in GUIDES:
            document=ROOT/name
            for target in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
                parts=urlsplit(target)
                if parts.scheme or not parts.path:
                    continue
                with self.subTest(document=name, target=target):
                    self.assertTrue((document.parent/unquote(parts.path)).exists())

    def test_start_page_uses_existing_numbered_tasks(self):
        tasks=json.loads((ROOT/'.vscode/tasks.json').read_text(encoding='utf-8'))['tasks']
        labels=[task['label'] for task in tasks]
        self.assertEqual(len(labels),len(set(labels)))
        guide=(ROOT/'00_START_HERE_TH.md').read_text(encoding='utf-8')
        documented=re.findall(r'\*\*(Durian: [^*]+)\*\*',guide)
        self.assertGreaterEqual(len(documented),5)
        for label in documented:
            with self.subTest(label=label):self.assertIn(label,labels)
        for task in tasks:
            for argument in task.get('args',[]):
                if argument.startswith('${workspaceFolder}/'):
                    with self.subTest(argument=argument):
                        self.assertTrue((ROOT/argument.removeprefix('${workspaceFolder}/')).is_file())
