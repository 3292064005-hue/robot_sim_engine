from __future__ import annotations

from robot_sim.presentation.qt_runtime import QFormLayout, QGroupBox, QLabel, QTextEdit, QVBoxLayout, QWidget, require_qt_runtime
from robot_sim.presentation.render_telemetry_state import RenderTelemetryPanelState


class DiagnosticsPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        require_qt_runtime('DiagnosticsPanel')
        super().__init__(parent)
        layout = QVBoxLayout(self)
        group = QGroupBox('诊断 / 质量')
        form = QFormLayout(group)
        self.labels = {}
        for key, title in [
            ('traj_mode', '轨迹模式'),
            ('traj_feasible', '可行性'),
            ('traj_reasons', '不可行原因'),
            ('path_length', '末端路径长度'),
            ('jerk_proxy', 'Jerk 代理'),
            ('bench_success', 'Benchmark 成功率'),
            ('bench_p95', 'Benchmark P95 ms'),
            ('bench_restarts', '平均重试次数'),
            ('render_event_count', 'Render 事件数'),
            ('render_latest_event', '最新 Render 事件'),
            ('render_latest_severity', '最新事件级别'),
            ('render_span_count', 'Render Span 数'),
            ('render_latest_span', '最新 Span'),
            ('render_counter_count', 'Sampling Counter 数'),
            ('render_latest_counter', '最新 Counter'),
            ('render_backend_perf', 'Backend 性能摘要'),
            ('render_latency_buckets', 'Latency Buckets'),
            ('render_percentiles', 'Duration Percentiles'),
            ('render_rolling_window', 'Rolling Window'),
            ('render_live_counters', 'Live Counters'),
            ('render_timeline_summary', 'Diagnostics Timeline'),
        ]:
            label = QLabel('-')
            if hasattr(label, 'setWordWrap'):
                label.setWordWrap(True)
            self.labels[key] = label
            form.addRow(title, label)
        layout.addWidget(group)

        telemetry_group = QGroupBox('Render Telemetry')
        telemetry_layout = QVBoxLayout(telemetry_group)
        self.telemetry_log = QTextEdit()
        self.telemetry_log.setReadOnly(True)
        telemetry_layout.addWidget(self.telemetry_log)
        layout.addWidget(telemetry_group)

        span_group = QGroupBox('Render Operation Spans')
        span_layout = QVBoxLayout(span_group)
        self.span_log = QTextEdit()
        self.span_log.setReadOnly(True)
        span_layout.addWidget(self.span_log)
        layout.addWidget(span_group)

        counter_group = QGroupBox('Render Sampling Counters')
        counter_layout = QVBoxLayout(counter_group)
        self.counter_log = QTextEdit()
        self.counter_log.setReadOnly(True)
        counter_layout.addWidget(self.counter_log)
        layout.addWidget(counter_group)

        backend_group = QGroupBox('Backend Performance Telemetry')
        backend_layout = QVBoxLayout(backend_group)
        self.backend_perf_log = QTextEdit()
        self.backend_perf_log.setReadOnly(True)
        backend_layout.addWidget(self.backend_perf_log)
        layout.addWidget(backend_group)

        timeline_group = QGroupBox('Diagnostics Timeline')
        timeline_layout = QVBoxLayout(timeline_group)
        self.timeline_log = QTextEdit()
        self.timeline_log.setReadOnly(True)
        timeline_layout.addWidget(self.timeline_log)
        layout.addWidget(timeline_group)

    def set_values(self, **kwargs) -> None:
        for key, value in kwargs.items():
            label = self.labels.get(key)
            if label is not None:
                label.setText(str(value))

    def set_render_telemetry(self, panel_state: RenderTelemetryPanelState) -> None:
        self.set_values(**panel_state.metric_payload)
        sections = {section.section_id: section for section in panel_state.log_sections}
        self.telemetry_log.setPlainText(sections.get('events').body_text if 'events' in sections else panel_state.events_text)
        self.span_log.setPlainText(sections.get('spans').body_text if 'spans' in sections else panel_state.spans_text)
        self.counter_log.setPlainText(sections.get('counters').body_text if 'counters' in sections else panel_state.counters_text)
        self.backend_perf_log.setPlainText(sections.get('backend_performance').body_text if 'backend_performance' in sections else panel_state.backend_perf_text)
        self.timeline_log.setPlainText(sections.get('timeline').body_text if 'timeline' in sections else panel_state.timeline_text)
