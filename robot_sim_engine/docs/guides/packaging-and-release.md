---
owner: release
audience: maintainer
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Packaging and Release

## 构建命令

```bash
python -m build
python scripts/package_release.py --output dist/release.zip --top-level-dir robot_sim_engine
```

## 打包规则

- 运行/打包真源始终是 `src/robot_sim`
- 构建时自动排除缓存、覆盖率、本地工件
- `scripts/package_release.py` 不再直接从调用方工作区打包；它会先建立一个 writable staging tree，在 staging 中自动再生成并核对 quality contract docs，只有 staged tree 通过校验后才会输出最终 zip
- `configs/` 从单一真源 staging 到包内资源目录
- 最终 package 语义是 artifact/audit bundle，而不是可重建开发工作区镜像

## Release 审计建议

至少执行：

```bash
python scripts/verify_runtime_contracts.py --mode headless --check-packaged-configs
python scripts/verify_compatibility_retirement.py
python scripts/verify_compatibility_budget.py --scenario clean_headless_mainline
python scripts/verify_perf_budget_config.py
python scripts/verify_release_environment.py
python scripts/collect_quality_evidence.py --out artifacts/quality_evidence.json --markdown-out artifacts/quality_evidence.md
```

## Evidence / manifest

- `artifacts/quality_evidence.json`
- `artifacts/quality_evidence.md`
- `artifacts/release_manifest.json`

release review 应同时检查：

- `artifact_ready`
- `environment_ready`
- `release_ready`

而不是只看某一条脚本结果。

## Clean source bundle

- `build_release_zip()` 现在显式排除 `build/`、`exports/`、`artifacts/`、缓存目录、截图与审计残留。
- release/source bundle 只承载可复现源码树，不再把 runtime outputs 混入最终源码交付物。
