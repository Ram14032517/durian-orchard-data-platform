"""Phase 10D full persisted review. Report only: conflicts never produce a release."""
from pathlib import Path
import json
from tools import build_tha_mai_spatial_pilot as p
from tools import diagnose_tha_mai_geometry as d
from tools import robust_tha_mai_geometry_review as r

OUT = d.BASE / "phase10d_20261012_review_v1"


def main():
    root=p.ROOT; out=root/OUT
    p.require(out.is_dir() and not (out/"review_report.json").exists(),"Preflight missing or report overwrite refused")
    before=p.read_json(out/"preflight_protected_hashes.json")
    authorized={"tools/review_tha_mai_spatial_pilot.py"}
    p.require(all(p.sha(root/k)==v for k,v in before.items() if k not in authorized),"Protected input mismatch")
    p.previous.verify_seal(root,p.DEFAULT); p.previous.verify_seal(root,d.FAILED)
    diag=p.read_json(root/d.OUT/"output_manifest.json")
    p.require(d.digest(diag["files"])==diag["manifest_payload_sha256"],"Golden fixture seal mismatch")
    p.require(all(p.sha(root/d.OUT/k)==v for k,v in diag["files"].items()),"Golden artifacts changed")
    source_manifest=p.read_json(root/p.DEFAULT/"source_manifest.json")
    p.require(all(p.sha(root/x["path"])==x["sha256"] for x in source_manifest),"Source hashes changed")
    dataset_path=root/p.DEFAULT/"dataset.json"; data_hash=p.sha(dataset_path)
    dataset=p.read_json(dataset_path); logical_before=p.digest(dataset)
    source_ids={x["source_id"] for x in source_manifest}
    for name,rows in dataset["tables"].items():
        for row in rows:
            p.require(set(row["source_ids"]).issubset(source_ids),"Unknown source lineage")
    report=r.review(dataset)
    p.require(report["pure_fragment_count"]==1504,"Pure fragment census changed")
    p.require(p.digest(dataset)==logical_before and p.sha(dataset_path)==data_hash,"Input mutated")
    after={k:p.sha(root/k) for k in before}
    unauthorized=[k for k,v in before.items() if k not in authorized and after[k]!=v]
    p.require(not unauthorized,"Protected files changed during review")
    report.update({"dataset_sha256_before":data_hash,"dataset_sha256_after":p.sha(dataset_path),
                   "logical_digest_before":logical_before,"logical_digest_after":p.digest(dataset),
                   "release_status":"not_accepted", "accepted_release_created":False,
                   "phase10b_status_unchanged":"QC FAILED / Quarantined",
                   "review_algorithm_code_sha256":p.sha(root/"tools/robust_tha_mai_geometry_review.py"),
                   "review_caller_code_sha256":p.sha(root/"tools/review_tha_mai_spatial_pilot.py"),
                   "golden_fixture_sha256":p.sha(root/d.OUT/"minimal_inputs.json")})
    p.write(out/"review_report.json",report)
    summary={"status":report["status"],"algorithm":report["algorithm"],"geos_version":report["geos_version"],
             "pure_fragments":{s:sum(x["status"]==s for x in report["pure_fragments"]) for s in ["pass","failed","inconclusive"]},
             "parent_partitions":{s:sum(x["status"]==s for x in report["parent_partitions"]) for s in ["pass","failed","inconclusive"]},
             "nonpassing":[{"label":x["label"],"status":x["status"],"error":x.get("error"),
                "failed_checks":[c for c in x["checks"] if not c["pass"]],
                "material_conflicts":[c for c in x["operation_conflicts"] if c["material"]]}
                for x in report["pure_fragments"]+report["parent_partitions"] if x["status"]!="pass"],
             "global_checks":report["global_checks"],"public_release":"HOLD","accepted_release_created":False}
    p.write(out/"summary.json",summary)
    p.write(out/"protected_verification.json",{"before":before,"after":after,"unauthorized_changes":[],
                "authorized_changes":[k for k in authorized if before[k]!=after[k]],
                "immutable_files_unchanged":len(before)-len(authorized),
                "production_sha256":p.sha(root/p.previous.MODEL),"status":"pass"})
    print(json.dumps(summary,ensure_ascii=False))


if __name__=="__main__": main()
