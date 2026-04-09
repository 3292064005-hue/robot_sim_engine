from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src" / "robot_sim"


def _module_text(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_stable_qt_modules_no_longer_define_local_fallback_shims() -> None:
    targets = (
        "src/robot_sim/presentation/playback_render_scheduler.py",
        "src/robot_sim/presentation/threading/qt_compat.py",
        "src/robot_sim/application/workers/base.py",
        "src/robot_sim/presentation/models/robot_library_model.py",
        "src/robot_sim/presentation/models/dh_table_model.py",
        "src/robot_sim/presentation/models/joint_limit_table_model.py",
    )
    forbidden_markers = (
        "except Exception:  # pragma: no cover",
        "except ImportError:  # pragma: no cover",
        "class QObject:",
        "class QTimer:",
        "QAbstractTableModel = object",
        "QAbstractListModel",
    )
    for path in targets:
        text = _module_text(path)
        for marker in forbidden_markers:
            if marker == "QAbstractListModel":
                continue
            assert marker not in text, f"stable Qt fallback leaked back into {path}"


def test_technical_debt_register_matches_stable_qt_boundary_scope_and_test_injection_scope() -> None:
    text = (PROJECT_ROOT / "docs" / "technical_debt_register.md").read_text(encoding="utf-8")
    assert "稳定 GUI/worker/thread/model 主链已移除本地 Qt fallback/dummy shim" in text
    assert "tests/regression" in text
