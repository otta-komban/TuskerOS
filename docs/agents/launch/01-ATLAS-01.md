# ATLAS-01 — Fedora Base & Image Foundation

Assigned branch: 01-ATLAS
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Fedora base, DNF5, package manifest, repository snapshot, reproducible ISO/QCOW2 build and boot evidence.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Inspect tools/atlas/build-image.sh and os package/repository locks. Main currently has empty package and repository inputs; preserve fail-closed checks.
2. Agree Fedora release, architecture, repositories and package set with NOVA/PHOENIX; record exact NEVRAs and snapshot identity.
3. Implement deterministic manifest validation and build metadata; test missing packages, architecture mismatch, repository failures and version parsing.
4. Run actual KIWI image build on a suitable host; record logs, artifact sizes, SHA-256 and exact commit.
5. Hand outputs to PHOENIX and support UEFI VM boot.

## Acceptance criteria
- [ ] Reviewed non-empty package manifest and pinned repository snapshot.
- [ ] Clean-checkout build produces ISO/QCOW2 with checksums and provenance.
- [ ] Repeat-build comparison documented.
- [ ] At least one artifact boots in UEFI VM.

## Dependencies
NOVA package dependencies; PHOENIX artifact contract; coordinator approval of release/repositories.

## Stop conditions / known blockers
Build inputs are empty on main. Never weaken the script or claim a build without actual artifact evidence.

## Engineering and merge rules
- Work only on 01-ATLAS; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [ATLAS-01] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/ATLAS-01.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID ATLAS-01-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
