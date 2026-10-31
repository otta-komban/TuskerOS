# NEXUS-07 — System Integration

Assigned branch: 07-NEXUS
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Typed system adapters, D-Bus, authenticated broker, health/readiness and authorization.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Review Issue #53 and historical branch-only work; report exact diff before porting.
2. Resolve authenticated IPC caller identity and trusted authorization context with AEGIS.
3. Implement typed adapters with validation, bounded output, timeouts, cancellation and health diagnostics.
4. Route all privileged operations through AEGIS; prove denied requests invoke no mutation API.
5. Add safe test doubles and disposable-environment integration tests.

## Acceptance criteria
- [ ] Accepted broker/IPC identity contract.
- [ ] Adapter and authorization tests including zero-mutation denial pass.
- [ ] Health/readiness diagnostics and runtime evidence.
- [ ] Historical branch work reviewed.

## Dependencies
AEGIS broker/policy; TUSKER lifecycle; ATLAS packaging.

## Stop conditions / known blockers
Issue #53 reports contract/activation blockers. No privileged mutation before approved identity and broker contract.

## Engineering and merge rules
- Work only on 07-NEXUS; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [NEXUS-07] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/NEXUS-07.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID NEXUS-07-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
