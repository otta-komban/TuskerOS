# FORGE-09 — Ecosystem & Extensions

Assigned branch: 09-FORGE
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Catalog, package metadata, dependency resolution, trust, transactions, rollback and audit.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Review catalog schemas, resolver, transaction state machine and existing PRs; avoid duplicating merged work.
2. Align extension/package resolution with ATLAS pinned repository model; reject ambiguous versions, architecture mismatch and untrusted sources.
3. Complete transaction planning and rollback semantics without privileged install actions.
4. Integrate install/remove authorization through AEGIS/NEXUS only after approval; default deny.
5. Test malformed metadata, dependency conflicts/cycles, traversal, interrupted transactions, rollback and audit.

## Acceptance criteria
- [ ] Deterministic resolver with reproducible fixtures/provenance.
- [ ] Transaction/rollback tests pass.
- [ ] Trust and privileged boundary explicit; install only after broker approval.
- [ ] Unsupported formats and disabled behavior documented.

## Dependencies
ATLAS package model; AEGIS authorization; NEXUS broker; TUSKER lifecycle.

## Stop conditions / known blockers
No direct package installation or privilege escalation. Static resolver tests do not prove marketplace operation.

## Engineering and merge rules
- Work only on 09-FORGE; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [FORGE-09] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/FORGE-09.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID FORGE-09-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
