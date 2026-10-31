from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "PySide6 is installed in the Qt runtime CI job")
class SettingsQtRuntimeTests(unittest.TestCase):
    def test_qml_window_loads_with_offscreen_qt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tuskeros-qt-smoke-") as config_home:
            environment = os.environ.copy()
            environment.update(
                {
                    "PYTHONPATH": str(REPO_ROOT) + os.pathsep + environment.get("PYTHONPATH", ""),
                    "XDG_CONFIG_HOME": config_home,
                    "QT_QPA_PLATFORM": "offscreen",
                    "QT_QUICK_BACKEND": "software",
                }
            )
            result = subprocess.run(
                [sys.executable, "-m", "desktop.settings.app", "--smoke-test"],
                cwd=REPO_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"Qt Quick QML failed to load. stdout={result.stdout!r}; stderr={result.stderr!r}",
        )

    def test_backend_round_trip_rejects_invalid_changes_and_resets(self) -> None:
        from desktop.config.controller import SettingsController
        from desktop.settings.app import SettingsBackend

        with tempfile.TemporaryDirectory(prefix="tuskeros-backend-") as directory:
            path = Path(directory) / "desktop.json"
            backend = SettingsBackend(SettingsController(path))
            self.assertEqual(backend.read()["panel"]["icon_size"], 48)
            self.assertEqual(backend.status(), {"needsRecovery": False})

            changed = backend.update({"panel": {"icon_size": 72}})
            self.assertTrue(changed["ok"])
            self.assertEqual(changed["settings"]["panel"]["icon_size"], 72)
            self.assertEqual(json.loads(path.read_text())["panel"]["icon_size"], 72)

            self.assertEqual(backend.update({"panel": {"edge": "unsafe"}}), {"ok": False})
            self.assertEqual(backend.read()["panel"]["edge"], "bottom")
            self.assertEqual(json.loads(path.read_text())["panel"]["edge"], "bottom")

            restarted = SettingsBackend(SettingsController(path))
            self.assertEqual(restarted.read()["panel"]["icon_size"], 72)
            reset = restarted.reset()
            self.assertTrue(reset["ok"])
            self.assertEqual(reset["settings"]["panel"]["icon_size"], 48)
            self.assertEqual(json.loads(path.read_text())["panel"]["icon_size"], 48)


if __name__ == "__main__":
    unittest.main()
