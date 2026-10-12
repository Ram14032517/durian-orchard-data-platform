"""Build a portable Render context from the Docker allowlist, never the whole repo."""
import fnmatch
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def selected_files(root=ROOT):
    rules = (root / '.dockerignore').read_text(encoding='utf-8').splitlines()
    selected = {'Dockerfile', '.dockerignore', 'render.yaml'}
    for line in rules:
        if not line.startswith('!') or line.endswith('/'):
            continue
        pattern = line[1:]
        parent = root / str(Path(pattern).parent)
        matches = [p for p in parent.glob(Path(pattern).name) if p.is_file()]
        if not matches:
            raise ValueError('Missing deployment input: ' + pattern)
        for path in matches:
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('Deployment input escapes project')
            relative = path.relative_to(root).as_posix()
            if any(part.startswith('.') for part in path.relative_to(root).parts):
                raise ValueError('Hidden input is not permitted')
            if fnmatch.fnmatchcase(relative, pattern):
                selected.add(relative)
    return sorted(selected)


def main():
    # Preserve the exact audited provincial model/data snapshot.
    from durian_model.common import check_snapshot
    check_snapshot()
    names = selected_files()
    out = ROOT / '.build/deploy'
    out.mkdir(parents=True, exist_ok=True)
    archive = out / 'durian-render.zip'
    manifest = {}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            raw = (ROOT / name).read_bytes()
            manifest[name] = hashlib.sha256(raw).hexdigest()
            bundle.writestr(name, raw)
        bundle.writestr('DEPLOY_MANIFEST.json', json.dumps(manifest, indent=2))
    print(json.dumps({'archive': str(archive), 'files': len(names),
                      'size_mb': round(archive.stat().st_size / 1_000_000, 2)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
