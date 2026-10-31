"""Narrow, read-only system-bus adapter.

This module is a provider primitive, not a public tool endpoint. A production
composition root must inject an AEGIS-backed authorization gate. No default
allow implementation exists, and no caller-controlled D-Bus identifiers or
arguments are accepted.
"""
from __future__ import annotations

import asyncio
import json
import math
import shutil
from dataclasses import dataclass
from typing import Awaitable, Callable, Final


AuthorizationGate = Callable[[str], Awaitable[bool]]

_BUSCTL: Final[str] = "/usr/bin/busctl"
_SERVICE: Final[str] = "org.freedesktop.DBus"
_PATH: Final[str] = "/org/freedesktop/DBus"
_INTERFACE: Final[str] = "org.freedesktop.DBus"
_MAX_STDOUT: Final[int] = 16 * 1024
_MAX_STDERR: Final[int] = 4 * 1024
_MAX_ALLOWED_STDOUT: Final[int] = 1024 * 1024
_MAX_ALLOWED_STDERR: Final[int] = 256 * 1024


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous JSON objects instead of silently accepting the last key."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    """Reject JavaScript-style NaN/Infinity tokens accepted by Python's decoder."""
    raise ValueError("non-standard JSON constant")


class _OutputLimitExceeded(Exception):
    """Internal signal used to terminate a child that exceeds an output cap."""


class AdapterError(Exception):
    """Safe, stable adapter failure; never includes subprocess output."""


class AuthorizationDenied(AdapterError):
    pass


@dataclass(frozen=True)
class BusSnapshot:
    bus_id: str
    names: tuple[str, ...]


def _is_valid_bus_name(name: object) -> bool:
    """Validate the ASCII grammar for well-known and unique D-Bus names."""
    if not isinstance(name, str) or not name or len(name) > 255:
        return False
    unique = name.startswith(":")
    body = name[1:] if unique else name
    if ":" in body:
        return False
    elements = body.split(".")
    if len(elements) < 2:
        return False
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    for element in elements:
        if not element or any(character not in allowed for character in element):
            return False
        # The D-Bus grammar permits digit-leading elements in unique names,
        # but forbids them in well-known names. Do not impose an extra
        # first-element restriction on unique connection names.
        if not unique and element[0].isdigit():
            return False
    return True


