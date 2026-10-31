"""Qt Quick host that connects the preferences UI to validated persistence."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any
from PySide6.QtCore import QObject, QUrl, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from desktop.config.controller import SettingsController
from desktop.tools.settings_recovery import default_settings_path

class SettingsBackend(QObject):
    """Narrow QML bridge; no filesystem or privileged operations are exposed."""
    def __init__(self, controller: SettingsController):
        super().__init__()
        self._controller = controller

    @Slot(result="QVariant")
    def read(self) -> dict[str, Any]:
        return self._controller.read()

    @Slot(result="QVariant")
    def status(self) -> dict[str, bool]:
        return {"needsRecovery": bool(self._controller.load_errors)}

    @Slot("QVariant", result="QVariant")
    def update(self, patch: Any) -> dict[str, Any]:
        try:
            return {"ok": True, "settings": self._controller.update(patch)}
        except (OSError, ValueError, TypeError):
            return {"ok": False}

    @Slot(result="QVariant")
    def reset(self) -> dict[str, Any]:
        try:
            return {"ok": True, "settings": self._controller.reset()}
        except (OSError, ValueError, TypeError):
            return {"ok": False}

def main(argv: list[str] | None = None) -> int:
    app = QGuiApplication(argv if argv is not None else sys.argv)
    engine = QQmlApplicationEngine()
    backend = SettingsBackend(SettingsController(default_settings_path()))
    engine.rootContext().setContextProperty("settingsBackend", backend)
    qml = Path(__file__).with_name("main.qml")
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        return 1
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
