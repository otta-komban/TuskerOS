# PIXEL-03 — Theme Studio

Assigned branch: 03-PIXEL
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Theme tokens/packs, validation, safe apply/reload, accessibility and rollback.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Inspect theme schemas, sample packs and Issue #50; resolve shared theme-contract blocker first.
2. Propose compatibility/version policy with NOVA and Chief Architect.
3. After approval, implement pack validation, safe paths, atomic apply, backup and rollback.
4. Test malformed packs, traversal/symlinks, contrast/accessibility and rollback.
5. Demonstrate apply/reload in running Plasma session.

## Acceptance criteria
- [ ] Approved versioned theme contract.
- [ ] Valid/invalid pack and path-safety tests pass.
- [ ] Runtime apply/reload and rollback demonstrated.

## Dependencies
NOVA shell/session API; Chief Architect approval of Issue #50.

## Stop conditions / known blockers
Until Issue #50 is resolved, limit work to audit/proposal/isolated tests; do not change shared schema.

## Engineering and merge rules
- Work only on 03-PIXEL; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [PIXEL-03] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/PIXEL-03.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID PIXEL-03-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
