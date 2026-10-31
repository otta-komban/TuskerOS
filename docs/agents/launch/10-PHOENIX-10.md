# PHOENIX-10 — Installer & Recovery

Assigned branch: 10-PHOENIX
Launch base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Scope: Installer/recovery, artifact verification, release manifest, storage safety, provenance and boot acceptance.

## First actions
1. Read AGENTS.md, docs/agents/OPERATING_RULES.md, docs/agents/AGENT_TASKS.md, launch manifest and logging policy.
2. Verify assigned branch, live main SHA and clean working tree; inspect current CI/PRs.
3. Inspect main and relevant historical branch work before editing. Preserve old branches/logs; port only reviewed changes.
4. Write a task plan with dependencies and acceptance criteria. If approval/contract is missing, stop and file an evidence-backed blocker.

## Assigned work
1. Review release contract, installer architecture, verifier, security release gate and Issue #52; preserve tests.
2. Integrate ATLAS ISO/QCOW2 metadata, checksums, SBOM/provenance and gate evidence.
3. Keep signature trust, trust roots and anti-rollback blocked until AEGIS approves; digest matching is not signature verification.
4. Coordinate NEXUS storage preflight and AEGIS authorization before disk-writing; keep writes disabled until approved.
5. Run UEFI boot/install/recovery only in disposable VM/storage; record image SHA, environment and outcome.

## Acceptance criteria
- [ ] Manifest/artifact integrity checks pass with checksums/architecture.
- [ ] Actual image and provenance linked to commit.
- [ ] UEFI VM boot and installer/recovery evidence.
- [ ] No promotion claim while trust/storage gates incomplete.

## Dependencies
ATLAS image; AEGIS trust/privilege; NEXUS storage; NOVA packaging.

## Stop conditions / known blockers
No disk mutation or release promotion without approved trust/storage contracts. No verified ISO/VM boot on main.

## Engineering and merge rules
- Work only on 10-PHOENIX; never push to main or another agent branch.
- No force-push, shared-branch rebase, blind cherry-pick, branch deletion or self-merge.
- Small focused commits: area: imperative summary.
- Add regression tests; never weaken/skip tests to make CI green.
- Validate and bound untrusted inputs, paths, sizes, time, memory and output.
- Sensitive/destructive/privileged actions require explicit approval; default deny. Destructive tests use disposable environments.
- Update docs, compatibility and rollback notes. Record exact commands, results, tested SHA and CI URLs.
- Distinguish PASS, FAIL, NOT RUN and UNVERIFIED; no unsupported runtime claims.
- PR title: [PHOENIX-10] deliverable; target main; include task ID, scope, base/head SHA, tests, security, rollback, evidence and blockers. Coordinator merges after review.

## Completion log
Append qualifying responses only to logs/launch-2026-10-31/PHOENIX-10.jsonl. One substantive task-relevant assistant response in this chat equals exactly one completion; status/ack/tool-only responses equal zero. A response cannot count twice. Use unique response UUID, sequential ID PHOENIX-10-000001, actual UTC timestamp at append time, exact branch and durable evidence. Re-read/validate after each append. Preserve prior cohort logs. Never edit progress/completions.jsonl or another agent's log.
