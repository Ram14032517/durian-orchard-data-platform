"""Hash/PDF checks for Phase11F documents, no network or dataset changes."""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'research_data/internal_research/chanthaburi_district_yield'
OLD=BASE/'phase11e_20261012_v1'
OUT=BASE/'phase11f_20261012_v1'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def read(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path,obj):
    with path.open('x',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,indent=2)


def seal():
    if (OUT/'output_manifest.json').exists(): raise FileExistsError('Refuse overwrite')
    protected=read(OLD/'preflight_protected_hashes.json')
    protected.update({str((OLD/k).relative_to(ROOT)):v for k,v in read(OLD/'output_manifest.json')['files'].items()})
    protected[str((OLD/'output_manifest.json').relative_to(ROOT))]=sha(OLD/'output_manifest.json')
    mismatches=[k for k,v in protected.items() if not (ROOT/k).is_file() or sha(ROOT/k)!=v]
    assert not mismatches,mismatches
    sources=[]
    for path in sorted((OUT/'sources').glob('*.pdf')):
        body=path.read_bytes(); assert body.startswith(b'%PDF-') and b'%%EOF' in body[-1024:]
        pdf=PdfReader(path,strict=True); assert not pdf.is_encrypted
        part=path.stem[-2:]
        sources.append(dict(file=path.name,sha256=sha(path),pages=len(pdf.pages),
            url=f'https://eresearch.rbru.ac.th/pdf-uploads/thesis-1803-file{part}-2020-09-29-10-50-59.pdf',
            transport='Invoke-WebRequest default TLS; HTTP200 application/pdf; final URL same domain observed',
            publication_date=None))
    assert {p['file'][-6:-4] for p in sources}=={'02','03','04','05','06','10','11'}
    for name in ['RESEARCHER_EMAIL_DRAFT_TH.md','OAE6_EMAIL_DRAFT_TH.md']:
        text=(OUT/name).read_text(encoding='utf-8')
        assert all(term in text for term in ['2557','2567','Production','Bearing','Standing','Yield','District Code','Crop Year',
                                            'Actual','Preliminary','Forecast','Revised','เผยแพร่','รุ่นข้อมูล','อ้างอิง'])
        assert 'ยังไม่ได้ส่ง' in text
    reused=['rbru2018_methods.pdf','rbru2018_results.pdf','promproh2026_full.pdf']
    model=ROOT/'research_data/five_province_history/training/ridge_vpd_final_model.json'
    assert sha(model)=='b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680'
    save(OUT/'source_manifest.json',dict(registration_time_utc=datetime.now(timezone.utc).isoformat(),new_sources=sources,
        reused_sources={name:sha(OLD/'sources'/name) for name in reused},
        repository={'url':'https://eresearch.rbru.ac.th/showthesis.php?depid=2&theid=1803',
                    'local_sha256':sha(OUT/'sources/rbru_repository.html')},
        code_sha256=sha(Path(__file__)),protected_files=len(protected),protected_hash_mismatches=mismatches,
        production_sha256=sha(model),candidate_new_district_rows=0,verified_new_district_rows=0,
        public_release='HOLD',emails_sent=0,notebooklm_uploads=0,repo_wide_tests_run=False))
    files={str(p.relative_to(OUT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()}
    digest=hashlib.sha256(json.dumps(files,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    save(OUT/'output_manifest.json',dict(files=files,manifest_payload_sha256=digest,public_release='HOLD'))
    assert all(sha(OUT/k)==v for k,v in files.items())
    print('PASS',len(protected),'protected files; PDFs/requests/output hashes; no emails/uploads/dataset changes')


if __name__=='__main__': seal()
