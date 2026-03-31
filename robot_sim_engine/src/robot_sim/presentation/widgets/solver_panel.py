from __future__ import annotations
try:
    from PySide6.QtWidgets import QWidget, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class SolverPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QWidget, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton

        layout = QFormLayout(self)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["pinv", "dls"])
        self.max_iters = QSpinBox(); self.max_iters.setRange(1, 5000); self.max_iters.setValue(150)
        self.step_scale = QDoubleSpinBox(); self.step_scale.setRange(0.01, 2.0); self.step_scale.setValue(0.5)
        self.damping = QDoubleSpinBox(); self.damping.setRange(0.0, 10.0); self.damping.setValue(0.05)
        self.pos_tol = QDoubleSpinBox(); self.pos_tol.setDecimals(6); self.pos_tol.setRange(1e-6, 1.0); self.pos_tol.setValue(1e-4)
        self.ori_tol = QDoubleSpinBox(); self.ori_tol.setDecimals(6); self.ori_tol.setRange(1e-6, 10.0); self.ori_tol.setValue(1e-4)
        self.max_step_norm = QDoubleSpinBox(); self.max_step_norm.setRange(1e-4, 10.0); self.max_step_norm.setValue(0.35)
        self.enable_nullspace = QCheckBox(); self.enable_nullspace.setChecked(True)
        self.position_only = QCheckBox(); self.position_only.setChecked(False)
        self.auto_fallback = QCheckBox(); self.auto_fallback.setChecked(True)
        self.traj_duration = QDoubleSpinBox(); self.traj_duration.setRange(0.1, 120.0); self.traj_duration.setValue(3.0)
        self.traj_dt = QDoubleSpinBox(); self.traj_dt.setDecimals(4); self.traj_dt.setRange(0.001, 1.0); self.traj_dt.setValue(0.02)
        self.run_fk_btn = QPushButton("执行 FK")
        self.run_ik_btn = QPushButton("执行 IK")
        self.cancel_btn = QPushButton("停止求解")
        self.plan_btn = QPushButton("生成轨迹")
        self.cancel_btn.setEnabled(False)
        layout.addRow("IK 模式", self.mode_combo)
        layout.addRow("最大迭代", self.max_iters)
        layout.addRow("步长", self.step_scale)
        layout.addRow("阻尼 λ", self.damping)
        layout.addRow("位置容差", self.pos_tol)
        layout.addRow("姿态容差", self.ori_tol)
        layout.addRow("步长限幅", self.max_step_norm)
        layout.addRow("零空间优化", self.enable_nullspace)
        layout.addRow("仅位置 IK", self.position_only)
        layout.addRow("奇异自动切 DLS", self.auto_fallback)
        layout.addRow("轨迹时长 s", self.traj_duration)
        layout.addRow("采样 dt", self.traj_dt)
        layout.addRow(self.run_fk_btn)
        layout.addRow(self.run_ik_btn)
        layout.addRow(self.cancel_btn)
        layout.addRow(self.plan_btn)

    def set_running(self, running: bool) -> None:
        self.cancel_btn.setEnabled(running)
        self.run_ik_btn.setEnabled(not running)
        self.plan_btn.setEnabled(not running)
        self.run_fk_btn.setEnabled(not running)
