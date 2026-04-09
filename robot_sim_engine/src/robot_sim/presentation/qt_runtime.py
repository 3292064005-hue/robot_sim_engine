from __future__ import annotations

import os
from typing import Any

if not str(os.environ.get('QT_QPA_PLATFORM', '') or '').strip() and not str(os.environ.get('DISPLAY', '') or '').strip() and not str(os.environ.get('WAYLAND_DISPLAY', '') or '').strip():
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'


class _QtUnavailableBase:
    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError('PySide6 is required for GUI runtime construction.')


class _QtUnavailableApplication:
    @staticmethod
    def instance():
        return None

    def __init__(self, *args, **kwargs) -> None:
        raise RuntimeError('PySide6 is required for QApplication construction.')


class _QtUnavailableDialog:
    @staticmethod
    def getOpenFileName(*args, **kwargs):
        raise RuntimeError('PySide6 is required for file-dialog operations.')


class _QtUnavailableMessageBox:
    @staticmethod
    def critical(*args, **kwargs):
        raise RuntimeError('PySide6 is required for message-box operations.')


try:
    from PySide6.QtCore import Qt as Qt
    from PySide6.QtCore import Signal as Signal
    from PySide6.QtWidgets import QApplication as QApplication
    from PySide6.QtWidgets import QCheckBox as QCheckBox
    from PySide6.QtWidgets import QComboBox as QComboBox
    from PySide6.QtWidgets import QDialog as QDialog
    from PySide6.QtWidgets import QDialogButtonBox as QDialogButtonBox
    from PySide6.QtWidgets import QDoubleSpinBox as QDoubleSpinBox
    from PySide6.QtWidgets import QFileDialog as QFileDialog
    from PySide6.QtWidgets import QFormLayout as QFormLayout
    from PySide6.QtWidgets import QGroupBox as QGroupBox
    from PySide6.QtWidgets import QHBoxLayout as QHBoxLayout
    from PySide6.QtWidgets import QLabel as QLabel
    from PySide6.QtWidgets import QLineEdit as QLineEdit
    from PySide6.QtWidgets import QMainWindow as QMainWindow
    from PySide6.QtWidgets import QMessageBox as QMessageBox
    from PySide6.QtWidgets import QPushButton as QPushButton
    from PySide6.QtWidgets import QSlider as QSlider
    from PySide6.QtWidgets import QSpinBox as QSpinBox
    from PySide6.QtWidgets import QSplitter as QSplitter
    from PySide6.QtWidgets import QTabWidget as QTabWidget
    from PySide6.QtWidgets import QTableView as QTableView
    from PySide6.QtWidgets import QTextEdit as QTextEdit
    from PySide6.QtWidgets import QVBoxLayout as QVBoxLayout
    from PySide6.QtWidgets import QWidget as QWidget
except ImportError:  # pragma: no cover
    QT_RUNTIME_AVAILABLE = False
    Qt: Any = type('_QtUnavailableNamespace', (), {'Horizontal': 1, 'Vertical': 2})()

    def Signal(*args, **kwargs):  # type: ignore
        return None
    QWidget = type('QWidget', (_QtUnavailableBase,), {})
    QMainWindow = type('QMainWindow', (_QtUnavailableBase,), {})
    QSplitter = type('QSplitter', (_QtUnavailableBase,), {})
    QVBoxLayout = type('QVBoxLayout', (_QtUnavailableBase,), {})
    QHBoxLayout = type('QHBoxLayout', (_QtUnavailableBase,), {})
    QFormLayout = type('QFormLayout', (_QtUnavailableBase,), {})
    QTabWidget = type('QTabWidget', (_QtUnavailableBase,), {})
    QGroupBox = type('QGroupBox', (_QtUnavailableBase,), {})
    QDialog = type('QDialog', (_QtUnavailableBase,), {'Ok': 1, 'Cancel': 2})
    QDialogButtonBox = type('QDialogButtonBox', (_QtUnavailableBase,), {'Ok': 1, 'Cancel': 2})
    QLabel = type('QLabel', (_QtUnavailableBase,), {})
    QTextEdit = type('QTextEdit', (_QtUnavailableBase,), {})
    QPushButton = type('QPushButton', (_QtUnavailableBase,), {})
    QCheckBox = type('QCheckBox', (_QtUnavailableBase,), {})
    QComboBox = type('QComboBox', (_QtUnavailableBase,), {})
    QDoubleSpinBox = type('QDoubleSpinBox', (_QtUnavailableBase,), {})
    QSpinBox = type('QSpinBox', (_QtUnavailableBase,), {})
    QSlider = type('QSlider', (_QtUnavailableBase,), {})
    QLineEdit = type('QLineEdit', (_QtUnavailableBase,), {})
    QTableView = type('QTableView', (_QtUnavailableBase,), {})
    QFileDialog = _QtUnavailableDialog
    QMessageBox = _QtUnavailableMessageBox
    QApplication = _QtUnavailableApplication
else:
    QT_RUNTIME_AVAILABLE = True


def require_qt_runtime(feature: str) -> None:
    """Raise a deterministic error when a stable GUI surface is constructed without Qt.

    Args:
        feature: Human-readable GUI surface name.

    Raises:
        RuntimeError: If the real Qt runtime is unavailable.
    """
    if QT_RUNTIME_AVAILABLE:
        return
    raise RuntimeError(f'{feature} requires PySide6 GUI runtime.')
