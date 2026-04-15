from __future__ import annotations

from threading import Timer
from typing import Any


class _BoundSignal:
    def __init__(self) -> None:
        self._callbacks: list[object] = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs) -> None:
        for callback in tuple(self._callbacks):
            callback(*args, **kwargs)


class Signal:
    """Minimal descriptor-compatible Qt signal shim used only for non-GUI tests."""

    def __init__(self, *args, **kwargs) -> None:
        self._name = ''

    def __set_name__(self, owner, name: str) -> None:
        self._name = f'__qt_signal_{name}'

    def __get__(self, instance, owner):
        if instance is None:
            return self
        bound = instance.__dict__.get(self._name)
        if bound is None:
            bound = _BoundSignal()
            instance.__dict__[self._name] = bound
        return bound


class QObject:
    def __init__(self, parent=None, *args, **kwargs) -> None:
        self._parent = parent

    def moveToThread(self, _thread) -> None:
        return None

    def deleteLater(self) -> None:
        return None


def Slot(*args, **kwargs):
    def _decorator(fn):
        return fn
    return _decorator


class _ThreadHandle:
    @staticmethod
    def loopLevel() -> int:
        return 0


class QCoreApplication:
    _instance: "QCoreApplication | None" = None

    def __init__(self, *args, **kwargs) -> None:
        QCoreApplication._instance = self
        self._robot_sim_headless_helper = True

    @staticmethod
    def instance() -> "QCoreApplication | None":
        return QCoreApplication._instance

    def thread(self):
        return _ThreadHandle()


class QThread(QObject):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.started = _BoundSignal()
        self._running = False

    def start(self) -> None:
        self._running = True
        self.started.emit()

    def quit(self) -> None:
        self._running = False

    def wait(self, timeout: int | None = None) -> bool:
        del timeout
        return True


class QTimer(QObject):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.timeout = _BoundSignal()
        self._timer: Timer | None = None
        self._active = False
        self._single_shot = False

    def setSingleShot(self, single_shot: bool) -> None:
        self._single_shot = bool(single_shot)

    def isActive(self) -> bool:
        return self._active

    def start(self, interval_ms: int) -> None:
        self.stop()
        self._active = True
        self._timer = Timer(max(float(interval_ms), 0.0) / 1000.0, self._emit_timeout)
        self._timer.daemon = True
        self._timer.start()

    def _emit_timeout(self) -> None:
        self._active = False
        self.timeout.emit()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        self._active = False


class QModelIndex:
    def __init__(self, row: int = -1, column: int = -1, valid: bool = False) -> None:
        self._row = int(row)
        self._column = int(column)
        self._valid = bool(valid)

    def row(self) -> int:
        return self._row

    def column(self) -> int:
        return self._column

    def isValid(self) -> bool:
        return self._valid


class _AbstractItemModel(QObject):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.dataChanged = _BoundSignal()

    def beginResetModel(self) -> None:
        return None

    def endResetModel(self) -> None:
        return None


class QAbstractTableModel(_AbstractItemModel):
    pass


class QAbstractListModel(_AbstractItemModel):
    pass


class _QtNamespace:
    Horizontal = 1
    Vertical = 2
    DisplayRole = 0
    EditRole = 2
    UserRole = 256
    NoItemFlags = 0
    ItemIsSelectable = 1 << 0
    ItemIsEnabled = 1 << 1
    ItemIsEditable = 1 << 2


Qt: Any = _QtNamespace()


class QApplication(QCoreApplication):
    _instance: 'QApplication | None' = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        QApplication._instance = self
        self._platform_name = 'offscreen'

    @staticmethod
    def instance() -> 'QApplication | None':
        return QApplication._instance

    def platformName(self) -> str:
        return self._platform_name


