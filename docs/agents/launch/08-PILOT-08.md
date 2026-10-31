# PILOT-08 — Remote Control

Assigned branch: 08-PILOT
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Remote pairing/API, sessions, revocation, transport security and network threat model.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Review remote threat model, decision register and historical branch-only work; preserve evidence.
2. List P0 owner decisions: exposure, pairing consent, trust, key lifecycle, revocation, recovery and remote action policy.
3. Specify protocol/session state machine and bind remote actions to AEGIS authorization.
4. Test replay, rate limits, downgrade, revocation, disconnect/network loss and audit.
5. Keep remote mutation disabled until security review and NEXUS/AEGIS acceptance.

## Acceptance criteria
- [ ] P0 decisions recorded.
- [ ] Threat model/protocol reviewed.
- [ ] Adversarial security tests pass.
- [ ] Remote release gate signed off or feature remains disabled.

## Dependencies
AEGIS authorization; NEXUS tool/broker; owner remote-access decisions.

## Stop conditions / known blockers
No unreviewed remote protocol or privileged actions. Unanswered product decisions mean design-only/disabled.

## Engineering and merge rules
- Work only on 08-PILOT; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [PILOT-08] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/PILOT-08.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID PILOT-08-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
