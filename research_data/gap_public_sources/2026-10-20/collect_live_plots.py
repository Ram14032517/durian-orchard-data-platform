"""Read only the public GAP search form and its observed Excel export links.

No authentication, CAPTCHA, opaque-query construction or identity search.
Large incomplete province responses are replaced by ordinary district filters.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlencode
import hashlib
import json
import re
import subprocess

BASE = Path(__file__).resolve().parent
OUT = BASE / "collection_live_plots"
OLD = BASE / "collection_north_northeast"
HOST = "https://gap.doa.go.th/"
PROVINCES = {"22":"จันทบุรี", "86":"ชุมพร", "84":"สุราษฎร์ธานี", "33":"ศรีสะเกษ", "53":"อุตรดิตถ์"}

def fetch(url, data=None):
    command=["curl","-fsS","--connect-timeout","15","--max-time","125"]
    if data is not None: command += ["--data",urlencode(data)]
    command.append(url)
    return subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.rows=[]; self.row=[]; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(v for k,v in attrs if k=="href" and "action=10" in v and "{querycondition}" not in v)
        if tag == "tr": self.row=[]
        if tag in ("td", "th"): self.cell=[]
    def handle_data(self, data):
        if self.cell is not None: self.cell.append(data)
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split())); self.cell=None
        if tag=="tr" and self.row: self.rows.append(self.row)

def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")

def collect(job):
    prov,crop,name,amphur,amphur_name=job
    key=f"{prov}_{crop}_{amphur}"
    cached=OUT/f"queries/{key}.json"
    if cached.exists():
        previous=json.loads(cached.read_text())
        if previous.get("complete"): return previous
    record=dict(source_id=f"DOA_PLOT_{key}",province_code=prov,province_name=PROVINCES[prov],
                crop_query_id=crop,crop_query_name=name,district_filter_id=amphur,
                district_filter_name=amphur_name,retrieved_utc=datetime.now(timezone.utc).isoformat(),
                query=dict(action=0,searchaction=1,plantex=crop,province=prov,amphur=amphur,tambol=0),
                source_url=HOST+"searchgap",complete=False)
    try:
        response=fetch(HOST+"searchgap",data=record["query"])
        path=OUT/f"raw/search_{key}.html"; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(response)
        record.update(search_file=str(path.relative_to(BASE)),search_sha256=hashlib.sha256(response).hexdigest())
        page=Page();page.feed(response.decode("utf-8"))
        if not page.links:
            # No export link is not treated as a verified zero count.
            record.update(error="No concrete public export link; no zero count inferred")
        else:
            record["source_url"]=urljoin(HOST+"searchgap",page.links[0])
            export=fetch(record["source_url"])
            path=OUT/f"raw/export_{key}.xls";path.write_bytes(export)
            table=Page();table.feed(export.decode("utf-8"))
            record.update(source_file=str(path.relative_to(BASE)),sha256=hashlib.sha256(export).hexdigest(),
                          bytes=len(export),complete="</html>" in export.decode("utf-8").lower(),
                          completed_data_rows=max(0,len(table.rows)-1),format="HTML_table_with_xls_extension")
    except Exception as exc:
        record["error"]=str(exc)
    save(cached,record)
    return record

def main():
    form=(OLD/"live_search_form.html").read_text()
    crops=[(code,name) for code,name in re.findall(r'<option value="(\d+)">([^<]*ทุเรียน[^<]*)</option>',form)
           if code!="146"] # Annona muricata / soursop is not Durio.
    save(OUT/"crop_queries.json",[dict(id=c,name=n) for c,n in crops])
    jobs=[]
    # Complete primary cultivar exports already obtained are reused locally.
    # Only four original responses lack closing HTML. Query each district instead.
    for prov,crop in [("22","145"),("22","614"),("86","614"),("84","614")]:
        api=HOST+f"api_amphurlistbyprovince?d=0&p={prov}"
        path=OUT/f"raw/districts_{prov}.json"
        if path.exists(): data=json.loads(path.read_text())
        else:
            data=json.loads(fetch(api));save(path,data)
        for row in data["results"]:
            jobs.append((prov,crop,dict(crops)[crop],str(row["AmphurID"]),row["AmphurName"]))
    for prov in PROVINCES:
        for crop,name in crops:
            if crop in ("145","614") or (prov=="53" and crop=="856"): continue
            jobs.append((prov,crop,name,"0",None))
    print(json.dumps(dict(queries=len(jobs),durian_categories=len(crops))),flush=True)
    results=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(collect,j):j for j in jobs}
        for f in as_completed(futures):
            results.append(f.result())
            if len(results)%10==0:
                print(json.dumps(dict(done=len(results),complete=sum(bool(r.get("complete")) for r in results),rows=sum(r.get("completed_data_rows",0) for r in results))),flush=True)
    save(OUT/"query_manifest.json",results)
    print(json.dumps(dict(done=len(results),complete=sum(bool(r.get("complete")) for r in results),rows=sum(r.get("completed_data_rows",0) for r in results))),flush=True)

if __name__=="__main__": main()
