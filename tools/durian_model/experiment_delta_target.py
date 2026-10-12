"""Phase 7B: frozen Level/Delta experiment, outer evaluation gated by inner results."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
import experiment_province_expansion_training as et
from availability_guard import timestamp

rb, pe, wa = et.rb, et.pe, et.wa
KEYS = et.KEYS
REFERENCE = et.OUTPUT / 'phase6b_20261011T140737783448Z'
OUTPUT = rb.OUT / 'delta_target_exploratory'
ARMS = ('level', 'delta')
PROVINCES = pe.COHORTS['10']


def protocol():
    return dict(base=et.protocol(), cohort='10', features=rb.FEATURES,
        targets=dict(level='yield', delta='yield - prior_yield'),
        reconstruction='level: raw; delta: lag + signed raw; then max(0, yield) for both',
        selection='independent depth 2/3, inner reconstructed yield MAE; depth2 exact ties',
        gate=dict(min_inner_improvement=.05, rmse_not_worse=True, max_province_degradation=.10),
        aggregate='135 primary inner context rows per arm, including repeats',
        outer='only fit and evaluate after aggregate inner gate passes', pit_certified=False)


def reconstruct(raw, lag, arm):
    if arm not in ARMS:
        raise ValueError('Unknown target arm')
    raw, lag = np.asarray(raw, float), np.asarray(lag, float)
    if raw.shape != lag.shape or not np.isfinite(raw).all() or not np.isfinite(lag).all():
        raise ValueError('Invalid prediction/reconstruction shape or value')
    yield_raw = raw + lag if arm == 'delta' else raw.copy()
    return yield_raw, np.maximum(0, yield_raw)


def signed_fit(training, testing, depth):
    # Do not call the shared fitter: it clamps signed targets before reconstruction.
    if depth not in (2,3) or training.empty or testing.empty or training.year_ce.max() >= testing.year_ce.min():
        raise ValueError('Invalid depth or temporal fitting boundary')
    from catboost import CatBoostRegressor
    x = wa.design(training, PROVINCES, rb.FEATURES)
    xt = wa.design(testing, PROVINCES, rb.FEATURES)
    model = CatBoostRegressor(iterations=400, loss_function='RMSE', boosting_type='Ordered',
        random_seed=42, thread_count=1, verbose=False, allow_writing_files=False,
        depth=depth, learning_rate=.03, l2_leaf_reg=10)
    model.fit(x, training[rb.TARGET].to_numpy(float))
    return np.asarray(model.predict(xt), float)


def target_audit(prepared):
    """Consumed target pairs, not estimates of historical publication dates."""
    folds = et.validate(prepared)
    lookup = prepared['annual'].set_index(KEYS)[rb.TARGET]
    inputs = prepared['inputs'].set_index(KEYS)
    rows, dependencies = [], []
    for (size, outer, year), fold in folds.items():
        if size != '10':
            continue
        for role, keys, cutoff in [
            ('training_label', [(p,y) for p in PROVINCES for y in range(2010,year)], fold['fit_cutoff']),
            ('selection_label', [(p,year) for p in rb.PROVINCES] if year < outer else [], fold['selection_cutoff'])]:
            for p,y in keys:
                current, prior = float(lookup.loc[p,y]), float(lookup.loc[p,y-1])
                if prior != float(inputs.loc[p,y][wa.LAG]):
                    raise ValueError('Target prior yield differs from consumed lag')
                pair = [p,y,current,y-1,prior]
                rows.append(dict(outer_year=outer, fold_year=year, province_code=p, target_year=y,
                    role=role, cutoff=cutoff, yield_value=current, lag_year=y-1, lag_value=prior,
                    signed_delta=current-prior, pair_sha256=rb.digest_value(pair)))
                ref = ('training_labels:' if role == 'training_label' else 'selection_labels:') + p
                if ref not in prepared['manifest']['records']:
                    raise ValueError('Missing target dependency')
                record = prepared['manifest']['records'][ref]
                actual_version = rb.digest(rb.ROOT / record['path'])
                for source_year in (y,y-1):
                    if record.get('publication_date') and timestamp(record['publication_date']) > timestamp(cutoff):
                        raise ValueError('Known future target-pair publication')
                    warnings = rb.check(record,role,actual_version,cutoff,'exploratory',f'{source_year}-12-31')
                    dependencies.append(dict(outer_year=outer,fold_year=year,province_code=p,
                        target_year=y,source_year=source_year,role=role,cutoff=cutoff,
                        source_version=actual_version,publication_date=record.get('publication_date'),
                        availability_status=record['availability_status'],warnings=json.dumps(warnings)))
    return pd.DataFrame(rows), pd.DataFrame(dependencies)


def metrics(frame, groups):
    rows = []
    for key,g in frame.groupby(groups):
        key = key if isinstance(key,tuple) else (key,)
        error = g.predicted_kg_rai.to_numpy() - g.actual_kg_rai.to_numpy()
        rows.append(dict(zip(groups,key)) | dict(n=len(g),mae=float(np.mean(abs(error))),
            rmse=float(np.sqrt(np.mean(error**2))),bias=float(np.mean(error)),
            p90_ae=float(np.quantile(abs(error),.9)),max_ae=float(np.max(abs(error)))))
    return pd.DataFrame(rows)


def inner_gate(frame):
    expected = {(a,o,y,p) for a in ARMS for o in rb.OUTER_YEARS
                for y in range(o-3,o) for p in rb.PROVINCES}
    keys = ['arm','outer_year','fold_year','province_code']
    if frame.duplicated(keys).any() or set(frame[keys].itertuples(index=False,name=None)) != expected:
        raise ValueError('Incomplete/duplicate inner contexts; never drop rows')
    if not np.isfinite(frame[['actual_kg_rai','predicted_kg_rai']].to_numpy(float)).all():
        raise ValueError('Nonfinite inner errors')
    if not frame.fold_year.lt(frame.outer_year).all():
        raise ValueError('Outer targets entered inner gate')
    paired = frame.pivot(index=keys[1:],columns='arm',values='actual_kg_rai')
    if not np.array_equal(paired.level.to_numpy(),paired.delta.to_numpy()):
        raise ValueError('Arms must evaluate identical inner outcomes')
    totals = metrics(frame,['arm']).set_index('arm')
    provinces = metrics(frame,['arm','province_code']).set_index(['arm','province_code'])
    baseline = float(totals.loc['level','mae'])
    if baseline <= 0:
        raise ValueError('Cannot define percentage improvement on zero baseline')
    improvement = float(1-totals.loc['delta','mae']/baseline)
    province_gate = []
    for p in rb.PROVINCES:
        level = float(provinces.loc['level',p]['mae'])
        delta = float(provinces.loc['delta',p]['mae'])
        province_gate.append(dict(province_code=p,level_mae=level,delta_mae=delta,
            passed=bool(delta <= 1.10*level)))
    mae_pass = bool(totals.loc['delta','mae'] <= .95*baseline)
    rmse_pass = bool(totals.loc['delta','rmse'] <= totals.loc['level','rmse'])
    return dict(passed=bool(mae_pass and rmse_pass and all(p['passed'] for p in province_gate)),
        mae_pass=mae_pass,rmse_pass=rmse_pass,improvement_fraction=improvement,
        overall=totals.reset_index().to_dict('records'),provinces=province_gate,
        contexts_per_arm=27,rows_per_arm=135,unique_keys_per_arm=55,
        duplicate_rows_per_arm=80,independent_significance_claim=False)


def cache_key(config,fold,arm,depth,training,testing):
    return rb.digest_value(dict(protocol=config['protocol_hash'],source=config['input_hashes'],
        code=config['code_hashes'],arm=arm,depth=depth,fold_year=fold['fold_year'],
        cutoff=fold['fit_cutoff'],issues=fold['issue_dates'],provinces=PROVINCES,
        training=training.to_dict('records'),testing=testing.to_dict('records')))


class Session:
    def __init__(self,prepared,config,fitter=signed_fit):
        if config['protocol'] != protocol() or config['protocol_hash'] != rb.digest_value(protocol()):
            raise ValueError('Frozen protocol changed')
        self.folds = et.validate(prepared)
        self.lineage,self.dependencies = target_audit(prepared)
        self.prepared,self.config,self.fitter = prepared,config,fitter
        self.cache,self.audit = {},[]

    def predict(self,fold,arm,depth):
        source = self.prepared['inputs']
        training = et.project(source[source.year_ce.lt(fold['fold_year'])].sort_values(KEYS),'D')
        testing = et.project(source[source.year_ce.eq(fold['fold_year'])].sort_values(KEYS),'D')
        lookup = self.prepared['annual'].set_index(KEYS)[rb.TARGET]
        training[rb.TARGET] = [float(lookup.loc[p,y]) for p,y in training[KEYS].itertuples(index=False,name=None)]
        if arm == 'delta':
            training[rb.TARGET] = training[rb.TARGET] - training[wa.LAG]
        elif arm != 'level':
            raise ValueError('Unknown target transform')
        key = cache_key(self.config,fold,arm,depth,training,testing)
        reused = key in self.cache
        if not reused:
            raw = np.asarray(self.fitter(training.copy(),testing.copy(),depth),float)
            if raw.shape != (10,) or not np.isfinite(raw).all():
                raise ValueError('Missing/nonfinite target predictions')
            self.cache[key] = raw.copy()
        raw = self.cache[key].copy()
        yield_raw,values = reconstruct(raw,testing[wa.LAG],arm)
        self.audit.append(dict(arm=arm,outer_year=fold['outer_year'],fold_year=fold['fold_year'],
            depth=depth,cache_key=key,reused=reused,fit_cutoff=fold['fit_cutoff'],
            training_rows=len(training),forecast_rows=len(testing),
            training_target_hash=rb.digest_value(training[KEYS+[rb.TARGET]].to_dict('records'))))
        return testing,raw,yield_raw,values

    def inner(self):
        records,all_candidates,choices,tuning = [],[],[],[]
        for arm in ARMS:
            for outer in rb.OUTER_YEARS:
                candidates = {}
                for depth in (2,3):
                    candidate_rows = []
                    for year in range(outer-3,outer):
                        fold = self.folds['10',outer,year]
                        testing,raw,yield_raw,values = self.predict(fold,arm,depth)
                        lookup = self.prepared['annual'].set_index(KEYS)[rb.TARGET]
                        rows = []
                        for i,(p,y) in enumerate(testing[KEYS].itertuples(index=False,name=None)):
                            if p not in rb.PROVINCES:
                                continue
                            rows.append(dict(arm=arm,outer_year=outer,fold_year=year,province_code=p,
                                year_ce=y,depth=depth,actual_kg_rai=float(lookup.loc[p,y]),
                                raw_target_prediction=float(raw[i]),lag_yield=float(testing.iloc[i][wa.LAG]),
                                reconstructed_raw_kg_rai=float(yield_raw[i]),predicted_kg_rai=float(values[i]),
                                clipped=bool(yield_raw[i]<0),fit_cutoff=fold['fit_cutoff'],
                                selection_cutoff=fold['selection_cutoff']))
                        candidate_rows.extend(rows)
                        m = metrics(pd.DataFrame(rows),['arm']).iloc[0]
                        tuning.append(dict(arm=arm,outer_year=outer,inner_year=year,depth=depth,
                            mae=float(m.mae),rmse=float(m.rmse),selection_rows=5))
                    candidates[depth] = pd.DataFrame(candidate_rows)
                    all_candidates.extend(candidate_rows)
                depth = min((2,3),key=lambda d:float(metrics(candidates[d],['arm']).iloc[0].mae))
                chosen = candidates[depth]
                m = metrics(chosen,['arm']).iloc[0]
                choices.append(dict(arm=arm,outer_year=outer,depth=depth,inner_mae=float(m.mae),
                    inner_rmse=float(m.rmse),fit_cutoff=self.folds['10',outer,outer]['fit_cutoff']))
                records.extend(chosen.to_dict('records'))
        frame = pd.DataFrame(records)
        return dict(inner_predictions=frame,inner_candidate_predictions=pd.DataFrame(all_candidates),
                    choices=pd.DataFrame(choices),tuning=pd.DataFrame(tuning)),inner_gate(frame)

    def outer(self,choices,gate):
        if not gate['passed']:
            raise ValueError('Inner gate failed: outer fit/evaluation prohibited')
        expected = {(a,o) for a in ARMS for o in rb.OUTER_YEARS}
        if choices.duplicated(['arm','outer_year']).any() or set(zip(choices.arm,choices.outer_year)) != expected:
            raise ValueError('Incomplete choices')
        records = []
        for c in choices.to_dict('records'):
            fold = self.folds['10',c['outer_year'],c['outer_year']]
            testing,raw,yield_raw,values = self.predict(fold,c['arm'],c['depth'])
            # Freeze predictions before looking up this fold's outer outcomes.
            lookup = self.prepared['annual'].set_index(KEYS)[rb.TARGET]
            for i,(p,y) in enumerate(testing[KEYS].itertuples(index=False,name=None)):
                records.append(dict(arm=c['arm'],province_code=p,year_ce=y,
                    evaluation='primary' if p in rb.PROVINCES else 'secondary',
                    actual_kg_rai=float(lookup.loc[p,y]),raw_target_prediction=float(raw[i]),
                    reconstructed_raw_kg_rai=float(yield_raw[i]),predicted_kg_rai=float(values[i]),
                    clipped=bool(yield_raw[i]<0),depth=c['depth'],issue_date=fold['issue_dates'][p]))
        frame = pd.DataFrame(records)
        if len(frame)!=180 or frame.duplicated(['arm',*KEYS]).any():
            raise ValueError('Incomplete outer predictions')
        old = pd.read_csv(REFERENCE/'predictions.csv',dtype={'province_code':str},float_precision='round_trip')
        match = frame[frame.arm.eq('level')].merge(old[old.model.eq('D')],on=KEYS,validate='one_to_one',suffixes=('_new','_old'))
        if len(match)!=90 or not np.allclose(match.predicted_kg_rai_new,match.predicted_kg_rai_old,rtol=1e-12,atol=1e-10):
            raise ValueError('Level prediction parity failed; do not interpret outer scores')
        frame['error'] = frame.predicted_kg_rai-frame.actual_kg_rai
        frame['absolute_error'] = abs(frame.error)
        paired = frame.pivot(index=['evaluation',*KEYS],columns='arm',values='absolute_error').reset_index()
        paired['gain'] = paired.level-paired.delta
        return dict(outer_predictions=frame,outer_overall=metrics(frame,['evaluation','arm']),
            outer_by_province=metrics(frame,['evaluation','arm','province_code']),
            outer_by_year=metrics(frame,['evaluation','arm','year_ce']),paired_errors=paired,
            worst_errors=frame.sort_values('absolute_error',ascending=False).groupby(['evaluation','arm']).head(5))


def preflight():
    cfg = json.loads((REFERENCE/'config.json').read_text())
    et.check_hashes(rb.ROOT,cfg['protected_hashes'])
    et.check_hashes(REFERENCE,json.loads((REFERENCE/'postflight_artifact_hashes.json').read_text()))
    if cfg['protocol'] != et.protocol() or cfg['protocol_hash'] != rb.digest_value(et.protocol()):
        raise ValueError('Phase 6B protocol changed')
    dependencies = {n:metadata.version(n) for n in cfg['dependencies']}
    if dependencies != cfg['dependencies']:
        raise ValueError('Dependency mismatch')
    prepared = et.load_inputs()
    lineage,deps = target_audit(prepared)
    protected = et.protected_hashes()
    for root in (pe.ROOT,et.OUTPUT,OUTPUT):
        protected.update({str(p.relative_to(rb.ROOT)).replace('\\','/'):rb.digest(p)
                          for p in root.rglob('*') if p.is_file()})
    et.unchanged(protected)
    codes = [Path(__file__),Path(et.__file__),Path(pe.__file__),Path(wa.__file__),
             rb.ROOT/'tools/compare_harvest_stage_yield.py',rb.ROOT/'tests/test_delta_target.py']
    config = dict(protocol=protocol(),protocol_hash=rb.digest_value(protocol()),dependencies=dependencies,
        input_hashes=cfg['input_hashes'],manifest_hash=rb.digest(et.INPUT/'manifest.json'),
        code_hashes={str(p.relative_to(rb.ROOT)).replace('\\','/'):rb.digest(p) for p in codes},
        protected_hashes=protected,reference=str(REFERENCE),input_snapshot=str(et.INPUT),
        target_lineage_hash=rb.digest_value(lineage.to_dict('records')),
        availability_hash=rb.digest_value(deps.to_dict('records')))
    return prepared,config,lineage,deps


def reserve(run_id):
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in run_id):
        raise ValueError('Unsafe run id')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    destination = OUTPUT/run_id
    destination.mkdir(exist_ok=False)
    return destination


def run(training=False):
    prepared,config,lineage,deps = preflight()
    if not training:
        print(f'Preflight passed: {len(lineage)} target pairs; no training requested',flush=True)
        return config
    destination = reserve('phase7b_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    pe.write_json(destination/'config.json',config)
    pe.write_json(destination/'manifest.json',prepared['manifest'])
    pe.write_json(destination/'folds.json',prepared['folds'])
    pe.write_csv(destination/'target_lineage.csv',lineage)
    pe.write_csv(destination/'target_availability.csv',deps)
    snapshot = destination/'source_snapshot';snapshot.mkdir()
    for name in config['code_hashes']:
        with (snapshot/name.replace('/','__')).open('xb') as f:
            f.write((rb.ROOT/name).read_bytes())
    try:
        session = Session(prepared,config)
        tables,gate = session.inner()
        reference_choices = pd.read_csv(REFERENCE/'choices.csv')
        original = reference_choices[reference_choices.arm.eq('D')].sort_values('outer_year')
        level = tables['choices'][tables['choices'].arm.eq('level')].sort_values('outer_year')
        if not np.array_equal(level.depth.to_numpy(),original.depth.to_numpy()) or not np.allclose(level.inner_mae,original.inner_mae,rtol=1e-12,atol=1e-10):
            raise ValueError('Level inner selection parity failed')
        pe.write_json(destination/'inner_gate.json',gate)
        for name,table in tables.items():
            pe.write_csv(destination/(name+'.csv'),table)
        print('Inner gate '+('PASSED' if gate['passed'] else 'FAILED')+'; criteria frozen',flush=True)
        if gate['passed']:
            for name,table in session.outer(tables['choices'],gate).items():
                pe.write_csv(destination/(name+'.csv'),table)
        pe.write_csv(destination/'fit_audit.csv',pd.DataFrame(session.audit))
        et.unchanged(config['protected_hashes'])
        et.check_hashes(rb.ROOT,config['code_hashes'])
        pe.write_json(destination/'status.json',dict(complete=True,training=True,inner_gate=gate['passed'],
            outer_evaluated=gate['passed'],pit_certified=False,level_inner_parity=True,
            delta_development_stopped=not gate['passed']))
        pe.write_json(destination/'completed_artifact_hashes.json',
            {str(p.relative_to(destination)).replace('\\','/'):rb.digest(p) for p in destination.rglob('*') if p.is_file()})
    except Exception as exc:
        pe.write_json(destination/'failure.json',dict(error=str(exc),complete=False,pit_certified=False))
        raise
    print(f'Completed once: {destination}',flush=True)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train',action='store_true')
    run(parser.parse_args().train)
