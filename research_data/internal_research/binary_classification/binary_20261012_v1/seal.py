"""Seal final binary outputs only after numeric and rendered-page review."""
import datetime
from pathlib import Path
from prepare import OUT,read,sha,js,verify_seals,PRODUCTION
def main():
 assert not (OUT/'output_manifest.json').exists()
 check=read(OUT/'final_verification.json');qa=read(OUT/'pdf_qa/text_page_verification.json')
 assert check['passed']==21 and qa['pages']==10 and qa['rounded_metrics_verified']
 assert read(OUT/'training_completion.json')['training_code_unchanged']
 protected,seals=verify_seals()
 js(OUT/'delivery_qc.json',{'numeric_checks_passed':21,'pretraining_tests_passed':14,'visual_review':'All10 rendered pages inspected via contact sheets; dense results page reviewed at full size; no clipping or unreadable fonts','pdf_pages':10,'model_retraining_after_scores':False,'protected_count':len(protected),'production_sha256':sha(PRODUCTION),'public_release':'HOLD','historical_pit':'not_certified','downloads_in_this_run':0,'external_uploads':0,'forecast_2026_issued':False,'source_files_changed':False,'report_draft1':'Prior presentation draft retained, not a separate experiment'})
 files={str(p.relative_to(OUT)).replace('\\','/'):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and 'report_draft1' not in p.parts}
 js(OUT/'output_manifest.json',{'run_id':OUT.name,'files':files,'sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_release':'HOLD','prior_sealed_release_counts':seals,'production_sha256':sha(PRODUCTION),'model_scope':'real provincial OAE binary direction only'})
 assert all(sha(OUT/p)==h for p,h in files.items())
 print('Sealed',len(files),'files; Production and prior sources unchanged; Public HOLD')
if __name__=='__main__':main()
