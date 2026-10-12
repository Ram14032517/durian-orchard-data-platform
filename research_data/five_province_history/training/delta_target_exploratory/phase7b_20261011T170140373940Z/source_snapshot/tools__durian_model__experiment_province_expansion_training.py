"""Frozen Phase 6B 2x2 exploratory experiment; training requires --train."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
import experiment_province_expansion as pe
import experiment_weather_ablation as wa
from audit_province_expansion_inputs import check_hashes
from experiment_enso_training import protected_hashes, unchanged

rb = pe.rb
KEYS = wa.KEYS
INPUT = pe.ROOT / 'phase6a_20261011T134340704642Z'
REFERENCE = wa.OUTPUT_ROOT / '20261011T122324056845Z'
OUTPUT = rb.OUT / 'province_expansion_exploratory'
ARMS = {'A': ('5', False), 'B': ('5', True), 'C': ('10', False), 'D': ('10', True)}


def protocol():
    return dict(mode='exploratory', cohorts=pe.COHORTS, anchors=pe.ANCHORS,
        lead=60, outer=list(rb.OUTER_YEARS), inner=3, training_start=2010,
        selection_cohort=rb.PROVINCES, arms={a:list(v) for a,v in ARMS.items()}, enso=False, depths=[2,3],
        seed=42, iterations=400, learning_rate=.03, l2_leaf_reg=10,
        loss_function='RMSE', boosting_type='Ordered', thread_count=1,
        allow_writing_files=False, encoding='locked cohort indicators, year, ordered features',
        features=rb.FEATURES, shared_cutoff='min provincial issue midnight +07:00',
        ties='depth 2 first', cache='arm/cohort/fold/candidate/cutoff/source/code/data; no outer targets')


def candidate(arm, depth):
    if arm not in ARMS or depth not in (2,3):
        raise ValueError('Unexpected arm/grid')
    return dict(group=arm, kind='catboost', parameter=dict(depth=depth,l2_leaf_reg=10,learning_rate=.03),
        features=list(rb.FEATURES) if ARMS[arm][1] else [wa.LAG])


def project(frame, arm):
    c = candidate(arm,2)
    provinces = pe.COHORTS[ARMS[arm][0]]
    if not set(frame.province_code).issubset(provinces) or frame.duplicated(KEYS).any():
        raise ValueError('Wrong cohort or duplicate model rows')
    result = frame[KEYS+c['features']].copy()
    matrix = wa.design(result,provinces,c['features'])
    if matrix.shape[1] != len(provinces)+1+len(c['features']) or not np.isfinite(matrix).all():
        raise ValueError('Invalid design/encoding')
    if not np.equal(matrix[:,:len(provinces)].sum(axis=1),1).all():
        raise ValueError('Unknown province encoding')
    return result


def load_inputs():
    read = lambda name: json.loads((INPUT/name).read_text(encoding='utf-8'))
    check_hashes(INPUT,read('completed_artifact_hashes.json'))
    config, manifest = read('config.json'), read('manifest.json')
    check_hashes(rb.ROOT,config['code_sha256'])
    check_hashes(rb.ROOT,config['source_sha256'])
    if (manifest['schedule']['anchors'] != pe.ANCHORS or manifest['enso']
            or manifest['selection_cohort'] != rb.PROVINCES
            or config['protocol_hash'] != rb.digest_value(manifest)):
        raise ValueError('Phase 6A protocol mismatch')
    for arm, (size, weather) in ARMS.items():
        if manifest['arms'][arm] != dict(cohort=size,features=rb.FEATURES if weather else [wa.LAG]):
            raise ValueError('Arm features/cohort changed')
    expected_grid = dict(depths=[2,3],seed=42,iterations=400,learning_rate=.03,l2_leaf_reg=10,
        loss_function='RMSE',boosting_type='Ordered',thread_count=1,allow_writing_files=False)
    if manifest['grid'] != expected_grid:
        raise ValueError('Grid changed')
    for record in manifest['records'].values():
        if 'path' in record:
            check_hashes(rb.ROOT,{record['path']:record['source_version']})
    inputs = pd.read_csv(INPUT/'predictors.csv',dtype={'province_code':str},float_precision='round_trip')
    annual = pd.read_csv(INPUT/'annual.csv',dtype={'province_code':str},float_precision='round_trip')
    pe.check_annual(annual)
    wa.require_rows(inputs,KEYS+rb.FEATURES,{(p,y) for p in pe.COHORTS['10'] for y in rb.YEARS})
    lineage=read('feature_lineage.json')
    lookup=annual.set_index(KEYS)[rb.TARGET]
    for trace in lineage:
        if trace['feature']==wa.LAG:
            p,y=trace['province_code'],trace['year_ce']
            if trace['value']!=float(lookup.loc[p,y-1]) or trace['source_value_sha256']!=rb.digest_value([p,y-1,trace['value']]):
                raise ValueError('Lag lineage differs from annual source')
    # Reuses the actual-consumption and label guards without changing Phase 6A.
    folds,checks=pe.prepare_folds(inputs,annual,lineage,manifest)
    if folds != read('folds.json') or checks != read('availability_checks.json'):
        raise ValueError('Fold/dependency audit does not reproduce sealed data')
    for arm in ARMS:
        project(inputs[inputs.province_code.isin(pe.COHORTS[ARMS[arm][0]])],arm)
    return dict(inputs=inputs,annual=annual,folds=folds,manifest=manifest)


def validate(prepared):
    inputs,annual=prepared['inputs'],prepared['annual']
    wa.require_rows(inputs,KEYS+rb.FEATURES,{(p,y) for p in pe.COHORTS['10'] for y in rb.YEARS})
    wa.require_rows(annual[KEYS+[rb.TARGET]],KEYS+[rb.TARGET],
                    {(p,y) for p in pe.COHORTS['10'] for y in range(2009,2026)})
    folds={(f['cohort'],f['outer_year'],f['fold_year']):f for f in prepared['folds']}
    expected={(s,o,y) for s in pe.COHORTS for o in rb.OUTER_YEARS for y in range(o-3,o+1)}
    if len(prepared['folds'])!=72 or set(folds)!=expected:
        raise ValueError('Incomplete/duplicate folds')
    for (size,outer,y),fold in folds.items():
        dates={p:rb.midnight(rb.issue_date(dict(kind='fixed_calendar',anchors=pe.ANCHORS),p,y,60))
               for p in pe.COHORTS['10']}
        select=min(rb.midnight(rb.issue_date(dict(kind='fixed_calendar',anchors=pe.ANCHORS),p,outer,60)) for p in rb.PROVINCES)
        if (fold['issue_dates']!=dates or fold['fit_cutoff']!=min(dates.values())
                or fold['selection_cutoff']!=select or fold['training_rows']!=len(pe.COHORTS[size])*(y-2010)
                or fold['forecast_rows']!=len(pe.COHORTS[size])
                or {tuple(k) for k in fold['selection_keys']}!={(p,y) for p in rb.PROVINCES}):
            raise ValueError('Fold cutoff/membership/selection mismatch')
        keys=sorted((p,t) for p in pe.COHORTS[size] for t in range(2010,y))
        lookup=annual.set_index(KEYS)[rb.TARGET]
        if fold['training_labels_sha256']!=rb.digest_value([[p,t,float(lookup.loc[p,t])] for p,t in keys]):
            raise ValueError('Training labels differ from sealed fold')
    return folds


def cache_key(config,fold,arm,depth,train,test):
    return rb.digest_value(dict(protocol=config['protocol_hash'],source=config['input_hashes'],
        code=config['code_hashes'],arm=arm,cohort=pe.COHORTS[ARMS[arm][0]],candidate=candidate(arm,depth),
        year=fold['fold_year'],cutoff=fold['fit_cutoff'],issues=fold['issue_dates'],
        train=train.to_dict('records'),forecast=test.to_dict('records')))


def reference_gate(predictions):
    old=pd.read_csv(REFERENCE/'predictions.csv',dtype={'province_code':str})
    for arm,model in [('A','catboost_no_weather'),('B','catboost_with_weather')]:
        match=predictions[predictions.model.eq(arm)].merge(old[old.model.eq(model)],on=KEYS,
            validate='one_to_one',suffixes=('_new','_old'))
        if len(match)!=45 or not all(np.allclose(match[k+'_new'],match[k+'_old'],rtol=1e-12,atol=1e-10)
                                    for k in ('predicted_kg_rai','actual_kg_rai')) or not match.issue_date_new.eq(match.issue_date_old).all():
            raise ValueError('Fresh 5-province predictions differ from Phase 3; stop before expansion')


def train(prepared,config,fitter=wa.fit_predict,gate=reference_gate):
    if config['protocol']!=protocol() or config['protocol_hash']!=rb.digest_value(protocol()):
        raise ValueError('Frozen protocol changed')
    folds=validate(prepared)
    labels=prepared['annual'].set_index(KEYS)[rb.TARGET]
    cache,predictions,choices,tuning,audit={ },[],[],[],[]
    for arm,(size,_) in ARMS.items():
        provinces=pe.COHORTS[size]
        def predict(fold,depth):
            source=prepared['inputs'][prepared['inputs'].province_code.isin(provinces)]
            training=project(source[source.year_ce.lt(fold['fold_year'])].sort_values(KEYS),arm)
            testing=project(source[source.year_ce.eq(fold['fold_year'])].sort_values(KEYS),arm)
            training[rb.TARGET]=[float(labels.loc[p,y]) for p,y in training[KEYS].itertuples(index=False,name=None)]
            key=cache_key(config,fold,arm,depth,training,testing)
            reused=key in cache
            if not reused:
                values=np.asarray(fitter(training.copy(),testing.copy(),provinces,deepcopy(candidate(arm,depth))),float)
                if values.shape!=(len(provinces),) or not np.isfinite(values).all():
                    raise ValueError('Incomplete/nonfinite forecast')
                cache[key]=values.copy()
            audit.append(dict(arm=arm,outer_year=fold['outer_year'],fold_year=fold['fold_year'],depth=depth,
                reused=reused,cache_key=key,fit_cutoff=fold['fit_cutoff'],training_rows=len(training),forecast_rows=len(testing)))
            return testing[KEYS],cache[key].copy()
        for outer in rb.OUTER_YEARS:
            losses=[]
            for depth in (2,3):
                errors=[]
                for y in range(outer-3,outer):
                    fold=folds[size,outer,y]
                    keys,values=predict(fold,depth)
                    mask=keys.province_code.isin(rb.PROVINCES).to_numpy()
                    actual=np.array([float(labels.loc[p,t]) for p,t in keys[mask][KEYS].itertuples(index=False,name=None)])
                    error=float(np.mean(abs(values[mask]-actual)))
                    errors.append(error)
                    tuning.append(dict(arm=arm,outer_year=outer,inner_year=y,depth=depth,mae=error,
                        selection_rows=5,selection_cutoff=fold['selection_cutoff']))
                losses.append(float(np.mean(errors)))
            depth=(2,3)[int(np.argmin(losses))]
            fold=folds[size,outer,outer]
            keys,values=predict(fold,depth)  # Choice and predictions frozen before reading outer labels.
            choices.append(dict(arm=arm,outer_year=outer,depth=depth,inner_mae=min(losses),fit_cutoff=fold['fit_cutoff']))
            for (p,y),value in zip(keys.itertuples(index=False,name=None),values):
                predictions.append(dict(model=arm,province_code=p,year_ce=y,issue_date=fold['issue_dates'][p],
                    evaluation='primary' if p in rb.PROVINCES else 'secondary',actual_kg_rai=float(labels.loc[p,y]),predicted_kg_rai=float(value)))
        print(f'Arm {arm}: all 9 outer years completed; inner-only choices frozen',flush=True)
        if arm=='B' and gate is not None:
            gate(pd.DataFrame(predictions))
            print('Phase 3 fresh prediction parity passed before 10-province fitting',flush=True)
    tables=summarize(pd.DataFrame(predictions))
    tables.update(choices=pd.DataFrame(choices),tuning=pd.DataFrame(tuning),fit_audit=pd.DataFrame(audit))
    return tables


def summarize(frame):
    expected={(a,p,y) for a,(size,_) in ARMS.items() for p in pe.COHORTS[size] for y in rb.OUTER_YEARS}
    if frame.duplicated(['model',*KEYS]).any() or set(zip(frame.model,frame.province_code,frame.year_ce))!=expected:
        raise ValueError('Require all 270 predictions')
    if not np.isfinite(frame[['actual_kg_rai','predicted_kg_rai']].to_numpy(float)).all():
        raise ValueError('Nonfinite predictions')
    frame=frame.copy()
    frame['error']=frame.predicted_kg_rai-frame.actual_kg_rai
    frame['absolute_error']=abs(frame.error)
    tables=dict(predictions=frame)
    for name,groups in [('overall',['evaluation','model']),('by_year',['evaluation','model','year_ce']),('by_province',['evaluation','model','province_code'])]:
        records=[]
        for key,g in frame.groupby(groups):
            records.append(dict(zip(groups,key))|dict(n=len(g),mae=float(g.absolute_error.mean()),
                rmse=float(np.sqrt(np.mean(g.error**2))),bias=float(g.error.mean())))
        tables[name]=pd.DataFrame(records)
    primary=frame[frame.evaluation.eq('primary')]
    paired=primary.pivot(index=KEYS,columns='model',values='absolute_error').reset_index()
    paired['no_weather_expansion_gain']=paired.A-paired.C
    paired['weather_expansion_gain']=paired.B-paired.D
    tables['paired_errors']=paired
    rows=[]
    for name in ['no_weather_expansion_gain','weather_expansion_gain']:
        gain=paired[name]; ties=np.isclose(gain,0,atol=1e-9,rtol=0)
        rows.append(dict(comparison=name,n=45,mean_gain=float(gain.mean()),median_gain=float(gain.median()),
            wins=int(((gain>0)&~ties).sum()),ties=int(ties.sum()),losses=int(((gain<0)&~ties).sum())))
    tables['paired_gains']=pd.DataFrame(rows)
    tables['worst_errors']=frame.sort_values('absolute_error',ascending=False).groupby(['evaluation','model']).head(5)
    return tables


def run(training=False):
    prepared=load_inputs()
    validate(prepared)
    # Pre-fit parity checks do not import reference predictions into any model input.
    check_hashes(REFERENCE,json.loads((REFERENCE/'completed_artifact_hashes.json').read_text()))
    oldconfig=json.loads((REFERENCE/'config.json').read_text())
    check_hashes(rb.ROOT,oldconfig['code_sha256'])
    if oldconfig['protocol']!=wa.protocol():
        raise ValueError('Phase 3 config mismatch')
    dependencies={n:metadata.version(n) for n in oldconfig['dependencies']}
    if dependencies!=oldconfig['dependencies']:
        raise ValueError('Dependencies differ from reference')
    old=pd.read_csv(REFERENCE/'catboost_with_weather_predictors.csv',dtype={'province_code':str},float_precision='round_trip').sort_values(KEYS)
    current=prepared['inputs'][prepared['inputs'].province_code.isin(rb.PROVINCES)].sort_values(KEYS)
    if not np.array_equal(old[KEYS].to_numpy(),current[KEYS].to_numpy()) or not np.allclose(old[rb.FEATURES],current[rb.FEATURES],rtol=1e-14,atol=1e-12):
        raise ValueError('Reference predictors changed')
    protected=protected_hashes()
    protected.update({str(p.relative_to(rb.ROOT)).replace('\\','/'):rb.digest(p) for p in pe.ROOT.rglob('*') if p.is_file()})
    unchanged(protected)
    config=dict(protocol=protocol(),protocol_hash=rb.digest_value(protocol()),dependencies=dependencies,
        input_hashes=json.loads((INPUT/'completed_artifact_hashes.json').read_text()),
        code_hashes={str(p.relative_to(rb.ROOT)).replace('\\','/'):rb.digest(p) for p in [Path(__file__),Path(wa.__file__),Path(pe.__file__),rb.ROOT/'tools/compare_harvest_stage_yield.py']},
        protected_hashes=protected,input_snapshot=str(INPUT),reference=str(REFERENCE))
    if not training:
        print('Preflight passed; no training requested',flush=True)
        return config
    destination=OUTPUT/('phase6b_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    destination.mkdir(parents=True,exist_ok=False)
    pe.write_json(destination/'config.json',config)
    pe.write_json(destination/'manifest.json',prepared['manifest'])
    pe.write_json(destination/'folds.json',prepared['folds'])
    snapshot=destination/'source_snapshot';snapshot.mkdir()
    for name in config['code_hashes']:
        with (snapshot/name.replace('/','__')).open('xb') as handle:
            handle.write((rb.ROOT/name).read_bytes())
    try:
        tables=train(prepared,config)
        for name,table in tables.items():
            pe.write_csv(destination/(name+'.csv'),table)
        unchanged(protected)
        pe.write_json(destination/'status.json',dict(training=True,complete=True,pit_certified=False,reference_parity=True))
        pe.write_json(destination/'completed_artifact_hashes.json',{str(p.relative_to(destination)).replace('\\','/'):rb.digest(p) for p in destination.rglob('*') if p.is_file()})
    except Exception as exc:
        pe.write_json(destination/'failure.json',dict(error=str(exc),training=True,complete=False,pit_certified=False))
        raise
    print(f'Completed once: {destination}',flush=True)
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train',action='store_true')
    run(parser.parse_args().train)
