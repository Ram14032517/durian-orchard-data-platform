"""Reuse sealed provincial inputs; re-label exact OAE directions. Offline only."""
import datetime, hashlib, importlib.metadata, json, platform, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('C:/project'); OUT=Path(__file__).resolve().parent
PREV=ROOT/'research_data/internal_research/optimized_classification/optimized_20261012_v1'
OLD=ROOT/'research_data/internal_research/integrated_ndvi_vpd/integrated_20261012_v1'
P9=ROOT/'research_data/internal_research/four_provinces/phase9d_20261012_v1'
AUTO=ROOT/'research_data/internal_research/automl/automl_20261012_v1'
PRODUCTION=ROOT/'research_data/five_province_history/training/ridge_vpd_final_model.json'
NAMES={22:'จันทบุรี',33:'ศรีสะเกษ',53:'อุตรดิตถ์',86:'ชุมพร'}
H=['province_code','year_offset','yield_lag2','last_known_pct_change','yield_trend_2yr_pct']
W=['nasa_temp_annual','nasa_rain_annual','nasa_rh_annual','nasa_temp_ond','nasa_rain_ond','nasa_rh_ond','nasa_monthly_temp_std','nasa_dry_months','nasa_rain_concentration','era_daily_temp_std','temp_anomaly','rain_anomaly_pct','rh_anomaly']
V=['vpd_mean','vpd_p95','vpd_high_fraction','vpd_max_duration','vpd_ond_mean','vpd_dry_fraction','vpd_night_mean','vpd_anomaly']
N=['ndvi_median','ndvi_std','ndvi_monthly_slope','ndvi_anomaly']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def js(p,v):
 def clean(x):
  if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
  if isinstance(x,(tuple,list)): return [clean(v) for v in x]
  if isinstance(x,(float,np.floating)) and not np.isfinite(x): return None
  if isinstance(x,np.integer): return int(x)
  if isinstance(x,np.bool_): return bool(x)
  return x
 payload=json.dumps(clean(v),ensure_ascii=False,indent=2,allow_nan=False,default=str)
 with p.open('x',encoding='utf-8') as f: f.write(payload)
def csv(p,d):
 assert not p.exists(),f'Refuse overwrite: {p}'
 d.to_csv(p,index=False,encoding='utf-8-sig')
def label(current,previous):
 if not np.isfinite(current) or not np.isfinite(previous): return None
 return 1 if current>previous else 0 if current<previous else None
def direction(value,fallback): return 1 if value>0 else 0 if value<0 else int(fallback)
def verify_seals():
 protected=read(OLD/'acquisition_config.json')['protected_hashes']
 assert all(sha(ROOT/p)==h for p,h in protected.items()),'Protected source changed'
 counts={}
 for folder in [P9,AUTO,OLD,PREV]:
  files=read(folder/'output_manifest.json')['files']
  assert all(sha(folder/p)==h for p,h in files.items()),f'Sealed release changed: {folder}'
  counts[str(folder.relative_to(ROOT))]=len(files)
 assert sha(PRODUCTION)=='b4b9e0985e6ba5e6ee371d8988cad5e65dee031b345eb0cf13a8695f91658680'
 return protected,counts
