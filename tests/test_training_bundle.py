from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from zipfile import ZipFile
from tools.package_training_bundle import INPUTS, package


class BundleTests(TestCase):
    def test_packages_sources_without_changing_them_and_preserves_snapshot(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            base=root/'research_data/five_province_history'
            folder=base/'training'
            folder.mkdir(parents=True)
            for name in INPUTS:
                (base/name).write_bytes(b'source bytes\r\n')
            (folder/'panel.csv').write_bytes(b'model bytes\r\n')
            (root/'docs').mkdir()
            (root/'docs/PORTFOLIO_PUBLICATION_TH.md').write_text('publication notes')
            path,created=package(root)
            self.assertTrue(created)
            with ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read('sources/weather_daily.csv'),b'source bytes\r\n')
                self.assertEqual(archive.read('panel.csv'),b'model bytes\r\n')
            original=path.read_bytes()
            (folder/'panel.csv').write_bytes(b'later model experiment')
            self.assertEqual(package(root),(path,False))
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual((base/'weather_daily.csv').read_bytes(),b'source bytes\r\n')

    def test_missing_source_does_not_create_partial_zip(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            folder=root/'research_data/five_province_history/training'
            folder.mkdir(parents=True)
            with self.assertRaises(FileNotFoundError):package(root)
            self.assertFalse((folder/'training_bundle.zip').exists())
