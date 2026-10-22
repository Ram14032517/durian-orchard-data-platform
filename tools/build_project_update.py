"""Render the dated update document; never fit models or change IoT inputs."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / 'docs/updates/PROJECT_UPDATE_2026-10-22_TH.md'
OUTPUT = UPDATE.with_suffix('.html')
ATTACHMENTS = UPDATE.with_name('PROJECT_UPDATE_2026-10-22.attachments.json')

STYLE = '''
:root{font-family:-apple-system,BlinkMacSystemFont,"Thonburi","Leelawadee UI",Tahoma,sans-serif;color:#263c36;background:#f5f6f3;font-size:16px;line-height:1.95}
*{box-sizing:border-box}body{margin:0}a{color:#21675a;text-underline-offset:4px}a:hover{color:#133e35}a:focus-visible{outline:3px solid #b98233;outline-offset:4px}
.page{display:grid;grid-template-columns:230px minmax(0,810px);gap:48px;max-width:1180px;margin:auto;padding:42px 28px 70px}
nav{position:sticky;top:24px;align-self:start;font-size:13px;line-height:1.8}nav strong{display:block;margin-bottom:12px;font-size:15px}nav a{display:block;padding:6px 0;text-decoration:none;color:#53655f}
main{min-width:0;background:white;padding:36px 44px;border:1px solid #dce2dc;border-radius:12px}h1{font-size:28px;line-height:1.55;margin:0 0 8px;letter-spacing:-.3px;color:#182e27}h2{font-size:21px;line-height:1.6;margin:44px 0 16px;padding-top:16px;border-top:1px solid #e3e8e1;scroll-margin-top:24px}h3{font-size:17px;line-height:1.7;margin:28px 0 10px;color:#294e41}
p{margin:12px 0 18px}li{margin:8px 0}ul,ol{padding-left:24px}code{font-family:ui-monospace,Menlo,monospace;font-size:.84em;background:#f0f3ef;border-radius:4px;padding:2px 5px;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#f0f3ef;padding:16px;border-radius:8px;overflow:auto}strong{color:#1f4437}
.intro{font-size:12px;letter-spacing:1.3px;text-transform:uppercase;color:#54776b;margin:0 0 18px}.links{display:flex;gap:12px;flex-wrap:wrap;margin:22px 0 0;font-size:13px}.links a{padding:8px 12px;border:1px solid #cfd9d1;border-radius:6px;text-decoration:none}footer{margin-top:36px;color:#65726b;font-size:12px;line-height:1.8}
@media(max-width:850px){.page{display:block;padding:18px 14px}nav{position:static;margin-bottom:20px}nav a{display:inline-block;margin-right:16px;padding:4px 0}main{padding:26px 22px}h1{font-size:25px}}
@media print{:root{background:white;font-size:11pt}body{background:white}.page{display:block;max-width:none;padding:0}nav,.links{display:none}main{border:0;padding:0}h2,h3{break-after:avoid}a{color:inherit}p,li{orphans:3;widows:3}footer{border-top:1px solid #ddd;padding-top:10px}}
'''


def render_update(markdown):
    import mistune
    content = mistune.html(markdown)
    headings = []

    def heading(match):
        anchor = f'section-{len(headings) + 1}'
        label = re.sub('<[^>]+>', '', match.group(1))
        headings.append((anchor, html.unescape(label)))
        return f'<h2 id="{anchor}">{match.group(1)}</h2>'

    content = re.sub(r'<h2>(.*?)</h2>', heading, content, flags=re.S)
    navigation = ''.join(f'<a href="#{anchor}">{html.escape(label)}</a>' for anchor, label in headings)
    return f'''<!doctype html>
<html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>บันทึกอัปเดตโปรเจกต์สวนทุเรียน 22 ตุลาคม 2569</title>
<style>{STYLE}</style></head><body><div class="page">
<nav aria-label="สารบัญ"><strong>บันทึกการเปลี่ยนแปลง</strong>{navigation}</nav>
<main><p class="intro">Project update 2026 10 22</p>{content}
<div class="links"><a href="{UPDATE.name}">ต้นฉบับ Markdown</a><a href="attachments/GAP_5_PROVINCES_20261020.xlsx">เปิด Excel GAP</a><a href="http://127.0.0.1:8871/research_data/five_province_history/UNIFIED_MAP.html">เปิดแดชบอร์ด</a></div>
<footer>ฉบับอ่านนี้สร้างจาก Markdown ในโฟลเดอร์เดียวกัน ไม่มีสคริปต์เชื่อมต่อ IoT และไม่แก้ข้อมูลหรือโมเดลเมื่อเปิดอ่าน เอกสารแนบ Excel เก็บเฉพาะในเครื่อง</footer>
</main></div></body></html>
'''


def verify_attachment(base=UPDATE.parent, manifest_path=ATTACHMENTS):
    meta = json.loads(manifest_path.read_text(encoding='utf-8'))
    relative = Path(meta['workbook']['path'])
    path = (base / relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(base.resolve()):
        raise ValueError('Attachment must stay inside the update folder')
    if not path.is_file():
        raise FileNotFoundError(f'Local GAP attachment missing: {relative}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != meta['workbook']['sha256']:
        raise ValueError('GAP attachment differs from the preserved original')
    with zipfile.ZipFile(path) as workbook:
        if workbook.testzip() is not None:
            raise ValueError('GAP workbook ZIP integrity check failed')
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify HTML and unchanged local Excel without writing')
    args = parser.parse_args()
    result = render_update(UPDATE.read_text(encoding='utf-8'))
    digest = verify_attachment()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding='utf-8') != result:
            raise RuntimeError('HTML differs from Markdown; rebuild the update document')
        print(f'Update HTML matches Markdown; unchanged Excel SHA256 {digest}')
    else:
        OUTPUT.write_text(result, encoding='utf-8')
        print(f'Updated {OUTPUT.relative_to(ROOT)}; Excel preserved ({digest})')


if __name__ == '__main__':
    main()
