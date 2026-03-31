from __future__ import annotations
import sys
from robot_sim.app.bootstrap import bootstrap

def main() -> int:
    root = bootstrap()
    try:
        from PySide6.QtWidgets import QApplication
    except Exception as exc:
        print("PySide6 未安装。先安装 GUI 依赖后再运行界面。")
        print(exc)
        return 1

    from robot_sim.presentation.main_window import MainWindow
    app = QApplication(sys.argv)
    w = MainWindow(root)
    w.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
