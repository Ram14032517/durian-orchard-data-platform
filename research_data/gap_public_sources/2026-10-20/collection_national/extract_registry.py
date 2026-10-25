"""Extract the public 2021 export registry without inventing current status."""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'durian_export_orchards_2021-04-01.pdf'
URL = 'https://www.moac.go.th/foreignagri-prohibit_import-files-431391791811'
TARGETS = {
    'chanthaburi': ('22', 'จันทบุรี'),
    'chumphon': ('86', 'ชุมพร'),
    'surat thani': ('84', 'สุราษฎร์ธานี'),
    'si sa ket': ('33', 'ศรีสะเกษ'),
    'sisaket': ('33', 'ศรีสะเกษ'),
    'uttaradit': ('53', 'อุตรดิตถ์'),
}

reader = PdfReader(SOURCE)
all_rows = []
target_rows = []
candidate_failures = []
page_dates = []
for page_index, page in enumerate(reader.pages, 1):
    content = page.extract_text()
    page_dates.append(bool(re.search(r'as\s+of\s+1\s*-\s*4\s*-\s*2021', content)))
    for line in content.splitlines():
        match = re.match(r'^\s*(\d+)\s+(.+?)\s+(AC\s*.+?)\s*$', line)
        if not match:
            if re.match(r'^\s*\d+\s+.*AC', line):
                candidate_failures.append({'page': page_index, 'line': line})
            continue
        number, province, code = match.groups()
        row = {
            'source_id': 'NAT2021', 'source_no': int(number),
            'province_source': province.strip(),
            'gap_code_source': code.strip(),
            'gap_code_compact': re.sub(r'\s+', '', code),
            'source_page': page_index,
            'as_of_date': '2021-04-01',
        }
        all_rows.append(row)
        key = ' '.join(province.casefold().split())
        if key in TARGETS:
            province_code, province_th = TARGETS[key]
            target_rows.append({**row, 'province_code': province_code, 'province_th': province_th})

sequence = [row['source_no'] for row in all_rows]
assert sequence == list(range(1, max(sequence) + 1)), 'Registry row sequence incomplete or duplicate'
assert not candidate_failures, candidate_failures[:3]
assert all(page_dates), 'Not every page has the same snapshot date'
code_counts = Counter(row['gap_code_compact'] for row in all_rows)
target_code_counts = Counter(row['gap_code_compact'] for row in target_rows)
for row in target_rows:
    row['code_occurrences_in_source'] = code_counts[row['gap_code_compact']]
    row['code_occurrences_targets'] = target_code_counts[row['gap_code_compact']]

manifest = {
    'source_id': 'NAT2021', 'source_url': URL,
    'title': 'List of Registered Durian Orchards of the Export from Thailand to China',
    'agency': 'กระทรวงเกษตรและสหกรณ์ / ทะเบียนสวนทุเรียนส่งออกจีน',
    'as_of_date': '2021-04-01', 'retrieved_date': '2026-10-20',
    'file_name': SOURCE.name, 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'pages': len(reader.pages), 'rows_total_source': len(all_rows),
    'rows_targets': len(target_rows),
    'counts_by_province': dict(Counter(row['province_th'] for row in target_rows)),
    'unique_codes_targets': len({row['gap_code_compact'] for row in target_rows}),
    'duplicate_code_rows_targets': sum(row['code_occurrences_in_source'] > 1 for row in target_rows),
    'duplicate_code_rows_within_targets_only': sum(row['code_occurrences_targets'] > 1 for row in target_rows),
    'duplicate_code_definitions': 'code_occurrences_in_source counts the full 38,767-row national register; code_occurrences_targets counts only target provinces; compact removes spaces only, not hyphens/version identifiers',
    'sequence_check': 'all source numbers contiguous from 1 to final row',
    'page_date_check': 'all pages say as of 1-4-2021',
    'crop': 'ทุเรียน', 'grain': 'หนึ่งรายการเลขทะเบียนสวนในบัญชี ณ วันอ้างอิง',
    'status_scope': 'อยู่ในบัญชีสวนทุเรียนส่งออกจีน ณ 1 เมษายน 2021',
    'current_status_verified': False,
    'available_fields': ['source_no', 'province_source', 'gap_code_source'],
    'unavailable_fields': ['district', 'subdistrict', 'latitude', 'longitude', 'area_rai', 'actual_harvest_kg', 'actual_export_kg', 'certificate_expiry', 'current_status'],
    'limitations': 'ทะเบียนย้อนหลัง ไม่ใช่ผลผลิตหรือยอดส่งออกจริง ไม่ยืนยันสถานะปัจจุบัน รหัสหลายรูปแบบห้ามเชื่อมรุ่นใหม่โดยเดา',
}
for filename, data in [('registry_target_rows.json', target_rows), ('source_manifest.json', manifest)]:
    (BASE / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
with (BASE / 'registry_target_rows.csv').open('w', newline='', encoding='utf-8-sig') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(target_rows[0]))
    writer.writeheader()
    writer.writerows(target_rows)
print(json.dumps(manifest, ensure_ascii=False, indent=2))