class ReadOnlySystemBusAdapter:
    """Read two fixed org.freedesktop.DBus methods after policy authorization."""

    def __init__(
        self,
        authorization_gate: AuthorizationGate | None,
        *,
        timeout_seconds: float = 3.0,
        max_stdout: int = _MAX_STDOUT,
        max_stderr: int = _MAX_STDERR,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or timeout_seconds <= 0
            or timeout_seconds > 30
            or not math.isfinite(timeout_seconds)
        ):
            raise ValueError("timeout_seconds must be finite and in (0, 30]")
        if (
            isinstance(max_stdout, bool)
            or not isinstance(max_stdout, int)
            or isinstance(max_stderr, bool)
            or not isinstance(max_stderr, int)
        ):
            raise ValueError("output limits must be integers")
        if max_stdout < 128 or max_stderr < 128:
            raise ValueError("output limits are too small")
        if max_stdout > _MAX_ALLOWED_STDOUT or max_stderr > _MAX_ALLOWED_STDERR:
            raise ValueError("output limits exceed safe maximums")
        self._authorization_gate = authorization_gate
        self._timeout = timeout_seconds
        self._max_stdout = max_stdout
        self._max_stderr = max_stderr

    async def get_bus_id(self) -> str:
        await self._authorize("system.bus.id.read")
        value = await self._call("GetId")
        if (
            not isinstance(value, str)
            or len(value) != 32
            or any(character not in "0123456789abcdefABCDEF" for character in value)
        ):
            raise AdapterError("invalid bus identifier response")
        return value

    async def list_names(self) -> tuple[str, ...]:
        await self._authorize("system.bus.names.read")
        value = await self._call("ListNames")
        if not isinstance(value, list) or len(value) > 1024:
            raise AdapterError("invalid bus names response")
        if any(not _is_valid_bus_name(name) for name in value):
            raise AdapterError("invalid bus names response")
        if len(set(value)) != len(value):
            raise AdapterError("invalid bus names response")
        return tuple(value)

    async def health(self) -> dict[str, str]:
        """Cheap, bounded, read-only readiness probe."""
        try:
            await self.get_bus_id()
        except AuthorizationDenied:
            return {"state": "degraded", "reason": "authorization_unavailable"}
        except AdapterError:
            return {"state": "degraded", "reason": "bus_unavailable"}
        return {"state": "ready", "reason": "probe_succeeded"}

    async def snapshot(self) -> BusSnapshot:
        """Collect the two bounded probes; each is independently authorized."""
        bus_id = await self.get_bus_id()
        names = await self.list_names()
        return BusSnapshot(bus_id=bus_id, names=names)

    async def _authorize(self, operation_id: str) -> None:
        gate = self._authorization_gate
        if gate is None:
            raise AuthorizationDenied("authorization gate unavailable")
        try:
            allowed = await gate(operation_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise AuthorizationDenied("authorization unavailable") from exc
        if allowed is not True:
            raise AuthorizationDenied("operation not authorized")

    async def _call(self, method: str) -> object:
        # The method is selected only by the private fixed call sites above.
        if method not in {"GetId", "ListNames"}:
            raise AdapterError("unsupported bus method")
        if shutil.which(_BUSCTL) is None:
            raise AdapterError("bus client unavailable")

        argv = (
            _BUSCTL,
            "--system",
            "--json=short",
            "--timeout",
            f"{max(1, math.ceil(self._timeout * 1000))}ms",
            "call",
            _SERVICE,
            _PATH,
            _INTERFACE,
            method,
        )
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise AdapterError("bus client could not start") from exc
        assert process.stdout is not None and process.stderr is not None
        out_task = asyncio.create_task(self._read_bounded(process.stdout, self._max_stdout))
        err_task = asyncio.create_task(self._read_bounded(process.stderr, self._max_stderr))
        wait_task = asyncio.create_task(process.wait())
        tasks = (out_task, err_task, wait_task)
        try:
            stdout, stderr, return_code = await asyncio.wait_for(
                asyncio.gather(*tasks), timeout=self._timeout
            )
        except asyncio.CancelledError:
            await self._terminate(process)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        except _OutputLimitExceeded as exc:
            await self._terminate(process)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise AdapterError("bus response exceeded output limit") from exc
        except asyncio.TimeoutError as exc:
            await self._terminate(process)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise AdapterError("bus call timed out") from exc
        except Exception as exc:
            await self._terminate(process)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise AdapterError("bus call failed") from exc
        if return_code != 0:
            raise AdapterError("bus call failed")
        try:
            payload = json.loads(
                stdout.decode("utf-8"),
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
            )
            expected_signature = "s" if method == "GetId" else "as"
            if (
                not isinstance(payload, dict)
                or set(payload) != {"type", "data"}
                or payload.get("type") != expected_signature
            ):
                raise ValueError("unexpected response envelope")
            data = payload.get("data")
            if not isinstance(data, list) or len(data) != 1:
                raise ValueError("unexpected result shape")
            return data[0]
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, RecursionError) as exc:
            raise AdapterError("invalid bus response") from exc

    @staticmethod
    async def _read_bounded(stream: asyncio.StreamReader, limit: int) -> bytes:
        """Drain a pipe only up to its cap; signal overflow before the child blocks."""
        result = bytearray()
        while True:
            chunk = await stream.read(min(4096, limit + 1 - len(result)))
            if not chunk:
                return bytes(result)
            result.extend(chunk)
            if len(result) > limit:
                raise _OutputLimitExceeded

    @staticmethod
    async def _terminate(process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        try:
            process.kill()
        except ProcessLookupError:
            # The child may exit between the returncode check and kill().
            pass
        try:
            await asyncio.wait_for(process.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
        except Exception:
            # Cleanup must not replace the sanitized adapter failure that
            # triggered termination (for example, a failed wait operation).
            pass
