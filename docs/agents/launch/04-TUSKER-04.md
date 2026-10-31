# TUSKER-04 — Core Lifecycle

Assigned branch: 04-TUSKER
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Task lifecycle, typed events, transitions, idempotency, cancellation and failure recovery.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Review core schemas/contracts/architecture and Issue #53; contracts remain draft/provisional and some fixtures differ.
2. Propose canonical transition matrix and event envelope for Chief Architect approval; include NEXUS/ORBIT needs.
3. After approval, implement versioned lifecycle transitions, event append/replay, idempotency, cancellation and unknown outcomes.
4. Test races, duplicate/replay, stale versions, cancellation and recovery.
5. Publish integration and migration notes.

## Acceptance criteria
- [ ] Approved contract version and state matrix.
- [ ] Implementation conforms to schemas and tests pass.
- [ ] Replay/idempotency/cancellation evidence and compatibility notes.

## Dependencies
Chief Architect contract approval; NEXUS and ORBIT integration.

## Stop conditions / known blockers
Issue #53 reports missing task assignment/contract approval. Do not change shared semantics before approval.

## Engineering and merge rules
- Work only on 04-TUSKER; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [TUSKER-04] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/TUSKER-04.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID TUSKER-04-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
