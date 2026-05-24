import os
import sys
from pathlib import Path


def configure_qt_paths() -> None:
    try:
        import PySide6

        pyside_path = Path(PySide6.__file__).resolve().parent
        platforms_path = pyside_path / "plugins" / "platforms"
        if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(pyside_path))
        if (platforms_path / "qwindows.dll").is_file():
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms_path)
    except Exception:
        # Let Qt/PyInstaller's built-in discovery try its normal path.
        pass


configure_qt_paths()

from PySide6.QtWidgets import QApplication

from frontend.ui import MainWindow


def main() -> None:
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
