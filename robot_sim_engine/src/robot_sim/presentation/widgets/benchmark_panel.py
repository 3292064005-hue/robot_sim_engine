from __future__ import annotations
<<<<<<< HEAD

from robot_sim.presentation.qt_runtime import QLabel, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout, QWidget, require_qt_runtime
=======
try:
    from PySide6.QtWidgets import QWidget
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3


class BenchmarkPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
<<<<<<< HEAD
        require_qt_runtime('BenchmarkPanel')
        super().__init__(parent)
=======
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.run_btn = QPushButton('运行 Benchmark')
        self.export_btn = QPushButton('导出 Benchmark')
        self.summary = QLabel('尚未运行 benchmark')
        top.addWidget(self.run_btn)
        top.addWidget(self.export_btn)
        top.addWidget(self.summary)
        layout.addLayout(top)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

    def set_running(self, running: bool) -> None:
        self.run_btn.setEnabled(not running)
        self.export_btn.setEnabled(not running)

    def set_report(self, report: dict[str, object]) -> None:
        self.summary.setText(
            f"cases={int(report.get('num_cases', 0))} | success={float(report.get('success_rate', 0.0)):.1%}"
        )
        self.log.clear()
        for case in report.get('cases', []):
            self.log.append(
                f"{case.get('name')}: {'OK' if case.get('success') else 'FAIL'} | stop={case.get('stop_reason')} | pos={case.get('final_pos_err', 0.0):.3e} | ori={case.get('final_ori_err', 0.0):.3e}"
            )
