"""Package the saved regional research data without rebuilding or changing CSVs."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

try:
    from .prepare_monthly_training import INPUTS
except ImportError:
    from prepare_monthly_training import INPUTS

ROOT = Path(__file__).resolve().parents[1]

def package(root=ROOT):
    base = root / 'research_data/five_province_history'
    folder = base / 'training'
    target = folder / 'training_bundle.zip'
    if target.exists():
        with ZipFile(target) as archive:
            if archive.testzip() is not None:
                raise ValueError('Existing ZIP is damaged. Preserve it and investigate before rebuilding.')
        return target, False
    sources = [(base / name, 'sources/' + name) for name in INPUTS]
    sources.extend((path, path.name) for path in sorted(folder.iterdir())
                   if path.is_file() and path.suffix in ('.csv', '.json', '.md'))
    sources.append((root / 'docs/PORTFOLIO_PUBLICATION_TH.md', 'PORTFOLIO_PUBLICATION_TH.md'))
    for path, _ in sources:
        if not path.is_file():
            raise FileNotFoundError(f'Missing source: {path}')
    # A failed creation never replaces an earlier research snapshot.
    with ZipFile(target, 'x', ZIP_DEFLATED) as archive:
        for path, name in sources:
            archive.write(path, name)
    with ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError('Created ZIP failed integrity verification')
    return target, True

if __name__ == '__main__':
    path, created = package()
    print(f'{"Created" if created else "Preserved existing snapshot"}: {path}')
    print('Regional research data only; this does not back up private orchard readings or prove training readiness.')
