from __future__ import annotations

from pathlib import Path

from robot_sim.presentation.main_window_qt_helpers import build_import_dialog_filters
from robot_sim.presentation.qt_runtime import QFileDialog


class MainWindowRequestReadersMixin:
    """View-shell readers that translate stable widget state into typed requests."""

    def _build_solver_kwargs(self) -> dict[str, object]:
        return dict(
            orientation_mode=self.target_panel.orientation_mode.currentText(),
            mode=self.solver_panel.mode_combo.currentText(),
            max_iters=self.solver_panel.max_iters.value(),
            step_scale=self.solver_panel.step_scale.value(),
            damping=self.solver_panel.damping.value(),
            enable_nullspace=self.solver_panel.enable_nullspace.isChecked(),
            position_only=self.solver_panel.position_only.isChecked(),
            pos_tol=self.solver_panel.pos_tol.value(),
            ori_tol=self.solver_panel.ori_tol.value(),
            max_step_norm=self.solver_panel.max_step_norm.value(),
            auto_fallback=self.solver_panel.auto_fallback.isChecked(),
            reachability_precheck=self.solver_panel.reachability_precheck.isChecked(),
            retry_count=self.solver_panel.retry_count.value(),
            joint_limit_weight=self.solver_panel.joint_limit_weight.value(),
            manipulability_weight=self.solver_panel.manipulability_weight.value(),
            orientation_weight=self.solver_panel.orientation_weight.value(),
            adaptive_damping=self.solver_panel.adaptive_damping.isChecked(),
            use_weighted_least_squares=self.solver_panel.weighted_ls.isChecked(),
        )

    def read_selected_robot_name(self) -> str:
        return str(self.robot_panel.selected_robot_name())

    def read_robot_import_request(self) -> dict[str, object] | None:
        importer_entries = list(getattr(self.robot_panel, 'importer_entries', lambda: ())() or ())
        if not importer_entries:
            raise RuntimeError('当前配置未暴露可用的机器人导入器')
        importer_id = self.robot_panel.selected_importer_id()
        filters = build_import_dialog_filters(importer_entries)
        runtime = self._runtime_ops()
        start_dir = runtime.config_root / 'robots'
        if not Path(start_dir).exists():
            start_dir = runtime.project_root
        source, _selected_filter = QFileDialog.getOpenFileName(
            self,
            '导入机器人配置',
            str(start_dir),
            filters,
        )
        source = str(source or '').strip()
        if not source:
            return None
        return {
            'source': source,
            'importer_id': importer_id,
        }

    def read_robot_editor_state(self) -> dict[str, object]:
        return {
            'rows': self.robot_panel.edited_rows(),
            'home_q': self.robot_panel.edited_home_q(),
            'name': self.robot_panel.selected_robot_name(),
        }

    def read_solver_kwargs(self) -> dict[str, object]:
        return self._build_solver_kwargs()

    def read_ik_request(self):
        return self._build_ik_request()

    def read_trajectory_request(self):
        return self._build_trajectory_request()

    def read_playback_launch_options(self) -> dict[str, object]:
        return {
            'speed_multiplier': float(self.playback_panel.speed.value()),
            'loop_enabled': bool(self.playback_panel.loop.isChecked()),
        }
