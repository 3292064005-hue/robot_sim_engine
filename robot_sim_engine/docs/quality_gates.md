# Quality Gates

<<<<<<< HEAD
- quick quality: `ruff check src tests` + targeted `mypy` (`tool.mypy.files`) + `python scripts/verify_quality_contracts.py` + `python scripts/verify_module_governance.py` + `python scripts/verify_benchmark_matrix.py` + `python scripts/verify_runtime_baseline.py --mode headless` + `python scripts/verify_compatibility_budget.py --scenario clean_headless_mainline` + `python scripts/verify_perf_budget_config.py` + `pytest tests/unit tests/regression -q`
- shipped behavior contracts: repo profiles must remain differentiable, coordinators must stay on explicit dependency injection paths, export/screenshot coordinators must stay on worker lifecycle routes, render degradation state must stay projected in SessionState.render_runtime through a typed status-panel subscription flow, clean bootstrap/headless mainline paths must stay within the configured compatibility budget, public plugin SDK examples must remain loader-compatible, render telemetry must remain recorded as bounded structured state transitions + operation spans + sampling counters + backend-specific performance telemetry, and screenshot/importer fidelity baselines must stay reproducible from checked-in fixtures
- full validation: `pytest --cov=src/robot_sim --cov-report=term-missing --cov-report=json:coverage.json -q` with `fail_under = 80` + `python scripts/verify_partition_coverage.py --coverage-json coverage.json`
- gui smoke: `python scripts/verify_runtime_baseline.py --mode gui` + `python scripts/verify_release_environment.py --mode gui` + `pytest tests/gui -q` on Ubuntu 22.04 with `PySide6>=6.5` installed; pytest defaults `QT_QPA_PLATFORM=offscreen` unless `ROBOT_SIM_PYTEST_FORCE_GUI_DISPLAY=1` is set
- quality contracts: `python scripts/verify_quality_contracts.py` + `python scripts/verify_module_governance.py` + `python scripts/verify_benchmark_matrix.py`
=======
- quick quality: `ruff check src tests` + targeted `mypy` + `pytest tests/unit tests/regression -q`
- full validation: `pytest --cov=src/robot_sim --cov-report=term-missing -q` with `fail_under = 80`
- gui smoke: `pytest tests/gui -q` on Ubuntu 22.04 with `PySide6>=6.5` installed
- quality contracts: `python scripts/verify_quality_contracts.py`
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
- contract regeneration: `python scripts/regenerate_quality_contracts.py` + `git diff --exit-code -- docs`
