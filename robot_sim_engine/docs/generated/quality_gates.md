---
owner: quality
audience: maintainer
status: generated
source_of_truth: regenerated
generated_by: scripts/regenerate_quality_contracts.py
last_reviewed: 2026-04-18
---
# Quality Gates

- release blockers: `python scripts/verify_release_blockers.py` => quick_quality + compatibility_budget + unit_and_regression + gui_smoke
- runtime contracts: `python scripts/verify_runtime_gate_layer.py` => runtime_contracts + performance_smoke + headless_runtime_baseline + planning_scene_regression + collision_validation_matrix + scene_capture_baseline
- runtime contract gate: `python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs` + `python scripts/verify_compatibility_retirement.py` + `python scripts/verify_perf_budget_config.py`
- runtime baseline/details: `python scripts/verify_runtime_baseline.py --mode headless` + `pytest tests/unit/test_planning_scene_v2.py tests/unit/test_scene_authority_service.py -q` + `pytest tests/unit/test_planning_scene_validation.py tests/unit/test_scene_capability_surface.py -q` + `pytest tests/unit/test_scene_capture_support.py tests/unit/test_scene_render_contracts.py -q` + `pytest tests/performance/test_ik_smoke.py -q`
- governance evidence: `python scripts/verify_governance_gate_layer.py` => governance_evidence + docs_sync
- governance evidence detail: `python scripts/verify_module_governance.py --execute-gates --evidence-out artifacts/module_governance_evidence.json` + `python scripts/verify_benchmark_matrix.py --execute-gates --execute --evidence-out artifacts/benchmark_matrix_evidence.json` + `python scripts/collect_quality_evidence.py --out artifacts/quality_evidence.json --markdown-out artifacts/quality_evidence.md --release-manifest-out artifacts/release_manifest.json --merge artifacts/module_governance_evidence.json artifacts/benchmark_matrix_evidence.json runtime_contracts compatibility_budget performance_smoke`; the aggregated manifest now derives `artifact_ready`, `environment_ready`, and `release_ready` separately and always evaluates the checked-in release/gui environment contracts
- aggregated quality evidence rejects governance/benchmark artifacts that were not generated with their required `--execute-gates` execution contract.
- aggregated quality evidence rejects artifacts whose source-tree fingerprint or tracked release-file count does not match the current repository checkout; the original repo_root is retained as provenance metadata but is not treated as a transport-stability requirement.
- unit/regression: `pytest tests/unit tests/regression -q`
- shipped behavior contracts: repo profiles must remain differentiable, coordinators must stay on explicit dependency injection paths, export/screenshot coordinators must stay on worker lifecycle routes, render degradation state must stay projected in SessionState.render_runtime through a typed status-panel subscription flow, clean bootstrap/headless mainline paths must stay within the configured compatibility budget, public plugin SDK examples must remain loader-compatible, render telemetry must remain recorded as bounded structured state transitions + operation spans + sampling counters + backend-specific performance telemetry, diagnostics widgets must consume structured telemetry log sections, scene authority summaries must expose declaration/validation/render geometry layers, and screenshot/importer fidelity baselines must stay reproducible from checked-in fixtures
- full validation: `pytest --cov=src/robot_sim --cov-report=term-missing --cov-report=json:coverage.json -q` with `fail_under = 80` + `python scripts/verify_partition_coverage.py --coverage-json coverage.json`
- gui smoke: `python scripts/verify_gui_smoke.py`; the gate prefers real `PySide6` and falls back to the repository-local Qt test shim only inside the verification process so deterministic offscreen smoke remains executable in constrained environments. Evidence must retain `runtime_kind`, `gui_real_runtime_ok`, and `gui_shim_runtime_ok` so release review can distinguish shim smoke from a real GUI baseline
- clean source bundle: `python scripts/package_release.py --output dist/source-release.zip --top-level-dir robot_sim_engine`; packaging now stages a writable clean-source mirror, regenerates checked-in contract docs inside the stage, re-verifies the staged tree, and refuses to ship stale contract surfaces from the caller working copy.
- contract regeneration: `python scripts/regenerate_quality_contracts.py` + `python scripts/verify_docs_information_architecture.py` + `git diff --exit-code -- docs`; docs gate now enforces full explanatory-doc semantic coverage through doc-class policies plus file-specific semantic contracts
