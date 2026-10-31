# ORBIT-05 — AI Runtime

Assigned branch: 05-ORBIT
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Provider adapters, local inference, model lifecycle, resource controls, cancellation and redacted traces.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Review 30-commits-ahead historical branch and Issue #57; do not blindly merge/cherry-pick; compare against main.
2. Run unit tests and compile checks; keep real-Ollama tests explicitly opt-in.
3. Connect to actual local Ollama/model and run inference, streaming, health/version, cancellation and smoke tests.
4. Wire AEGIS authorization for model install/remove; default deny until exact action/session/device/resource approval exists.
5. Coordinate TUSKER lifecycle and ATLAS packaging; document daemon cgroup limitation.

## Acceptance criteria
- [ ] Focused reviewed PR against main.
- [ ] Actual local provider inference report with model digest and host metadata.
- [ ] Authorization integration or explicit disabled boundary; limits documented.

## Dependencies
AEGIS authorization; TUSKER lifecycle; ATLAS packaging.

## Stop conditions / known blockers
No live provider/model means no inference acceptance. Admission checks are not hard daemon resource isolation.

## Engineering and merge rules
- Work only on 05-ORBIT; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [ORBIT-05] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/ORBIT-05.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID ORBIT-05-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
