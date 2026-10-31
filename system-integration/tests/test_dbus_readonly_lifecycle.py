"""Lifecycle and cancellation tests for the read-only system-bus adapter."""
import asyncio
import pathlib
import sys
import unittest
from unittest.mock import AsyncMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from adapters.dbus_readonly import AuthorizationDenied, ReadOnlySystemBusAdapter


class ReadOnlySystemBusLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_authorization_cancellation_propagates_without_provider_call(self):
        gate = AsyncMock(side_effect=asyncio.CancelledError())
        adapter = ReadOnlySystemBusAdapter(gate)
        adapter._call = AsyncMock()

        with self.assertRaises(asyncio.CancelledError):
            await adapter.get_bus_id()

        gate.assert_awaited_once_with("system.bus.id.read")
        adapter._call.assert_not_awaited()

    async def test_health_does_not_convert_cancellation_into_degraded_readiness(self):
        adapter = ReadOnlySystemBusAdapter(AsyncMock(return_value=True))
        adapter._call = AsyncMock(side_effect=asyncio.CancelledError())

        with self.assertRaises(asyncio.CancelledError):
            await adapter.health()

        adapter._call.assert_awaited_once_with("GetId")

    async def test_snapshot_stops_after_first_authorization_denial(self):
        gate = AsyncMock(side_effect=[False, True])
        adapter = ReadOnlySystemBusAdapter(gate)
        adapter._call = AsyncMock()

        with self.assertRaises(AuthorizationDenied):
            await adapter.snapshot()

        gate.assert_awaited_once_with("system.bus.id.read")
        adapter._call.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
