# Desktop task-event presentation contract — draft v0.1

**Owner:** NOVA-02 (consumer/presentation) and TUSKER-04 (authoritative task state/execution)  
**Status:** NOVA-02 reviewed and accepted the current envelope proposal in issue #9; mutual approval remains pending AEGIS-06 and PILOT-08. No live transport or backend integration is implemented.

## Responsibility boundary

- TUSKER-04 owns task execution, authoritative state, snapshots, event production and control acknowledgements.
- NOVA-02 renders task summaries, progress, origin, approvals and controls. The desktop never infers success from a click or optimistic UI state.
- AEGIS-06 remains authoritative for approval policy and authorization.
- PILOT-08 supplies authenticated remote-session context; the UI does not trust a client-provided origin claim.
- Closing/dismissing a task card is presentation-only and never cancels execution.

## Event envelope

The desktop consumer accepts the draft v0.1 envelope: `schema_version`, unique `event_id`, `task_id`, monotonic per-task `sequence`, RFC3339 UTC `occurred_at`, `type`, current authoritative `state`, trusted `origin` display metadata, optional `step` and `progress`, optional `approval`, `result`, `error`, and opaque `correlation_id`. NOVA-02 requires no additional envelope fields at this stage.

The `origin` field must be supplied from authenticated server/session context. The desktop never trusts a client-asserted origin. `step`, `progress`, `approval`, `result`, and `error` may be absent; absence is not itself an error.

Payload text is untrusted display content. Render safe summaries only; do not display raw prompts, credentials, private file contents, chain-of-thought, or unredacted tool output.

## Consumer behavior

1. Deduplicate by `event_id` and track sequence independently per `task_id`.
2. Ignore stale/duplicate events; detect sequence gaps and out-of-order delivery.
3. On reconnect, detected gap, or stale sequence, request an authorized task snapshot from the TUSKER-04 API before resuming event consumption.
4. Map task state from the authoritative `state` field; never calculate terminal state from progress percentage.
5. Show progress as indeterminate when totals are absent or invalid; do not assume every task has a known total.
6. Keep the task panel optional. If its service/transport fails, hide or show an unavailable state without affecting Plasma, applications, or task execution.

## Controls and approval presentation

- **Cancel:** send the task control request and wait for the authoritative acknowledgement/state. `task.cancel_requested` means cancellation is pending, not complete. `task.cancelled` is the terminal cancellation event and must carry the authoritative terminal `state`. Accepted cancellation does not prove side effects were rolled back.
- **Pause/resume:** render only when capability metadata explicitly says the active provider supports safe checkpointing. Otherwise do not show the control.
- **Dismiss:** local UI action only; preserve task history and execution.
- **Approve/deny:** distinct actions referencing the opaque approval ID. The desktop presents the request; AEGIS-06 validates authorization and policy. Never merge approval with dismiss or cancel.
- Disable repeated control submissions while awaiting acknowledgement; show returned outcome and error details in safe, redacted form.

## UI mapping (provisional)

| Event/state | Desktop presentation |
|---|---|
| `task.created`, `task.plan_ready` | New task card / plan-ready indicator |
| `task.awaiting_approval` | Prominent approval card with action/resource summary, risk and expiry |
| `running` / `step.progress` | Running state, safe step summary and determinate/indeterminate progress |
| `task.verification_started` | Verifying state |
| `task.finished` | Completed state and result reference/summary |
| `task.error` | Error state with safe diagnostic summary |
| `task.cancel_requested` | Cancellation pending; do not claim cancelled |
| `task.cancelled` | Cancelled state |
| origin kind `remote` | Remote-origin label from trusted session metadata |

## Open questions before implementation

- Final state enum and mapping of nonterminal/terminal states.
- Snapshot endpoint, authorization model, pagination/history retention and reconnect cursor.
- Transport choice and subscription lifecycle.
- Capability representation for pause/resume and supported controls.
- Exact approval response API and AEGIS-06 authorization handshake.
- Event schema validation/version compatibility and redaction guarantees.
- PILOT-08 confirmation of the authenticated remote-session/origin source.

## Acceptance criteria

- Duplicate, stale, out-of-order and missing-sequence events do not corrupt displayed task state.
- Reconnect refreshes from an authorized snapshot.
- Dismiss never cancels; cancel never implies rollback; pause/resume never appears without capability.
- Approval actions are explicit and authorization is server-side.
- Assistant service loss cannot destabilize the desktop.
- Contract is marked implemented only after TUSKER-04, AEGIS-06 and PILOT-08 confirm their respective interfaces and integration tests pass.
