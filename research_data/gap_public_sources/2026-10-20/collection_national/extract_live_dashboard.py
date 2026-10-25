"""Read complete public DOA GAP dashboards; preserve UI status definitions."""
import hashlib
import html
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
TARGETS = {'จันทบุรี': '22', 'ชุมพร': '86', 'สุราษฎร์ธานี': '84', 'ศรีสะเกษ': '33', 'อุตรดิตถ์': '53'}
SOURCES = [
    ('NATLIVE_DURIAN', 'gap_durian_group_live.html', 'https://gap.doa.go.th/reportbyplant?t=4&r=78', 'ทุเรียน', 'GAPdurian'),
    ('NATLIVE_ALLCROPS', 'gap_online_public_dashboard.html', 'https://gap.doa.go.th/', 'พืชทุกชนิด', 'GAPallcrops'),
]
all_rows, manifests = [], []
for source_id, filename, url, crop, scope in SOURCES:
    path = BASE / filename
    original = path.read_text(encoding='utf-8')
    assert original.rstrip().endswith('</html>'), 'Incomplete download'
    # Commented legacy columns are not part of the displayed source table.
    document = re.sub(r'<!--.*?-->', '', original, flags=re.S)
    assert 'ผลการดำเนินงาน ณ วันที่ 20-ต.ค.-2569' in document
    if scope == 'GAPdurian':
        assert 'ผลการดำเนินงานพืชทุเรียน' in document
    table = re.findall(r'<table\b.*?</table>', document, re.S | re.I)[0]
    raw_rows = re.findall(r'<tr\b.*?</tr>', table, re.S | re.I)

    def cells(row):
        return [re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', value))).strip()
                for value in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', row, re.S | re.I)]

    groups = cells(raw_rows[0])[1:]
    units = cells(raw_rows[1])
    assert len(groups) == 9 and units == ['ราย', 'แปลง', 'ไร่'] * 9
    found = set()
    for row_number, raw_row in enumerate(raw_rows[2:], 3):
        values = cells(raw_row)
        if not values or values[0] not in TARGETS:
            continue
        assert len(values) == 28, values
        province = values[0]
        found.add(province)
        for index, value in enumerate(values[1:]):
            unit = units[index]
            numeric = float(value.replace(',', ''))
            if unit != 'ไร่':
                assert numeric.is_integer()
                numeric = int(numeric)
            status = groups[index // 3]
            all_rows.append({
                'source_id': source_id, 'province_code': TARGETS[province],
                'province_name': province, 'district_name': None,
                'crop': crop, 'certification_scope': scope,
                'year_be': 2569, 'year_ce': 2026, 'as_of_date': '2026-10-20',
                'year_basis': 'snapshot_as_of_source_displayed_date',
                'metric': {'ราย': 'certified_farmers', 'แปลง': 'certified_plots', 'ไร่': 'certified_area_rai'}[unit],
                'source_status': status, 'value': numeric, 'unit': unit,
                'source_value': value, 'source_url': url,
                'source_anchor': f'HTML table 1 row {row_number}; จังหวัด={province}; สถานะ={status}; หน่วย={unit}',
                'verification': 'Original public HTML complete; 9 status groups x 3 units; source numbers copied without inference',
                'limitations': 'ข้อมูลสรุปในระบบตามวันแสดงบนเว็บ; ไม่ได้ตรวจเอกสารรายแปลงซ้ำ; สถานะอาจเปลี่ยน; ไม่ใช่ผลผลิตหรือยอดส่งออก',
            })
    assert found == set(TARGETS), (source_id, found)
    manifests.append({
        'source_id': source_id, 'source_url': url, 'file_name': filename,
        'title': 'GAP DOA Online - ' + crop + ' - ผลการดำเนินงานแยกจังหวัด',
        'agency': 'กรมวิชาการเกษตร', 'as_of_date': '2026-10-20',
        'retrieved_date': '2026-10-20', 'crop_scope': scope,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
        'html_complete': True, 'target_provinces_found': len(found),
        'status_columns': groups, 'observations': 135,
        'license': 'ไม่ระบุในหน้ารายงาน',
    })

(BASE / 'live_dashboard_rows.json').write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding='utf-8')
(BASE / 'live_dashboard_manifest.json').write_text(json.dumps(manifests, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps([r for r in all_rows if r['source_id'] == 'NATLIVE_DURIAN' and r['source_status'] == 'ได้รับการรับรองที่ยังไม่หมดอายุ'], ensure_ascii=False, indent=2))
