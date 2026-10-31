from __future__ import annotations

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
