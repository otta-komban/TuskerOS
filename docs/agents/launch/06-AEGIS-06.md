# AEGIS-06 — Security Gatekeeper

Assigned branch: 06-AEGIS
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Policy, approval binding, privileged authorization, one-time consumption and audit.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Start from main PR #70 strict-literal-true hardening. Inspect legacy branch unique commits separately; preserve conflicting logs.
2. Audit approval/audit schemas against lifecycle/NEXUS contracts: actor/session/device, action, registry, resource, preconditions, task/step, expiry/replay.
3. Verify deny-by-default and atomic one-time approval consumption; no caller-controlled authorization boolean.
4. Test malformed callbacks, stale/altered approvals, replay, concurrency, audit failure, DB path hazards and zero-mutation denial.
5. Publish threat-model/release gate; keep privileged production actions disabled until NEXUS integration passes.

## Acceptance criteria
- [ ] Security tests pass on exact PR head.
- [ ] Approval binding and atomic consumption proven.
- [ ] Audit durability/redaction and denial-before-mutation evidence.
- [ ] Legacy unique commits selectively reviewed.

## Dependencies
NEXUS broker identity; TUSKER approved task/step contract; Chief Architect approval.

## Stop conditions / known blockers
Mock callback/public boolean is not production authorization. Missing broker identity/consumption means fail closed.

## Engineering and merge rules
- Work only on 06-AEGIS; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [AEGIS-06] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/AEGIS-06.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID AEGIS-06-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