def main():
 assert not (OUT/'preflight.json').exists()
 protected,seals=verify_seals()
 status=subprocess.check_output(['git','status','--porcelain=v1','-uall'],cwd=ROOT,text=True,encoding='utf-8')
 js(OUT/'repository_state_before.json',{'status':status,'note':'Existing changes preserved; hash-only snapshot, no secrets copied'})
 paths=[P9/'province_year.csv',P9/'source_manifest.json',PREV/'unified_features.csv',PREV/'unified_feature_dictionary.csv',PREV/'hourly_feature_lineage.csv',PREV/'hourly_source_audit.json',PREV/'ndvi_sensor_features.csv',PREV/'soil_gis_context.csv',PREV/'source_manifest.json',PREV/'preflight.json',PREV/'final_verification.json',PREV/'conclusion.json',PREV/'model_comparison.csv',PREV/'predictions_vs_actual.csv',PREV/'inner_model_comparison.csv',PREV/'protocol_frozen.json',PREV/'fit_cache_audit.json',PREV/'output_manifest.json',OLD/'results/model_comparison.csv',OLD/'results/model_predictions.csv',AUTO/'results/conclusion.json',AUTO/'results/model_evaluation.csv',ROOT/'research_data/external/oae_2026-09-17/durian_province.xlsx']
 # The preceding manifest supplies the raw weather/NDVI chain without redownloading.
 hashes={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in paths if p.exists()}
 hashes.update(read(PREV/'source_manifest.json')['files'])
 js(OUT/'source_manifest.json',{'files':hashes,'sealed_release_counts':seals,'upstream_release_manifest_sha256':sha(PREV/'output_manifest.json'),'new_downloads':False,'external_uploads':False,'public_release':'HOLD','historical_publication_vintage':'unverified'})
 p=pd.read_csv(P9/'province_year.csv').sort_values(['province_code','year_ce'])
 assert len(p)==80 and p.yield_kg_per_rai.notna().all() and not p.duplicated(['province_code','year_ce']).any()
 p['yield_previous_year']=p.groupby('province_code').yield_kg_per_rai.shift()
 p['label']=[label(y,l) for y,l in zip(p.yield_kg_per_rai,p.yield_previous_year)]
 p['status']=np.where(p.yield_previous_year.isna(),'no_previous_year',np.where(p.label.isna(),'exact_equal_excluded','binary_label_available'))
 csv(OUT/'all_OAE_direction_labels.csv',p[['province_code','province_name','year_ce','oae_observation_id','yield_kg_per_rai','yield_previous_year','label','status']])
 equal=p[p.status=='exact_equal_excluded'];csv(OUT/'exact_equal_excluded.csv',equal[['province_code','province_name','year_ce','yield_kg_per_rai','yield_previous_year','status']])
 lookup=p.set_index(['province_code','year_ce'])
 df=pd.read_csv(PREV/'unified_features.csv'); assert len(df)==64
 actual=[]
 for r in df.itertuples():
  s=lookup.loc[(r.province_code,r.year_ce)]
  assert r.yield_kg_per_rai==s.yield_kg_per_rai and r.yield_previous_year_label_only==s.yield_previous_year
  assert r.yield_lag2==lookup.loc[(r.province_code,r.year_ce-2)].yield_kg_per_rai
  assert r.yield_lag3==lookup.loc[(r.province_code,r.year_ce-3)].yield_kg_per_rai
  assert r.yield_lag4==lookup.loc[(r.province_code,r.year_ce-4)].yield_kg_per_rai
  assert abs(getattr(r,'pct_change')-100*(s.yield_kg_per_rai/s.yield_previous_year-1))<1e-10
  actual.append(s.label)
 df['label']=actual; df=df[df.label.notna()].copy();df['label']=df.label.astype(int)
 csv(OUT/'unified_features.csv',df)
 dictionary=pd.read_csv(PREV/'unified_feature_dictionary.csv')
 dictionary.loc[dictionary.field=='label',['unit','calculation']]=['binary category','1 if reported OAE Yield(Y)>Yield(Y-1); 0 if less; exact equals excluded']
 dictionary.loc[dictionary.field=='label','note']='Target only; recomputed from OAE, not converted from old three-class labels'
 for f in ['weather_year','province_name','max_observation_date','availability_status']:
  dictionary.loc[dictionary.field==f,'source']='input lineage metadata'
 csv(OUT/'unified_feature_dictionary.csv',dictionary)
 csv(OUT/'class_distribution.csv',df.groupby(['province_code','province_name','label']).size().rename('n').reset_index())
 csv(OUT/'missingness.csv',pd.DataFrame([{'field':c,'missing_rows':int(df[c].isna().sum()),'total_rows':len(df)} for c in df]))
 # Prior results are read for limitations, never used as new binary rankings.
 prior_counts={}
 for folder,names in [(PREV,['model_comparison.csv','predictions_vs_actual.csv','inner_model_comparison.csv']),(OLD/'results',['model_comparison.csv','model_predictions.csv'])]:
  for name in names:
   d=pd.read_csv(folder/name);prior_counts[str((folder/name).relative_to(ROOT))]={'rows':len(d),'columns':list(d.columns)}
 js(OUT/'prior_results_review.json',{'tables_reviewed':prior_counts,'previous_three_class':read(PREV/'conclusion.json'),'previous_regression':read(AUTO/'results/conclusion.json'),'use':'Protocol/source/error limitations only; no old test score selects binary family/features'})
 js(OUT/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scikit-learn','xgboost','lightgbm','catboost']},'new_installations':False})
 js(OUT/'preflight.json',{'protected_hashes':protected,'protected_count':len(protected),'seals':seals,'production_sha256':sha(PRODUCTION),'source_rows':80,'paired_label_rows':int(p.label.notna().sum()),'equal_rows':len(equal),'model_rows':len(df),'issue_date_rule':'March 1 target CE year; exploratory calendar, not recorded historical issue','label_availability_policy':'Y-2 or earlier, conservative year gap but no verified publication vintage','observation_end':'December31 Y-1','soil_gis':'context only; historical fixed footprint is not verified','start_utc':'2026-10-12T14:41:43Z','task_deadline_utc':'2026-10-12T16:11:43Z','new_year_forecast':False,'public_release':'HOLD'})
 print(f'Preflight: {len(df)} modeling rows; OAE paired labels {p.label.notna().sum()}; exact equals {len(equal)}; protected {len(protected)} unchanged',flush=True)
if __name__=='__main__': main()
