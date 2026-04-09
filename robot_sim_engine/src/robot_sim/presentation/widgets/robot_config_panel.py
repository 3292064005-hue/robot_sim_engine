from __future__ import annotations

from robot_sim.presentation.models.dh_table_model import DHTableModel
from robot_sim.presentation.qt_runtime import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
    require_qt_runtime,
)


class RobotConfigPanel(QWidget):  # pragma: no cover - GUI shell
    """Robot configuration panel.

    The panel now exposes both the canonical robot library selector and a stable importer
    surface for YAML / URDF / plugin-backed robot sources. Importer metadata is supplied
    by the registry so file filters and labels stay configuration-driven instead of being
    hard-coded in the widget.
    """

    AUTO_IMPORTER_ID = 'auto'

    def __init__(self, robot_entries, importer_entries=None, parent=None):
        require_qt_runtime('RobotConfigPanel')
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("机器人配置"))

        selector_row = QHBoxLayout()
        self.robot_combo = QComboBox()
        self.load_button = QPushButton("加载")
        self.save_button = QPushButton("保存 YAML")
        selector_row.addWidget(self.robot_combo)
        selector_row.addWidget(self.load_button)
        selector_row.addWidget(self.save_button)
        layout.addLayout(selector_row)

        import_row = QHBoxLayout()
        self.importer_combo = QComboBox()
        self.import_button = QPushButton("导入机器人")
        import_row.addWidget(self.importer_combo)
        import_row.addWidget(self.import_button)
        layout.addLayout(import_row)

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
        layout.addWidget(home_group)

        self._importer_entries = []
        self.set_robot_entries(robot_entries)
        self.set_importer_entries(importer_entries or [])

    def set_robot_entries(self, robot_entries, *, selected_name: str | None = None) -> None:
        """Refresh the robot selector while preserving a target selection when possible."""
        previous_name = selected_name if selected_name is not None else self.selected_robot_name()
        self.robot_combo.clear()
        selected_index = -1
        for index, entry in enumerate(robot_entries):
            if hasattr(entry, "label") and hasattr(entry, "name"):
                label = str(entry.label)
                if getattr(entry, "dof", None) is not None:
                    label = f"{label} ({int(entry.dof)} DOF)"
                self.robot_combo.addItem(label, str(entry.name))
                if str(entry.name) == str(previous_name):
                    selected_index = index
            else:
                value = str(entry)
                self.robot_combo.addItem(value, value)
                if value == str(previous_name):
                    selected_index = index
        if selected_index >= 0:
            self.robot_combo.setCurrentIndex(selected_index)

    def set_importer_entries(self, importer_entries) -> None:
        """Refresh importer choices exposed by the stable robot-import UI."""
        self._importer_entries = list(importer_entries)
        self.importer_combo.clear()
        self.importer_combo.addItem("自动识别", self.AUTO_IMPORTER_ID)
        for entry in self._importer_entries:
            metadata = dict(getattr(entry, 'metadata', {}) or {})
            source_format = str(metadata.get('source_format', '') or '').strip()
            fidelity = str(metadata.get('fidelity', '') or '').strip()
            label = str(metadata.get('display_name', '') or getattr(entry, 'importer_id', 'importer'))
            parts = [label]
            if source_format:
                parts.append(source_format.upper())
            if fidelity:
                parts.append(fidelity)
            self.importer_combo.addItem(' | '.join(parts), str(getattr(entry, 'importer_id', '')))
        self.import_button.setEnabled(bool(self._importer_entries))
        self.importer_combo.setEnabled(bool(self._importer_entries))

    def importer_entries(self):
        """Return the active importer descriptors backing the import selector."""
        return tuple(self._importer_entries)

    def selected_robot_name(self) -> str:
        data = self.robot_combo.currentData()
        return str(data if data is not None else self.robot_combo.currentText())

    def selected_importer_id(self) -> str | None:
        """Return the importer override selected in the UI.

        Returns ``None`` when the panel is configured for automatic importer resolution.
        """
        data = self.importer_combo.currentData()
        value = str(data if data is not None else '').strip()
        return None if value in {'', self.AUTO_IMPORTER_ID} else value

    def _ensure_home_boxes(self, dof: int) -> None:
        while len(self.home_boxes) < dof:
            idx = len(self.home_boxes)
            box = QDoubleSpinBox()
            box.setRange(-999.0, 999.0)
            box.setDecimals(6)
            label = QLabel(f"q{idx}")
            self.home_boxes.append(box)
            self.home_row_labels.append(label)
            self.home_form.addRow(label, box)

    def set_robot_spec(self, spec) -> None:
        desc = f" | {spec.description}" if getattr(spec, 'description', '') else ""
        self.info_label.setText(f"{spec.label} | DOF = {spec.dof}{desc}")
        self.table_model.set_rows(list(spec.dh_rows))
        self._ensure_home_boxes(spec.dof)
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