class QWidget:
    def __init__(self, parent=None, *args, **kwargs) -> None:
        self._parent = parent
        self._layout = None
        self._window_title = ''
        self._visible = False
        self._enabled = True
        self._size = (0, 0)
        self._style_sheet = ''
        self._tool_tip = ''

    def setLayout(self, layout) -> None:
        self._layout = layout

    def layout(self):
        return self._layout

    def setWindowTitle(self, title: str) -> None:
        self._window_title = str(title)

    def resize(self, width: int, height: int) -> None:
        self._size = (int(width), int(height))

    def show(self) -> None:
        self._visible = True

    def close(self) -> None:
        self._visible = False

    def setVisible(self, visible: bool) -> None:
        self._visible = bool(visible)

    def isVisible(self) -> bool:
        return self._visible

    def setEnabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    def setStyleSheet(self, style: str) -> None:
        self._style_sheet = str(style)

    def styleSheet(self) -> str:
        return self._style_sheet

    def setToolTip(self, text: str) -> None:
        self._tool_tip = str(text)

    def toolTip(self) -> str:
        return self._tool_tip


class QMainWindow(QWidget):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._central_widget = None

    def setCentralWidget(self, widget) -> None:
        self._central_widget = widget


class _BaseLayout:
    def __init__(self, parent=None, *args, **kwargs) -> None:
        self.parent = parent
        self.children: list[object] = []
        if isinstance(parent, QWidget):
            parent.setLayout(self)

    def addWidget(self, widget) -> None:
        self.children.append(widget)

    def addLayout(self, layout) -> None:
        self.children.append(layout)

    def addStretch(self, stretch: int = 0) -> None:
        self.children.append(('stretch', int(stretch)))


class QVBoxLayout(_BaseLayout):
    pass


class QHBoxLayout(_BaseLayout):
    pass


class QFormLayout(_BaseLayout):
    def addRow(self, *widgets) -> None:
        self.children.append(tuple(widgets))


class QGroupBox(QWidget):
    pass


