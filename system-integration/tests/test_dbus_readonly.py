"""Unit tests for the fail-closed D-Bus provider boundary."""
import asyncio
import pathlib
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from adapters.dbus_readonly import (
    AdapterError,
    AuthorizationDenied,
    ReadOnlySystemBusAdapter,
    _OutputLimitExceeded,
)


class FakeProcess:
    def __init__(self, stdout=b"", stderr=b"", returncode=0):
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.stdout.feed_data(stdout)
        self.stdout.feed_eof()
        self.stderr.feed_data(stderr)
        self.stderr.feed_eof()
        self.returncode = returncode
        self.killed = False
        self._exited = asyncio.Event()
        if returncode is not None:
            self._exited.set()

    async def wait(self):
        await self._exited.wait()
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9
        self._exited.set()


class ReadOnlySystemBusAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_bus_id_authorizes_canonical_operation(self):
        gate = AsyncMock(return_value=True)
        adapter = ReadOnlySystemBusAdapter(gate)
        adapter._call = AsyncMock(return_value="0123456789abcdef0123456789abcdef")

        result = await adapter.get_bus_id()

        self.assertEqual(result, "0123456789abcdef0123456789abcdef")
        gate.assert_awaited_once_with("system.bus.id.read")
        adapter._call.assert_awaited_once_with("GetId")

    async def test_list_names_authorizes_and_preserves_names(self):
        gate = AsyncMock(return_value=True)
        adapter = ReadOnlySystemBusAdapter(gate)
        adapter._call = AsyncMock(return_value=["org.freedesktop.DBus", ":1.42"])

        result = await adapter.list_names()

        self.assertEqual(result, ("org.freedesktop.DBus", ":1.42"))
        gate.assert_awaited_once_with("system.bus.names.read")
        adapter._call.assert_awaited_once_with("ListNames")

    async def test_missing_authorization_gate_fails_closed(self):
        adapter = ReadOnlySystemBusAdapter(None)
        adapter._call = AsyncMock()

        with self.assertRaises(AuthorizationDenied):
            await adapter.get_bus_id()

        adapter._call.assert_not_awaited()

    async def test_denial_prevents_provider_call(self):
        gate = AsyncMock(return_value=False)
        adapter = ReadOnlySystemBusAdapter(gate)
        adapter._call = AsyncMock()

        with self.assertRaises(AuthorizationDenied):
            await adapter.list_names()

        gate.assert_awaited_once_with("system.bus.names.read")
        adapter._call.assert_not_awaited()

    async def test_authorization_error_fails_closed(self):
        gate = AsyncMock(side_effect=RuntimeError("private detail"))
        adapter = ReadOnlySystemBusAdapter(gate)
        adapter._call = AsyncMock()

        with self.assertRaises(AuthorizationDenied) as caught:
            await adapter.get_bus_id()

        self.assertEqual(str(caught.exception), "authorization unavailable")
        adapter._call.assert_not_awaited()

    async def test_invalid_bus_id_is_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=["not-a-string"])

        with self.assertRaises(AdapterError):
            await adapter.get_bus_id()

    async def test_bus_id_with_non_hex_characters_is_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value="g" * 32)

        with self.assertRaises(AdapterError):
            await adapter.get_bus_id()

    async def test_invalid_bus_name_collection_is_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=["valid.name", 7])

        with self.assertRaises(AdapterError):
            await adapter.list_names()

    async def test_truthy_non_boolean_authorization_is_denied(self):
        gate = AsyncMock(return_value=1)
        adapter = ReadOnlySystemBusAdapter(gate)
        adapter._call = AsyncMock()

        with self.assertRaises(AuthorizationDenied):
            await adapter.get_bus_id()

        gate.assert_awaited_once_with("system.bus.id.read")
        adapter._call.assert_not_awaited()

    async def test_bus_id_with_invalid_length_is_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value="b" * 33)

        with self.assertRaises(AdapterError):
            await adapter.get_bus_id()

    async def test_bus_name_collection_at_maximum_count_is_accepted(self):
        names = [f"org.example.Service{i}" for i in range(1024)]
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=names)

        self.assertEqual(await adapter.list_names(), tuple(names))

    async def test_bus_name_collection_over_maximum_count_is_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=["org.example.Service"] * 1025)

        with self.assertRaises(AdapterError):
            await adapter.list_names()

    async def test_bus_name_over_maximum_length_is_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=["a" * 256])

        with self.assertRaises(AdapterError):
            await adapter.list_names()

    async def test_bus_name_at_maximum_length_is_accepted(self):
        name = "a." + ("b" * 253)
        self.assertEqual(len(name), 255)
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=[name])

        self.assertEqual(await adapter.list_names(), (name,))

    async def test_empty_bus_name_is_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=[""])

        with self.assertRaises(AdapterError):
            await adapter.list_names()

    async def test_malformed_bus_name_grammar_is_rejected(self):
        invalid_names = (
            "single", "org..service", ".org.service", "org.service.",
            "org.1service", "org.service name", "org.sérvice", "org:service.name",
            ":1", ":.42", ":1..42", "::1.42",
        )
        for name in invalid_names:
            with self.subTest(name=name):
                adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
                adapter._call = AsyncMock(return_value=[name])
                with self.assertRaises(AdapterError):
                    await adapter.list_names()

    async def test_duplicate_bus_names_are_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=["org.example.Service", "org.example.Service"])

        with self.assertRaises(AdapterError):
            await adapter.list_names()

    async def test_health_reports_degraded_when_authorization_unavailable(self):
        adapter = ReadOnlySystemBusAdapter(None)

        self.assertEqual(
            await adapter.health(),
            {"state": "degraded", "reason": "authorization_unavailable"},
        )

    async def test_health_reports_degraded_when_bus_fails(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(side_effect=AdapterError("bus call failed"))

        self.assertEqual(
            await adapter.health(),
            {"state": "degraded", "reason": "bus_unavailable"},
        )

    async def test_bounded_pipe_reader_accepts_exact_limit(self):
        stream = asyncio.StreamReader()
        stream.feed_data(b"x" * 128)
        stream.feed_eof()

        result = await ReadOnlySystemBusAdapter._read_bounded(stream, 128)

        self.assertEqual(result, b"x" * 128)

    async def test_bounded_pipe_reader_signals_overflow(self):
        stream = asyncio.StreamReader()
        stream.feed_data(b"x" * 129)
        stream.feed_eof()

        with self.assertRaises(_OutputLimitExceeded):
            await ReadOnlySystemBusAdapter._read_bounded(stream, 128)

    async def test_subprocess_uses_only_fixed_system_bus_arguments(self):
        process = FakeProcess(stdout=b'{"type":"s","data":["0123456789abcdef0123456789abcdef"]}')
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ) as spawn:
            result = await adapter._call("GetId")

        self.assertEqual(result, "0123456789abcdef0123456789abcdef")
        self.assertEqual(
            spawn.await_args.args,
            (
                "/usr/bin/busctl", "--system", "--json=short", "--timeout",
                "3000ms", "call", "org.freedesktop.DBus",
                "/org/freedesktop/DBus", "org.freedesktop.DBus", "GetId",
            ),
        )
        self.assertFalse(process.killed)

    async def test_sub_millisecond_timeout_rounds_up_for_busctl(self):
        process = FakeProcess(stdout=b'{"type":"s","data":["0123456789abcdef0123456789abcdef"]}')
        adapter = ReadOnlySystemBusAdapter(
            AsyncMock(return_value=True), timeout_seconds=0.0001
        )
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ) as spawn:
            await adapter._call("GetId")

        self.assertEqual(spawn.await_args.args[4], "1ms")

    async def test_subprocess_is_killed_on_stdout_overflow(self):
        process = FakeProcess(stdout=b"x" * 129, returncode=None)
        adapter = ReadOnlySystemBusAdapter(
            AsyncMock(return_value=True), max_stdout=128
        )
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "bus response exceeded output limit")
        self.assertTrue(process.killed)

    async def test_terminate_reaps_process_when_kill_races_with_exit(self):
        class ExitedDuringKill(FakeProcess):
            def kill(self):
                self._exited.set()
                raise ProcessLookupError

        process = ExitedDuringKill(returncode=None)

        await ReadOnlySystemBusAdapter._terminate(process)

        self.assertTrue(process._exited.is_set())
        self.assertFalse(process.killed)

    async def test_cancellation_kills_running_subprocess(self):
        process = FakeProcess(returncode=None)
        spawned = asyncio.Event()

        async def spawn(*args, **kwargs):
            spawned.set()
            return process

        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=spawn,
        ):
            call = asyncio.create_task(adapter._call("GetId"))
            await asyncio.wait_for(spawned.wait(), timeout=1)
            call.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await call

        self.assertTrue(process.killed)

    async def test_nonzero_exit_does_not_expose_stderr(self):
        process = FakeProcess(stdout=b"", stderr=b"secret diagnostic", returncode=2)
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "bus call failed")
        self.assertNotIn("secret", str(caught.exception))

    async def test_malformed_json_response_is_rejected(self):
        process = FakeProcess(stdout=b"{not-json")
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "invalid bus response")


    async def test_excessively_nested_json_response_is_sanitized(self):
        nested = b"[" * 1100 + b"0" + b"]" * 1100
        process = FakeProcess(
            stdout=b'{"type":"s","data":[' + nested + b"]}"
        )
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "invalid bus response")

    async def test_subprocess_startup_failure_is_sanitized(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=OSError("private host detail")),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "bus client could not start")
        self.assertNotIn("private host", str(caught.exception))

    async def test_subprocess_is_killed_on_stderr_overflow(self):
        process = FakeProcess(
            stdout=b'{"type":"s","data":["0123456789abcdef0123456789abcdef"]}',
            stderr=b"x" * 129,
            returncode=None,
        )
        adapter = ReadOnlySystemBusAdapter(
            AsyncMock(return_value=True), max_stderr=128
        )
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "bus response exceeded output limit")
        self.assertTrue(process.killed)

    async def test_timeout_kills_running_subprocess(self):
        process = FakeProcess(returncode=None)
        adapter = ReadOnlySystemBusAdapter(
            AsyncMock(return_value=True), timeout_seconds=0.01
        )
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "bus call timed out")
        self.assertTrue(process.killed)

    async def test_duplicate_json_response_keys_are_rejected(self):
        process = FakeProcess(
            stdout=b'{"type":"s","type":"as","data":["0123456789abcdef0123456789abcdef"]}'
        )
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "invalid bus response")

    async def test_non_standard_json_numeric_constants_are_rejected(self):
        process = FakeProcess(stdout=b'{"type":"s","data":[NaN]}')
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "invalid bus response")

    async def test_unexpected_json_response_fields_are_rejected(self):
        process = FakeProcess(
            stdout=b'{"type":"s","data":["0123456789abcdef0123456789abcdef"],"metadata":{"trusted":true}}'
        )
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "invalid bus response")

    async def test_wrong_dbus_signature_is_rejected(self):
        process = FakeProcess(stdout=b'{"type":"as","data":[["name"]]}')
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "invalid bus response")

    async def test_wrong_dbus_result_arity_is_rejected(self):
        process = FakeProcess(stdout=b'{"type":"s","data":["one","two"]}')
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ):
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "invalid bus response")

    async def test_unsupported_method_is_rejected_before_process_lookup(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which") as lookup, patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec"
        ) as spawn:
            with self.assertRaises(AdapterError):
                await adapter._call("BecomeMonitor")

        lookup.assert_not_called()
        spawn.assert_not_awaited()

    async def test_missing_busctl_is_reported_without_spawn(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value=None), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec"
        ) as spawn:
            with self.assertRaises(AdapterError) as caught:
                await adapter._call("GetId")

        self.assertEqual(str(caught.exception), "bus client unavailable")
        spawn.assert_not_awaited()

    def test_non_finite_and_boolean_timeouts_are_rejected(self):
        for timeout in (float("nan"), float("inf"), float("-inf"), True, 10 ** 1000):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    ReadOnlySystemBusAdapter(AsyncMock(), timeout_seconds=timeout)

    def test_non_integer_output_limits_are_rejected(self):
        for keyword, value in (("max_stdout", 128.5), ("max_stderr", True)):
            with self.subTest(keyword=keyword, value=value):
                with self.assertRaises(ValueError):
                    ReadOnlySystemBusAdapter(AsyncMock(), **{keyword: value})

    def test_output_limit_maximums_are_enforced(self):
        for keyword, value in (("max_stdout", 1024 * 1024 + 1), ("max_stderr", 256 * 1024 + 1)):
            with self.subTest(keyword=keyword):
                with self.assertRaises(ValueError):
                    ReadOnlySystemBusAdapter(AsyncMock(), **{keyword: value})

    def test_output_limit_maximum_boundaries_are_accepted(self):
        adapter = ReadOnlySystemBusAdapter(
            AsyncMock(),
            max_stdout=1024 * 1024,
            max_stderr=256 * 1024,
        )
        self.assertEqual(adapter._max_stdout, 1024 * 1024)
        self.assertEqual(adapter._max_stderr, 256 * 1024)

    def test_timeout_and_output_limits_are_bounded(self):
        with self.assertRaises(ValueError):
            ReadOnlySystemBusAdapter(AsyncMock(), timeout_seconds=31)
        with self.assertRaises(ValueError):
            ReadOnlySystemBusAdapter(AsyncMock(), max_stdout=1)


if __name__ == "__main__":
    unittest.main()
