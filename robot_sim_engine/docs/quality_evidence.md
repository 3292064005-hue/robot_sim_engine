# Quality Evidence

- contract docs (`docs/*.md`) remain deterministic checked-in specifications.
- executed quality evidence is written as JSON artifacts through `scripts/collect_quality_evidence.py`, `scripts/verify_module_governance.py --evidence-out`, and `scripts/verify_benchmark_matrix.py --evidence-out`.
- `artifacts/release_manifest.json` is the canonical aggregated release-readiness summary; release review must evaluate `artifact_ready`, `environment_ready`, and `release_ready` together rather than treating executed artifacts alone as a sufficient release signal.
- evidence artifacts must include a runtime fingerprint (python / platform / machine) so perf and governance results stay attributable to the environment that produced them.
- evidence artifacts must also include a transportable source-tree fingerprint (`repo_root`, `source_tree_fingerprint`, `source_tree_file_count`, `generated_at_utc`); aggregation rejects mixed-source evidence by comparing the source-tree fingerprint + file count, while tolerating repository relocation after packaging.
- GUI smoke evidence must preserve whether the verified runtime was real `PySide6` or the repository-local test shim; shim success is acceptable for constrained smoke coverage but does not satisfy the checked-in GUI release environment contract.
- promotion and benchmark decisions should prefer executed evidence artifacts over static governance summaries whenever both are available.