class QLabel(QWidget):
    def __init__(self, text: str = '', parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._text = str(text)
        self._word_wrap = False

    def setText(self, text: str) -> None:
        self._text = str(text)

    def text(self) -> str:
        return self._text

    def setWordWrap(self, enabled: bool) -> None:
        self._word_wrap = bool(enabled)


class QTextEdit(QWidget):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._text = ''
        self._placeholder = ''
        self._readonly = False

    def setReadOnly(self, value: bool) -> None:
        self._readonly = bool(value)

    def append(self, text: str) -> None:
        self._text = f'{self._text}\n{text}'.strip()

    def clear(self) -> None:
        self._text = ''

    def setPlainText(self, text: str) -> None:
        self._text = str(text)

    def toPlainText(self) -> str:
        return self._text

    def setPlaceholderText(self, text: str) -> None:
        self._placeholder = str(text)


class QPushButton(QWidget):
    def __init__(self, text: str = '', parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._text = str(text)
        self.clicked = _BoundSignal()


class QCheckBox(QWidget):
    def __init__(self, text: str = '', parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._text = str(text)
        self._checked = False
        self.toggled = _BoundSignal()

    def setChecked(self, checked: bool) -> None:
        self._checked = bool(checked)

    def isChecked(self) -> bool:
        return self._checked


class QComboBox(QWidget):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._items: list[tuple[str, object]] = []
        self._current_index = -1
        self.currentTextChanged = _BoundSignal()

    def addItems(self, items) -> None:
        for item in items:
            self.addItem(str(item), str(item))

    def addItem(self, item: str, user_data: object = None) -> None:
        text = str(item)
        self._items.append((text, text if user_data is None else user_data))
        if self._current_index < 0:
            self._current_index = 0

    def clear(self) -> None:
        self._items = []
        self._current_index = -1

    def currentText(self) -> str:
        return self._items[self._current_index][0] if self._current_index >= 0 else ''

    def currentData(self):
        return self._items[self._current_index][1] if self._current_index >= 0 else None

    def setCurrentText(self, text: str) -> None:
        target = str(text)
        idx = self.findText(target)
        if idx >= 0:
            self._current_index = idx
        self.currentTextChanged.emit(self.currentText())

    def setCurrentIndex(self, index: int) -> None:
        if 0 <= int(index) < len(self._items):
            self._current_index = int(index)
            self.currentTextChanged.emit(self.currentText())

    def findText(self, text: str) -> int:
        target = str(text)
        for idx, (item, _data) in enumerate(self._items):
            if item == target:
                return idx
        return -1


class _SpinBoxBase(QWidget):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._value = 0
        self._range = (0, 0)
        self.valueChanged = _BoundSignal()

    def setRange(self, minimum, maximum) -> None:
        self._range = (minimum, maximum)

    def setValue(self, value) -> None:
        self._value = value

    def value(self):
        return self._value

    def setSingleStep(self, value) -> None:
        self._single_step = value

    def setDecimals(self, value: int) -> None:
        self._decimals = int(value)


class QDoubleSpinBox(_SpinBoxBase):
    pass


class QSpinBox(_SpinBoxBase):
    pass


class QSlider(QWidget):
    def __init__(self, orientation=None, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.orientation = orientation
        self._range = (0, 0)
        self._value = 0
        self.valueChanged = _BoundSignal()
        self._signals_blocked = False

    def setRange(self, minimum: int, maximum: int) -> None:
        self._range = (int(minimum), int(maximum))

    def setValue(self, value: int) -> None:
        self._value = int(value)
        if not self._signals_blocked:
            self.valueChanged.emit(self._value)

    def value(self) -> int:
        return self._value

    def blockSignals(self, blocked: bool) -> None:
        self._signals_blocked = bool(blocked)


class QTabWidget(QWidget):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.tabs: list[tuple[object, str]] = []

    def addTab(self, widget, label: str) -> None:
        self.tabs.append((widget, str(label)))


class QSplitter(QWidget):
    def __init__(self, orientation=None, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.orientation = orientation
        self.widgets: list[object] = []
        self.sizes: list[int] = []

    def addWidget(self, widget) -> None:
        self.widgets.append(widget)

    def setSizes(self, sizes) -> None:
        self.sizes = [int(value) for value in sizes]


class QLineEdit(QWidget):
    def __init__(self, text: str = '', parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._text = str(text)

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = str(text)


class QDialog(QWidget):
    Accepted = 1
    Rejected = 0

    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._dialog_result = self.Rejected

    def exec(self) -> int:
        return int(self._dialog_result)

    def accept(self) -> None:
        self._dialog_result = self.Accepted

    def reject(self) -> None:
        self._dialog_result = self.Rejected


class QDialogButtonBox(QWidget):
    Ok = 1
    Cancel = 2

    def __init__(self, buttons=None, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self.buttons = buttons
        self.accepted = _BoundSignal()
        self.rejected = _BoundSignal()


class _HeaderShim:
    def setStretchLastSection(self, enabled: bool) -> None:
        self._stretch_last = bool(enabled)


class QTableView(QWidget):
    def __init__(self, parent=None, *args, **kwargs) -> None:
        super().__init__(parent, *args, **kwargs)
        self._model = None
        self._header = _HeaderShim()

    def setModel(self, model) -> None:
        self._model = model

    def horizontalHeader(self):
        return self._header


class QFileDialog:
    @staticmethod
    def getOpenFileName(*args, **kwargs):
        return '', ''


def real_pyside6_available() -> bool:
    """Return whether a real ``PySide6`` distribution is importable from disk."""
    import importlib.machinery

    return importlib.machinery.PathFinder.find_spec('PySide6') is not None


def install_pyside6_test_shims() -> bool:
    """Install a minimal in-memory ``PySide6`` package for non-GUI tests.

    Returns:
        bool: ``True`` when shim modules were installed, ``False`` when a real
            ``PySide6`` distribution is already available or shim modules were
            already present.

    Boundary behavior:
        The helper only mutates ``sys.modules`` and never shadows a real
        ``PySide6`` installation discovered by the import system.
    """
    import sys
    from importlib.machinery import ModuleSpec
    from types import ModuleType

    if real_pyside6_available():
        return False
    existing = sys.modules.get('PySide6')
    if existing is not None:
        return bool(getattr(existing, '__robot_sim_test_shim__', False))

    package = ModuleType('PySide6')
    qtcore = ModuleType('PySide6.QtCore')
    qtwidgets = ModuleType('PySide6.QtWidgets')
    package.__path__ = []
    package.__package__ = 'PySide6'
    package.__spec__ = ModuleSpec('PySide6', loader=None, is_package=True)
    package.__robot_sim_test_shim__ = True
    qtcore.__package__ = 'PySide6'
    qtcore.__spec__ = ModuleSpec('PySide6.QtCore', loader=None, is_package=False)
    qtcore.__robot_sim_test_shim__ = True
    qtwidgets.__package__ = 'PySide6'
    qtwidgets.__spec__ = ModuleSpec('PySide6.QtWidgets', loader=None, is_package=False)
    qtwidgets.__robot_sim_test_shim__ = True

    qtcore.QAbstractListModel = QAbstractListModel
    qtcore.QAbstractTableModel = QAbstractTableModel
    qtcore.QCoreApplication = QCoreApplication
    qtcore.QModelIndex = QModelIndex
    qtcore.QObject = QObject
    qtcore.QThread = QThread
    qtcore.QTimer = QTimer
    qtcore.Qt = Qt
    qtcore.Signal = Signal
    qtcore.Slot = Slot
    qtwidgets.QApplication = QApplication
    qtwidgets.QCheckBox = QCheckBox
    qtwidgets.QComboBox = QComboBox
    qtwidgets.QDialog = QDialog
    qtwidgets.QDialogButtonBox = QDialogButtonBox
    qtwidgets.QDoubleSpinBox = QDoubleSpinBox
    qtwidgets.QFileDialog = QFileDialog
    qtwidgets.QFormLayout = QFormLayout
    qtwidgets.QGroupBox = QGroupBox
    qtwidgets.QHBoxLayout = QHBoxLayout
    qtwidgets.QLabel = QLabel
    qtwidgets.QLineEdit = QLineEdit
    qtwidgets.QMainWindow = QMainWindow
    qtwidgets.QMessageBox = QMessageBox
    qtwidgets.QPushButton = QPushButton
    qtwidgets.QSlider = QSlider
    qtwidgets.QSpinBox = QSpinBox
    qtwidgets.QSplitter = QSplitter
    qtwidgets.QTabWidget = QTabWidget
    qtwidgets.QTableView = QTableView
    qtwidgets.QTextEdit = QTextEdit
    qtwidgets.QVBoxLayout = QVBoxLayout
    qtwidgets.QWidget = QWidget

    package.QtCore = qtcore
    package.QtWidgets = qtwidgets

    sys.modules['PySide6'] = package
    sys.modules['PySide6.QtCore'] = qtcore
    sys.modules['PySide6.QtWidgets'] = qtwidgets
    return True


def uninstall_pyside6_test_shims() -> bool:
    """Remove previously installed in-memory ``PySide6`` shim modules.

    Returns:
        bool: ``True`` when shim modules were removed.
    """
    import sys

    removed = False
    for name in ('PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6'):
        module = sys.modules.get(name)
        if module is not None and getattr(module, '__robot_sim_test_shim__', False):
            sys.modules.pop(name, None)
            removed = True
    return removed


class QMessageBox:
    @staticmethod
    def critical(*args, **kwargs):
        return None


__all__ = [
    'QAbstractListModel',
    'QAbstractTableModel',
    'QApplication',
    'QCoreApplication',
    'QModelIndex',
    'QObject',
    'QThread',
    'QTimer',
    'QCheckBox',
    'QComboBox',
    'QDialog',
    'QDialogButtonBox',
    'QDoubleSpinBox',
    'QFileDialog',
    'QFormLayout',
    'QGroupBox',
    'QHBoxLayout',
    'QLabel',
    'QLineEdit',
    'QMainWindow',
    'QMessageBox',
    'QPushButton',
    'QSlider',
    'QSpinBox',
    'QSplitter',
    'QTabWidget',
    'QTableView',
    'QTextEdit',
    'QVBoxLayout',
    'QWidget',
    'Qt',
    'Signal',
    'Slot',
    'install_pyside6_test_shims',
    'real_pyside6_available',
    'uninstall_pyside6_test_shims',
]
