---
owner: quality
audience: maintainer
status: generated
source_of_truth: regenerated
generated_by: scripts/regenerate_quality_contracts.py
last_reviewed: 2026-04-18
---
# Module Status

## experimental
- `presentation.experimental.widgets.collision_panel` (disabled_by_profile)
  - owner: `presentation-runtime`
  - stable_ui_surface: `main_window_ui`
  - exit_criteria: `['widget must mount through the stable main window builder without namespace aliases', 'task orchestration must remain on explicit coordinator dependency routes']`
  - required_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke']`
  - promotion_blockers: `['stable UI intentionally hides the panel until promotion criteria are satisfied']`
  - missing_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke']`
  - promotion_ready: `False`
- `presentation.experimental.widgets.export_panel` (disabled_by_profile)
  - owner: `presentation-runtime`
  - stable_ui_surface: `main_window_ui`
  - exit_criteria: `['export widget must project only through stable view contracts', 'background export worker lifecycle must remain intact under GUI smoke']`
  - required_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke']`
  - promotion_blockers: `['stable UI intentionally hides the panel until promotion criteria are satisfied']`
  - missing_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke']`
  - promotion_ready: `False`
- `presentation.experimental.widgets.scene_options_panel` (disabled_by_profile)
  - owner: `presentation-runtime`
  - stable_ui_surface: `main_window_ui`
  - exit_criteria: `['scene options widget must consume typed scene authority summaries only', 'GUI smoke and planning-scene regressions must remain green']`
  - required_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke']`
  - promotion_blockers: `['stable UI intentionally hides the panel until promotion criteria are satisfied']`
  - missing_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke']`
  - promotion_ready: `False`
- `render.experimental.picking` (disabled_by_profile)
  - owner: `render-runtime`
  - stable_ui_surface: `scene_3d_widget`
  - exit_criteria: `['legacy experimental namespace must be removed before stable exposure']`
  - required_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke', 'scene_capture_baseline']`
  - promotion_blockers: `['legacy experimental namespace retained only for compatibility']`
  - missing_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke', 'scene_capture_baseline']`
  - promotion_ready: `False`
- `render.experimental.plot_sync` (disabled_by_profile)
  - owner: `render-runtime`
  - stable_ui_surface: `scene_3d_widget`
  - exit_criteria: `['legacy experimental namespace must be removed before stable exposure']`
  - required_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke', 'scene_capture_baseline']`
  - promotion_blockers: `['legacy experimental namespace retained only for compatibility']`
  - missing_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke', 'scene_capture_baseline']`
  - promotion_ready: `False`
- `render.picking` (disabled_by_profile)
  - owner: `render-runtime`
  - stable_ui_surface: `scene_3d_widget`
  - exit_criteria: `['picking must expose provenance-aware diagnostics in render runtime state', 'GUI smoke must verify picking does not degrade screenshot fallback semantics']`
  - required_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke', 'scene_capture_baseline']`
  - promotion_blockers: `['stable render pipeline still defaults to placeholder/snapshot fallback when live picking is unavailable']`
  - missing_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke', 'scene_capture_baseline']`
  - promotion_ready: `False`
- `render.plot_sync` (disabled_by_profile)
  - owner: `render-runtime`
  - stable_ui_surface: `scene_3d_widget`
  - exit_criteria: `['plot sync must not bypass typed render telemetry projections', 'GUI smoke must validate sync lifecycle under offscreen Qt runtime']`
  - required_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke', 'scene_capture_baseline']`
  - promotion_blockers: `['plot sync remains disabled outside experimental profiles']`
  - missing_quality_gates: `['headless_runtime_baseline', 'unit_and_regression', 'compatibility_budget', 'docs_sync', 'gui_smoke', 'scene_capture_baseline']`
  - promotion_ready: `False`

## stable
- `application.importers.urdf_model_importer` (enabled)
- `application.importers.urdf_skeleton_importer` (enabled)
- `core.collision.capsule_backend` (enabled)
- `core.collision.scene` (enabled)
