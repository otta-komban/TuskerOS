# Read-only system D-Bus adapter (prototype)

**Status:** isolated provider primitive; not registered as a public NEXUS tool and not connected to a production AEGIS broker.

## Scope

`adapters/dbus_readonly.py` currently supports only two fixed, read-only calls on the standard `org.freedesktop.DBus` interface:

- `system.bus.id.read` → `GetId`
- `system.bus.names.read` → `ListNames`

The adapter does not accept a bus name, object path, interface, method, command-line argument, or D-Bus payload from a caller. The executable path is a module constant (`/usr/bin/busctl`) and cannot be overridden through the adapter constructor; it uses the system bus, JSON output, a finite call timeout (strictly greater than zero and at most 30 seconds), integer stdout/stderr byte caps, and concurrent bounded stdout/stderr streaming. Constructor validation rejects non-finite/boolean timeouts and non-integer output limits. A pipe that crosses its byte cap triggers immediate child termination rather than waiting for the overall timeout. Subprocess diagnostics are not returned to callers.

## Authorization boundary

The constructor requires an injected asynchronous authorization gate. Each public read method asks the gate for its canonical operation ID before starting a subprocess. A missing gate, exception, or value other than literal `True` denies the operation. There is no permissive default.

The gate is an internal composition seam only; it is **not** the AEGIS wire contract. Do not inject an always-allow callback in production. A production composition root must bind this seam to the owner-approved AEGIS policy/consume flow, including trusted peer identity and any required one-time consume/audit sequencing. Until that integration is approved and implemented, this adapter must remain unregistered and unavailable to invocation callers. It does not parse caller-provided `authorization_context` or treat it as a grant.

## Failure behavior

- Timeout, process startup failure, nonzero exit, malformed or ambiguous JSON (including duplicate object keys, non-standard numeric constants, and unexpected response-envelope fields), invalid signature, invalid result shape, and output overflow produce a stable generic adapter error.
- Cancellation propagates and terminates the child process. Cleanup tolerates the child exiting in the narrow race between the return-code check and the kill request, and still waits for process reaping.
- Health returns `degraded` when authorization or the bus probe is unavailable; it never treats inability to authorize as readiness.
- This prototype does not implement mutation, arbitrary D-Bus introspection, signal subscriptions, retry, or operation reconciliation because it performs no mutations.

## Tests

Run from the repository root:

```sh
python -m unittest discover -s system-integration/tests -v
```

The adapter unit tests verify the authorization stop condition (including rejection of truthy non-boolean grants), fixed operation mapping, bus-ID and bus-name count/length bounds, result validation, degraded health behavior, exact subprocess arguments, stdout and stderr overflow termination, timeout termination, cancellation cleanup, sanitized startup/nonzero-exit errors, malformed JSON, wrong D-Bus signatures and result arity, unsupported-method rejection, and missing-client handling using a controlled fake process. They do not prove real system-bus interoperability or production AEGIS integration. Those require a disposable D-Bus test session and the owner-approved broker contract respectively.
