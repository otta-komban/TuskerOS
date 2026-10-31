"""Qt Quick host that connects the preferences UI to validated persistence."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Sequence

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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the preferences window; --smoke-test loads QML and exits headlessly."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="load the packaged QML window with the offscreen Qt platform and exit",
    )
    options = parser.parse_args(list(argv) if argv is not None else sys.argv[1:])

    # Consume our own arguments before Qt parses argv; only the program name is
    # passed to QGuiApplication so test flags never leak into Qt's option parser.
    app = QGuiApplication([sys.argv[0]])
    engine = QQmlApplicationEngine()
    backend = SettingsBackend(SettingsController(default_settings_path()))
    engine.rootContext().setContextProperty("settingsBackend", backend)
    qml = Path(__file__).with_name("main.qml")
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        return 1
    if options.smoke_test:
        app.processEvents()
        return 0
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
