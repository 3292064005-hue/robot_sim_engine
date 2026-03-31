from __future__ import annotations
from robot_sim.presentation.models.dh_table_model import DHTableModel

try:
    from PySide6.QtWidgets import (
        QWidget,
        QVBoxLayout,
        QLabel,
        QPushButton,
        QComboBox,
        QHBoxLayout,
        QTableView,
        QGroupBox,
        QFormLayout,
        QDoubleSpinBox,
    )
except Exception:  # pragma: no cover
    QWidget = object  # type: ignore


class RobotConfigPanel(QWidget):  # pragma: no cover - GUI shell
    def __init__(self, robot_names: list[str], parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import (
            QWidget,
            QVBoxLayout,
            QLabel,
            QPushButton,
            QComboBox,
            QHBoxLayout,
            QTableView,
            QGroupBox,
            QFormLayout,
            QDoubleSpinBox,
        )

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("机器人配置"))

        selector_row = QHBoxLayout()
        self.robot_combo = QComboBox()
        self.robot_combo.addItems(robot_names)
        self.load_button = QPushButton("加载")
        self.save_button = QPushButton("保存 YAML")
        selector_row.addWidget(self.robot_combo)
        selector_row.addWidget(self.load_button)
        selector_row.addWidget(self.save_button)
        layout.addLayout(selector_row)

        self.info_label = QLabel("尚未加载机器人")
        layout.addWidget(self.info_label)

        self.table_model = DHTableModel([])
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_view)

        home_group = QGroupBox("Home q")
        self.home_form = QFormLayout(home_group)
        self.home_boxes: list[QDoubleSpinBox] = []
        self.home_row_labels: list[QLabel] = []
        for i in range(8):
            box = QDoubleSpinBox()
            box.setRange(-999.0, 999.0)
            box.setDecimals(6)
            box.setVisible(False)
            label = QLabel(f"q{i}")
            label.setVisible(False)
            self.home_boxes.append(box)
            self.home_row_labels.append(label)
            self.home_form.addRow(label, box)
        layout.addWidget(home_group)

    def set_robot_spec(self, spec) -> None:
        desc = f" | {spec.description}" if getattr(spec, 'description', '') else ""
        self.info_label.setText(f"{spec.label} | DOF = {spec.dof}{desc}")
        self.table_model.set_rows(list(spec.dh_rows))
        for i, box in enumerate(self.home_boxes):
            visible = i < spec.dof
            box.setVisible(visible)
            self.home_row_labels[i].setVisible(visible)
            if visible:
                box.setValue(float(spec.home_q[i]))

    def edited_home_q(self):
        rows = self.table_model.to_rows()
        return [self.home_boxes[i].value() for i in range(len(rows))]

    def edited_rows(self):
        return list(self.table_model.to_rows())
