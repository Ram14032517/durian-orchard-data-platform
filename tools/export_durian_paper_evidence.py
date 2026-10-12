"""Offline evidence register, not a district-yield importer."""
import csv
import json
from pathlib import Path
import re
from tools.hunt_durian_paper_provenance import OUT,ROOT,save
from tools import audit_chanthaburi_historical_district_yield as a

STATUS={'verified_official_district_year_data','published_table_needs_verification','data_source_lead_only','province_level_only','no_usable_yield_data'}


def write_csv(name,rows,fields):
    with (OUT/name).open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def require_verified(row):
    if row['status']=='verified_official_district_year_data':
        if not all(row.get(k) for k in ('district_code','year_ce','unit','official_origin_evidence','source_sha256','anchor')):
            raise ValueError('Cannot certify missing district/year/unit/official origin/lineage')
    return True


def export():
    if (OUT/'source_manifest.json').exists(): raise FileExistsError('Refuse overwrite')
    entries=[]
    def add(sid,title,status,local,years,grain,anchor,finding,contact,review='full_text_read'):
        meta=json.loads((OUT/'sources'/f'{local}.source.json').read_text(encoding='utf-8')) if local else a.read(a.OLD/'source_manifest.json')
        entries.append(dict(source_id=sid,title=title,status=status,url=meta.get('source_url',meta.get('approved_url')),
            local_file=str((OUT/'sources'/f'{local}.pdf').relative_to(ROOT)) if local else str((a.OLD/'source.pdf').relative_to(ROOT)),
            source_sha256=meta['sha256'],access_date='2026-10-12',reported_years=years,
            spatial_level=grain,anchor=anchor,finding=finding,contact_lead=contact,review_scope=review,
            verified_new_district_year_rows=0,finality='unverified',public_release='HOLD'))
    add('P2026','Promproh et al. 2026 Integrated Analysis','data_source_lead_only','promproh2026_full','claimed 2014–2024; 10-year wording inconsistent with inclusive 11 years','district claim vs provincial results',
        'PDF pp2 §2.1; p4; p6 Table3/conclusion; p7 acknowledgments',
        'OAE6 named; no district-year raw table or linked data repository; conclusion says provincial analysis; paper dates do not prove data vintage',
        'kasidid_pr@rmutto.ac.th; OAE6')
    add('P2026_T3','Promproh 2026 Table3','province_level_only','promproh2026_full','2021–2024','province',
        'PDF p6 Table3','Four province-year metrics only; no district allocations permitted; 2023/2024 values partly differ from Phase11B','OAE6')
    add('P2025','Promproh et al. 2025 Geoinformatics-Based Spatial Evaluation','data_source_lead_only','promproh2025_full','yield explicitly 2023–2024; imagery 2022–2025','10 districts claimed',
        'PDF p4 printed360 §2.2; p11 printed367 acknowledgments','Provincial Agricultural Office supplies source; imagery years must not be substituted for yield years','wachirathorn_ja@rmutto.ac.th; Provincial Agricultural Office')
    add('P2025_T2','Promproh 2025 Table2','published_table_needs_verification','promproh2025_full','yield year unspecified; NDVI column says 2024','district summary',
        'PDF p10 printed366 Table2 rows1–10; p8 printed364 denominator statement',
        'Ten Yield/rai values in tons; no Production/Bearing columns or explicit yield year; text uses standing area denominator; not verified actual district-year observations','wachirathorn_ja@rmutto.ac.th')
    add('C2025','Thongnim Srinil Phukseng 2025 Data-driven clustering','data_source_lead_only','clustering2025_full','claimed 2012–2023','district source claimed; province/group summaries',
        'PDF p2 §2.1; pp8–9 Tables1–3; p10 acknowledgments',
        'Chanthaburi Data Center vague in methods; acknowledges OAE6 and BUU Data Center; tables show scores/cluster statistics/membership not raw yield; unit and preprocessing clarification needed','thanaph@buu.ac.th; OAE6')
    add('R2018_M','RBRU 2018 Durian Quantity report Chapter3','province_level_only','rbru2018_methods','retrospective decade; Chapter1 web text says 2550–2560','province',
        'chapter3 PDF p1 printed20','Annual secondary data from Provincial Agricultural Office; no district-year table in inspected methods/results','RBRU authors via university repository','Chapter3 and Chapter4 read; full report appendices not verified')
    add('R2018_R','RBRU 2018 Durian Quantity report Chapter4','province_level_only','rbru2018_results','2550–2560 stated; forecast2561','province',
        'chapter4 PDF pp1–9 printed22–30','Regression/correlation coefficients and graphs; no inspectable district-year raw rows','RBRU repository','Chapter4 read; no inference about unseen appendices')
    add('DOAE11B','DOAE source reused from Phase11B','verified_official_district_year_data',None,'2566–2567','10 districts',
        'PDF p5 Table2','20 previously verified transcription rows, NOT new data or certified Final Actual; status means official-hosted transcription only','OAE6','Phase11B sealed source reused; no new download')
    # Existing verification carries real keys, not a claim that the entire publication is PIT-certified.
    for r in entries:
        if r['status'] not in STATUS: raise ValueError('Unexpected evidence status')
    write_csv('research_paper_evidence_register.csv',entries,list(entries[0]))
    write_csv('verified_new_district_year_coverage.csv',[dict(year_be=y,year_ce=y-543,
        verified_new_rows=0,verified_new_districts=0,complete_10_districts=False,
        status='no_new_verified_district_year_data',missing_district_codes='2201;2202;2203;2204;2205;2206;2207;2208;2209;2210') for y in range(2557,2566)],
        ['year_be','year_ce','verified_new_rows','verified_new_districts','complete_10_districts','status','missing_district_codes'])
    supplementary=[]
    for name,sid in [('promproh2026','P2026'),('promproh2025','P2025')]:
        html=(OUT/'sources'/f'{name}.html').read_text(encoding='utf-8')
        links=re.findall(r'href=["\']([^"\']+)',html)
        data_links=[link for link in links if any(k in link.lower() for k in ['supplement','zenodo','figshare','osf.io','dataverse'])]
        supplementary.append(dict(source_id=sid,public_linked_raw_dataset_count=len(data_links),
            raw_dataset_urls=';'.join(data_links),scope='downloaded landing page plus entire main PDF inspected',
            status='no_linked_raw_dataset_detected_in_inspected_material',note='not proof authors lack files; citation exports and PDF galley are not raw datasets'))
    for sid,scope in [('C2025','entire 12-page publisher PDF'),('R2018','downloaded Chapters3/4; indexed cover/introduction; repository detail fetch failed')]:
        supplementary.append(dict(source_id=sid,public_linked_raw_dataset_count=0,raw_dataset_urls='',scope=scope,
            status='not_found_in_inspected_material',note='no raw data file downloaded; uninspected appendices remain a gap'))
    write_csv('supplementary_data_inventory.csv',supplementary,list(supplementary[0]))
    # Preserve printed values with null yield-year; they must never be exported as verified district-year targets.
    table=[('2201','เมืองจันทบุรี',3.50),('2205','มะขาม',3.20),('2203','ท่าใหม่',3.45),('2210','เขาคิชฌกูฏ',2.90),
           ('2204','โป่งน้ำร้อน',3.00),('2206','แหลมสิงห์',3.60),('2209','นายายอาม',3.25),('2202','ขลุง',3.35),
           ('2207','สอยดาว',2.60),('2208','แก่งหางแมว',2.70)]
    candidate=[dict(district_code=c,district_name=n,year_ce=None,printed_yield_tons_per_rai=v,
        source_id='P2025_T2',source_sha256=entries[3]['source_sha256'],pdf_page_1based=10,
        table_number=2,table_row_1based=i,unit='tons/rai',denominator_status='standing_vs_bearing_unresolved',
        status='published_table_needs_verification') for i,(c,n,v) in enumerate(table,1)]
    save(OUT/'published_unverified_table2.json',candidate)
    comparisons=[]
    old=a.read(a.OLD/'district_year.json')['rows']
    for r in candidate:
        for y in (2023,2024):
            reference=next(x for x in old if x['district_code']==r['district_code'] and x['year_ce']==y)
            comparisons.append(dict(district_code=r['district_code'],candidate_year=None,reference_year_ce=y,
                printed_value_tonnes_per_rai=r['printed_yield_tons_per_rai'],
                unit_conversion_only_kg_per_rai=r['printed_yield_tons_per_rai']*1000,
                phase11b_reported_kg_per_rai=reference['reported_yield_kg_rai'],
                compatible_value=abs(r['printed_yield_tons_per_rai']*1000-reference['reported_yield_kg_rai'])<.5,
                use='compatibility_screen_only_not_year_assignment_or_dataset_join'))
    save(OUT/'phase11b_compatibility_screen.json',comparisons)
    sources={f.name:json.loads(f.read_text(encoding='utf-8')) for f in sorted((OUT/'sources').glob('*.source.json'))}
    before=json.loads((OUT/'preflight_protected_hashes.json').read_text(encoding='utf-8'))
    assert all(a.p.sha(ROOT/k)==v for k,v in before.items())
    save(OUT/'source_manifest.json',dict(sources=sources,existing_source=a.read(a.OLD/'source_manifest.json'),
        code_sha256={p.name:a.p.sha(p) for p in [Path(__file__),ROOT/'tools/hunt_durian_paper_provenance.py']},
        downloaded_raw_district_yield_datasets=0,downloaded_pdf_files=5,
        notebooklm={'connector_search_result':[],'available_connected_tools':False,
          'official_api':'https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks',
          'user_enterprise_project_iam_license_authorization':'not_verified','connection_attempted':False,'uploaded_sources':0,
          'approval_needed_before_public_PDF_import':True},
        protected_files_checked=len(before),protected_hash_mismatches=[],production_sha256=a.p.sha(ROOT/a.p.previous.MODEL),
        public_release='HOLD',historical_pit='not_certified'))
    print('Evidence rows',len(entries),'candidate rows',len(candidate),'new verified years/rows 0/0; PDFs 5; raw datasets 0')


if __name__=='__main__': export()
