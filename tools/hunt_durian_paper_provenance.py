"""Bounded Phase11E public-document retrieval, no authentication/uploads/ML/GIS."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'research_data/internal_research/chanthaburi_district_yield/phase11e_20261012_v1'
HOSTS={'li01.tci-thaijo.org','ph02.tci-thaijo.org','eresearch.rbru.ac.th','www.beei.org'}


def save(path,obj):
    with path.open('x',encoding='utf-8') as f: json.dump(obj,f,ensure_ascii=False,indent=2)


def fetch(name,url):
    if urlparse(url).hostname not in HOSTS: raise ValueError('Unapproved retrieval host')
    class CheckedRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,req,fp,code,msg,headers,newurl):
            if urlparse(newurl).hostname not in HOSTS: raise ValueError('Redirect outside allowed public sources')
            return super().redirect_request(req,fp,code,msg,headers,newurl)
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research provenance audit)'})
    with urllib.request.build_opener(CheckedRedirect).open(req,timeout=35) as response:
        content=response.read(20_000_001)
        if len(content)>20_000_000: raise ValueError('Document exceeds bounded download')
        meta={'source_url':url,'response_url':response.url,'content_type':response.headers.get('Content-Type'),
            'http_status':response.status,'access_time_utc':datetime.now(timezone.utc).isoformat(),
            'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),
            'http_last_modified':response.headers.get('Last-Modified'),
            'publication_date_note':'HTTP/retrieval timestamps do not prove publication of underlying data'}
    folder=OUT/'sources'; folder.mkdir(parents=True,exist_ok=True)
    is_pdf=content.startswith(b'%PDF-')
    path=folder/(name+('.pdf' if is_pdf else '.html'))
    with path.open('xb') as f: f.write(content)
    if is_pdf:
        reader=PdfReader(path,strict=True)
        if reader.is_encrypted: raise ValueError('Encrypted PDF')
        meta['pages']=len(reader.pages)
        save(folder/(name+'.pages.json'),[{'physical_page_1based':i,'text':page.extract_text()} for i,page in enumerate(reader.pages,1)])
    else:
        html=content.decode('utf-8',errors='replace')
        meta['candidate_pdf_urls']=re.findall(r'<meta[^>]*name=["\']citation_pdf_url["\'][^>]*content=["\']([^"\']+)',html,re.I)
    save(folder/(name+'.source.json'),meta)
    print(json.dumps(meta,ensure_ascii=False))


def register_local(name,url):
    """Register a TLS-verified PowerShell download; do not assert unrecorded HTTP headers."""
    if urlparse(url).hostname not in HOSTS: raise ValueError('Unapproved retrieval host')
    path=OUT/'sources'/(name+'.pdf'); body=path.read_bytes()
    if not body.startswith(b'%PDF-'): raise ValueError('Not a PDF')
    reader=PdfReader(path,strict=True)
    save(path.with_suffix('.pages.json'),[{'physical_page_1based':i,'text':page.extract_text()} for i,page in enumerate(reader.pages,1)])
    save(path.with_suffix('.source.json'),{'source_url':url,'sha256':hashlib.sha256(body).hexdigest(),
        'bytes':len(body),'pages':len(reader.pages),'registration_time_utc':datetime.now(timezone.utc).isoformat(),
        'transport':'PowerShell Invoke-WebRequest default TLS validation; response URL checked separately',
        'publication_date':None,'retrieval_note':'registration time is not data publication time'})
    print(name,len(reader.pages),'pages',hashlib.sha256(body).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('name'); parser.add_argument('url'); parser.add_argument('--register-local',action='store_true'); args=parser.parse_args()
    (register_local if args.register_local else fetch)(args.name,args.url)
