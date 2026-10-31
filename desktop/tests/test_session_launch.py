from __future__ import annotations

import configparser
import io
import unittest
from pathlib import Path
from unittest.mock import Mock

from desktop.session.launch import (
    SESSION_ENVIRONMENT,
    build_session_environment,
    main,
)


class SessionLaunchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executable = Path("/usr/bin/startplasma-wayland")
        self.available = lambda path: path == self.executable

    def test_session_descriptor_targets_packaged_launcher(self) -> None:
        descriptor = Path(__file__).resolve().parents[1] / "session" / "tuskeros-wayland.desktop"
        metadata = configparser.ConfigParser(interpolation=None)
        metadata.read(descriptor, encoding="utf-8")
        entry = metadata["Desktop Entry"]
        self.assertEqual(entry["Exec"], "/usr/libexec/tuskeros/session-launcher")
        self.assertEqual(entry["TryExec"], entry["Exec"])
        self.assertEqual(entry["Type"], "Application")
        self.assertIn("KDE", entry["DesktopNames"])

    def test_environment_declares_wayland_plasma_and_preserves_login_context(self) -> None:
        source = {"HOME": "/home/tester", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"}
        result = build_session_environment(source)
        self.assertEqual(result["HOME"], source["HOME"])
        self.assertEqual(result["DBUS_SESSION_BUS_ADDRESS"], source["DBUS_SESSION_BUS_ADDRESS"])
        for key, value in SESSION_ENVIRONMENT.items():
            self.assertEqual(result[key], value)
        self.assertNotIn("DISPLAY", result)

    def test_session_environment_overrides_conflicting_login_metadata(self) -> None:
        source = {
            "HOME": "/home/tester",
            "XDG_SESSION_TYPE": "x11",
            "XDG_CURRENT_DESKTOP": "GNOME",
            "XDG_SESSION_DESKTOP": "GNOME",
            "KDE_FULL_SESSION": "false",
            "KDE_SESSION_VERSION": "5",
        }
        original = dict(source)
        result = build_session_environment(source)
        self.assertEqual(source, original)
        for key, value in SESSION_ENVIRONMENT.items():
            self.assertEqual(result[key], value)

    def test_execve_gets_a_private_environment_snapshot(self) -> None:
        source = {"HOME": "/home/tester", "XDG_SESSION_TYPE": "x11"}
        execve = Mock()
        main(
            [], environ=source, executable=self.executable,
            is_executable=self.available, execve=execve,
            stdout=io.StringIO(), stderr=io.StringIO(),
        )
        self.assertEqual(source, {"HOME": "/home/tester", "XDG_SESSION_TYPE": "x11"})
        passed_environment = execve.call_args.args[2]
        self.assertEqual(passed_environment["XDG_SESSION_TYPE"], "wayland")
        self.assertEqual(passed_environment["HOME"], "/home/tester")
        self.assertIsNot(passed_environment, source)

    def test_check_mode_reports_ready_without_starting_session(self) -> None:
        output, errors = io.StringIO(), io.StringIO()
        execve = Mock()
        result = main(
            ["--check"], executable=self.executable, is_executable=self.available,
            execve=execve, stdout=output, stderr=errors,
        )
        self.assertEqual(result, 0)
        self.assertIn("launcher ready", output.getvalue())
        self.assertEqual(errors.getvalue(), "")
        execve.assert_not_called()

    def test_start_execs_stock_plasma_directly_with_expected_environment(self) -> None:
        execve = Mock()
        result = main(
            [], environ={"HOME": "/home/tester", "PATH": "/usr/bin"},
            executable=self.executable, is_executable=self.available, execve=execve,
            stdout=io.StringIO(), stderr=io.StringIO(),
        )
        self.assertEqual(result, 0)
        execve.assert_called_once()
        path, argv, environment = execve.call_args.args
        self.assertEqual(path, str(self.executable))
        self.assertEqual(argv, [str(self.executable)])
        self.assertEqual(environment["HOME"], "/home/tester")
        self.assertEqual(environment["XDG_SESSION_TYPE"], "wayland")
        self.assertEqual(environment["KDE_SESSION_VERSION"], "6")

    def test_plasma_arguments_are_forwarded_without_shell_interpolation(self) -> None:
        execve = Mock()
        marker = "$(touch /tmp/should-not-run)"
        main(
            ["--", marker], executable=self.executable, is_executable=self.available,
            execve=execve, stdout=io.StringIO(), stderr=io.StringIO(),
        )
        self.assertEqual(execve.call_args.args[1], [str(self.executable), "--", marker])

    def test_missing_plasma_binary_fails_closed(self) -> None:
        output, errors = io.StringIO(), io.StringIO()
        execve = Mock()
        result = main(
            ["--check"], executable=self.executable, is_executable=lambda _: False,
            execve=execve, stdout=output, stderr=errors,
        )
        self.assertEqual(result, 127)
        self.assertIn("unavailable", errors.getvalue())
        execve.assert_not_called()

    def test_exec_failure_is_reported(self) -> None:
        def fail(*_args: object) -> None:
            raise OSError("simulated exec failure")

        errors = io.StringIO()
        result = main(
            [], executable=self.executable, is_executable=self.available,
            execve=fail, stdout=io.StringIO(), stderr=errors,
        )
        self.assertEqual(result, 126)
        self.assertIn("simulated exec failure", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
