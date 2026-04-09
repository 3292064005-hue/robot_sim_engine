from __future__ import annotations

from robot_sim.presentation.qt_runtime import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    require_qt_runtime,
)
from robot_sim.presentation.scene_ui_support import (
    format_allowed_collision_pairs,
    format_vector,
    parse_allowed_collision_pairs_text,
    parse_vector_text,
)


class SceneEditorDialog(QDialog):  # pragma: no cover - GUI shell
    """Structured stable editor for the bounded planning-scene surface.

    The dialog remains intentionally small, but it now supports the stable primitive set
    consumed by ``SceneAuthorityService``: box, sphere, cylinder, plus attached-object
    metadata and explicit ACM pair editing.
    """

    def __init__(self, *, initial: dict[str, object], parent=None) -> None:
        require_qt_runtime('SceneEditorDialog')
        super().__init__(parent)
        self.setWindowTitle('场景编辑')
        root = QVBoxLayout(self)

        intro = QLabel('编辑稳定场景能力：box / sphere / cylinder + attached object + allowed collision pairs')
        if hasattr(intro, 'setWordWrap'):
            intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.object_id_edit = QLineEdit(str(initial.get('object_id', 'obstacle') or 'obstacle'))
        self.center_edit = QLineEdit(format_vector(initial.get('center', (0.3, 0.0, 0.2))))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(['box', 'sphere', 'cylinder'])
        initial_shape = str(initial.get('shape', 'box') or 'box').strip().lower()
        if initial_shape in {'box', 'sphere', 'cylinder'}:
            self.shape_combo.setCurrentText(initial_shape)
        self.size_edit = QLineEdit(format_vector(initial.get('size', (0.2, 0.2, 0.2))))
        self.radius_edit = QLineEdit(str(initial.get('radius', 0.1) or 0.1))
        self.height_edit = QLineEdit(str(initial.get('height', 0.2) or 0.2))
        self.attach_link_edit = QLineEdit(str(initial.get('attach_link', '') or ''))
        self.attached_chk = QCheckBox('作为 attached object 写入 scene')
        self.attached_chk.setChecked(bool(initial.get('attached', False) or initial.get('attach_link')))
        form.addRow('对象标识', self.object_id_edit)
        form.addRow('中心 xyz', self.center_edit)
        form.addRow('形状', self.shape_combo)
        form.addRow('box 尺寸 xyz', self.size_edit)
        form.addRow('sphere/cylinder 半径', self.radius_edit)
        form.addRow('cylinder 高度', self.height_edit)
        form.addRow('附着 link/tool', self.attach_link_edit)
        root.addLayout(form)

        toggle_row = QHBoxLayout()
        self.replace_existing_chk = QCheckBox('若标识重复则替换现有对象')
        self.replace_existing_chk.setChecked(bool(initial.get('replace_existing', False)))
        self.clear_pairs_chk = QCheckBox('提交前清空 allowed collision pairs')
        self.clear_pairs_chk.setChecked(bool(initial.get('clear_allowed_collision_pairs', False)))
        toggle_row.addWidget(self.replace_existing_chk)
        toggle_row.addWidget(self.clear_pairs_chk)
        toggle_row.addWidget(self.attached_chk)
        root.addLayout(toggle_row)

        self.allowed_pairs_edit = QTextEdit()
        if hasattr(self.allowed_pairs_edit, 'setPlaceholderText'):
            self.allowed_pairs_edit.setPlaceholderText('每行一对，例如：\nlink_1, obstacle\nfixture, tool')
        self.allowed_pairs_edit.setPlainText(
            format_allowed_collision_pairs(initial.get('allowed_collision_pairs', ()) or ())
        )
        root.addWidget(QLabel('Allowed collision pairs'))
        root.addWidget(self.allowed_pairs_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def build_request(self) -> dict[str, object]:
        """Build the canonical scene-editor payload from widget state.

        Returns:
            dict[str, object]: Structured request compatible with ``SceneAuthorityService``.

        Raises:
            ValueError: If vector, pair, or primitive fields are malformed.
        """
        center = parse_vector_text(self.center_edit.text(), field_name='center')
        shape = str(self.shape_combo.currentText() or 'box').strip().lower() or 'box'
        pairs = parse_allowed_collision_pairs_text(self.allowed_pairs_edit.toPlainText())
        payload = {
            'object_id': str(self.object_id_edit.text() or 'obstacle').strip() or 'obstacle',
            'center': center,
            'shape': shape,
            'replace_existing': bool(self.replace_existing_chk.isChecked()),
            'attached': bool(self.attached_chk.isChecked()),
            'attach_link': str(self.attach_link_edit.text() or '').strip(),
            'allowed_collision_pairs': pairs,
            'clear_allowed_collision_pairs': bool(self.clear_pairs_chk.isChecked()),
            'metadata': {},
        }
        if shape == 'box':
            size = parse_vector_text(self.size_edit.text(), field_name='size')
            if any(value <= 0.0 for value in size):
                raise ValueError('scene obstacle size must be strictly positive')
            payload['size'] = size
        else:
            try:
                radius = float(self.radius_edit.text())
            except ValueError as exc:
                raise ValueError('scene obstacle radius must be numeric') from exc
            if radius <= 0.0:
                raise ValueError('scene obstacle radius must be strictly positive')
            payload['radius'] = radius
            if shape == 'cylinder':
                try:
                    height = float(self.height_edit.text())
                except ValueError as exc:
                    raise ValueError('scene obstacle height must be numeric') from exc
                if height <= 0.0:
                    raise ValueError('scene obstacle height must be strictly positive')
                payload['height'] = height
        return payload

    @classmethod
    def get_request(cls, *, initial: dict[str, object], parent=None) -> dict[str, object] | None:
        """Open the structured editor and return the submitted request.

        Args:
            initial: Initial payload shown in the editor.
            parent: Optional Qt parent widget.

        Returns:
            dict[str, object] | None: Structured request on acceptance, otherwise ``None``.

        Raises:
            RuntimeError: If the Qt runtime is unavailable.
            ValueError: Propagates field validation failures from ``build_request``.
        """
        dialog = cls(initial=initial, parent=parent)
        accepted = bool(dialog.exec())
        if not accepted:
            return None
        return dialog.build_request()
