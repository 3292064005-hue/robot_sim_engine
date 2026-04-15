from __future__ import annotations

from robot_sim.presentation.qt_runtime import QFormLayout, QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget, require_qt_runtime
from robot_sim.presentation.status_panel_state import RenderRuntimePanelState


_STYLE_BY_SEVERITY = {
    'nominal': 'color: #2e7d32; font-weight: 600;',
    'warning': 'color: #b26a00; font-weight: 600;',
    'critical': 'color: #b00020; font-weight: 700;',
}


class StatusPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        require_qt_runtime('StatusPanel')
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.summary = QLabel("状态：未运行")
        layout.addWidget(self.summary)

        metrics_group = QGroupBox("求解指标")
        metrics_layout = QFormLayout(metrics_group)
        self.metric_labels = {}
        for key, title in [
            ("iterations", "迭代次数"),
            ("pos_err", "位置误差"),
            ("ori_err", "姿态误差"),
            ("cond", "条件数"),
            ("manip", "可操作度"),
            ("dq_norm", "末步长度"),
            ("mode", "实际模式"),
            ("damping", "最终阻尼"),
            ("stop_reason", "停止原因"),
            ("elapsed", "耗时 ms"),
            ("playback", "播放状态"),
            ("scene_3d", "3D 视图"),
            ("plots", "曲线面板"),
            ("screenshot", "截图能力"),
        ]:
            label = QLabel("-")
            self.metric_labels[key] = label
            metrics_layout.addRow(title, label)
        layout.addWidget(metrics_group)

        render_group = QGroupBox('Render 告警')
        render_layout = QFormLayout(render_group)
        self.render_summary = QLabel('Render 状态：等待初始化')
        render_layout.addRow('总体状态', self.render_summary)
        self.render_detail_labels = {}
        for key, title in [
            ('scene_3d', '3D 视图'),
            ('plots', '曲线面板'),
            ('screenshot', '截图能力'),
        ]:
            label = QLabel('-')
            if hasattr(label, 'setWordWrap'):
                label.setWordWrap(True)
            self.render_detail_labels[key] = label
            render_layout.addRow(title, label)
        layout.addWidget(render_group)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def append(self, text: str):
        self.log.append(text)

    def set_metrics(self, **kwargs) -> None:
        for key, value in kwargs.items():
            label = self.metric_labels.get(key)
            if label is not None:
                label.setText(str(value))

    def set_render_runtime(self, panel_state: RenderRuntimePanelState) -> None:
        """Render the structured render-runtime projection into the status widget.

        Args:
            panel_state: Typed render-runtime projection built from shared session state.

        Raises:
            AttributeError: Propagates programmer errors when the caller passes an incompatible
                projection object.

        Boundary behavior:
            Every known capability row is refreshed on each call so stale text/tooltips do not
            survive capability recovery or downgrade transitions.
        """
        self.render_summary.setText(panel_state.summary_text)
        if hasattr(self.render_summary, 'setStyleSheet'):
            self.render_summary.setStyleSheet(_STYLE_BY_SEVERITY.get(panel_state.overall_severity, ''))
        detail_rows = panel_state.detail_rows
        alerts_by_capability = {alert.capability: alert for alert in panel_state.alerts}
        for key, label in self.render_detail_labels.items():
            detail = detail_rows.get(key, '-')
            label.setText(detail)
            alert = alerts_by_capability.get(key)
            if alert is not None and hasattr(label, 'setStyleSheet'):
                label.setStyleSheet(_STYLE_BY_SEVERITY.get(alert.severity, ''))
            if alert is not None and hasattr(label, 'setToolTip'):
                label.setToolTip(alert.tooltip_text)
