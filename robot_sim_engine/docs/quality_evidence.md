# Quality Evidence

- contract docs (`docs/*.md`) remain deterministic checked-in specifications.
- executed quality evidence is written as JSON artifacts through `scripts/collect_quality_evidence.py`, `scripts/verify_module_governance.py --evidence-out`, and `scripts/verify_benchmark_matrix.py --evidence-out`.
- evidence artifacts must include a runtime fingerprint (python / platform / machine) so perf and governance results stay attributable to the environment that produced them.
- promotion and benchmark decisions should prefer executed evidence artifacts over static governance summaries whenever both are available.
