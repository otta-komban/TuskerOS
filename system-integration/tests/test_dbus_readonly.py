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
        adapter._call = AsyncMock(return_value="bus-id-123")

        result = await adapter.get_bus_id()

        self.assertEqual(result, "bus-id-123")
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

    async def test_invalid_bus_name_collection_is_rejected(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(return_value=["valid.name", 7])

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
        process = FakeProcess(stdout=b'{"type":"s","data":["bus-123"]}')
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        with patch("adapters.dbus_readonly.shutil.which", return_value="/usr/bin/busctl"), patch(
            "adapters.dbus_readonly.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=process),
        ) as spawn:
            result = await adapter._call("GetId")

        self.assertEqual(result, "bus-123")
        self.assertEqual(
            spawn.await_args.args,
            (
                "/usr/bin/busctl", "--system", "--json=short", "--timeout",
                "3000ms", "call", "org.freedesktop.DBus",
                "/org/freedesktop/DBus", "org.freedesktop.DBus", "GetId",
            ),
        )
        self.assertFalse(process.killed)

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

    def test_timeout_and_output_limits_are_bounded(self):
        with self.assertRaises(ValueError):
            ReadOnlySystemBusAdapter(AsyncMock(), timeout_seconds=31)
        with self.assertRaises(ValueError):
            ReadOnlySystemBusAdapter(AsyncMock(), max_stdout=1)


if __name__ == "__main__":
    unittest.main()
