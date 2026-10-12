"""Phase 10F review/tests gate, immutable internal release proposal; no overlay."""
from pathlib import Path
import shutil
import subprocess
import sys
from tools import build_tha_mai_spatial_pilot as p
from tools import diagnose_tha_mai_geometry as d
from tools import robust_tha_mai_geometry_review as r

OUT=d.BASE/"phase10f_20261012_policy_v1"
RELEASE=d.BASE/"phase10f_20261012_internal_accepted_proposal_v1"
AUTHORIZED={"tools/robust_tha_mai_geometry_review.py","tests/test_robust_tha_mai_geometry_review.py"}


def protected(before):
    changed=[k for k,v in before.items() if not (p.ROOT/k).exists() or p.sha(p.ROOT/k)!=v]
    p.require(not(set(changed)-AUTHORIZED),"Unauthorized protected changes")
    p.require(p.sha(p.ROOT/p.previous.MODEL)==p.previous.MODEL_HASH,"Production changed")
    return {"checked":len(before),"unchanged":len(before)-len(changed),"authorized_changes":changed,
            "unauthorized_changes":[],"production_sha256":p.sha(p.ROOT/p.previous.MODEL)}


def seal(out):
    files={x.name:p.sha(x) for x in out.iterdir() if x.is_file() and x.name!="output_manifest.json"}
    p.write(out/"output_manifest.json",{"files":files,"manifest_payload_sha256":p.digest(files)})
    p.previous.verify_seal(p.ROOT,out.relative_to(p.ROOT))


def main():
    out=p.ROOT/OUT; release=p.ROOT/RELEASE
    p.require(out.exists() and not (out/"review_report.json").exists() and not release.exists(),"Refuse overwrite")
    before=p.read_json(out/"preflight_protected_hashes.json"); protected(before)
    for folder in [p.DEFAULT,d.FAILED,d.BASE/"phase10d_20261012_review_v1",d.BASE/"phase10e_20261012_verification_v1"]:
        p.previous.verify_seal(p.ROOT,folder)
    m=p.read_json(p.ROOT/d.OUT/"output_manifest.json")
    p.require(d.digest(m["files"])==m["manifest_payload_sha256"],"Golden seal payload")
    p.require(all(p.sha(p.ROOT/d.OUT/k)==v for k,v in m["files"].items()),"Golden artifacts changed")
    sources=p.read_json(p.ROOT/p.DEFAULT/"source_manifest.json")
    p.require(all(p.sha(p.ROOT/x["path"])==x["sha256"] for x in sources),"Source hash mismatch")
    data=p.read_json(p.ROOT/p.DEFAULT/"dataset.json"); original=p.digest(data)
    report=r.review(data)
    p.require(p.digest(data)==original,"Dataset mutated")
    p.require(report["pure_fragment_count"]==1504 and len(report["parent_partitions"])==3025,"Census mismatch")
    p.write(out/"review_report.json",report)
    p.write(out/"summary.json",{ "status":report["status"],"algorithm":r.ALGORITHM,
        "pure_fragments":{s:sum(x["status"]==s for x in report["pure_fragments"]) for s in ["pass","failed","inconclusive"]},
        "parent_partitions":{s:sum(x["status"]==s for x in report["parent_partitions"]) for s in ["pass","failed","inconclusive"]},
        "warnings":report["diagnostic_warnings"],"global_checks":report["global_checks"],"public_release":"HOLD"})
    p.require(report["status"]=="pass","Primary checks not passing; stop before release")
    node=Path(sys.base_prefix).parent/"node/bin/node.exe"
    commands={"python":[sys.executable,"-X","utf8","-B","-m","unittest","discover","-s","tests","-p","test_*.py","-q"],
              "javascript":[str(node),"--test"]+[str(x.relative_to(p.ROOT)) for x in sorted((p.ROOT/"tests").glob("test*.js"))]}
    results={}
    for name,command in commands.items():
        print("Running repository "+name+" tests",flush=True)
        test=subprocess.run(command,cwd=p.ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace")
        results[name]={"command":command,"returncode":test.returncode,"stdout":test.stdout,"stderr":test.stderr}
        p.write(out/(name+"_tests.json"),results[name])
        p.require(test.returncode==0,"Repository tests failed: "+name)
    p.write(out/"protected_verification.json",protected(before))
    provenance={"dataset_sha256":p.sha(p.ROOT/p.DEFAULT/"dataset.json"),"dataset_logical_digest":original,
        "golden_fixture_sha256":p.sha(p.ROOT/d.OUT/"minimal_inputs.json"),
        "review_code_sha256":p.sha(p.ROOT/"tools/robust_tha_mai_geometry_review.py"),
        "runner_code_sha256":p.sha(Path(__file__)),"tests_code_sha256":p.sha(p.ROOT/"tests/test_robust_tha_mai_geometry_review.py"),
        "geos_version":report["geos_version"],"shapely_version":report["shapely_version"],
        "python":sys.version,"algorithm":r.ALGORITHM,"qc_tolerance_rai":p.TOL_RAI}
    p.write(out/"provenance.json",provenance)
    release.mkdir(exist_ok=False)
    # Copy byte-for-byte, not reserialize or relabel the historical source dataset.
    for name in ["dataset.json","source_manifest.json"]:
        shutil.copyfile(p.ROOT/p.DEFAULT/name,release/name)
        p.require(p.sha(release/name)==p.sha(p.ROOT/p.DEFAULT/name),"Release copy mismatch")
    p.write(release/"release_metadata.json",{ "status":"internal_accepted_proposal",
        "qc_status":"accepted_under_phase10f_primary_policy","public_release":"HOLD",
        "source_quarantine_status":"unchanged_QC_FAILED", "source_directory":p.DEFAULT.as_posix(),
        "review_evidence":OUT.as_posix(),"warning_count":len(report["diagnostic_warnings"]),
        "limitations":["same GEOS kernel; not cross-engine certified","no district/orchard yield inference","no public release"],
        **provenance})
    shutil.copyfile(out/"summary.json",release/"qc_summary.json")
    seal(release); seal(out)
    protected(before)
    print("Primary checks and repository suites passed; internal release proposal sealed",flush=True)


if __name__=="__main__": main()
