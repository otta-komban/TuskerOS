# TuskerOS — 10-agent launch cohort

Created UTC: 2026-10-31T13:23:57.715Z
Base main SHA: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d
Coordination branch: coordination/launch-10-agents-20261031

This owner-approved cohort uses ten branches named NN-AGENT (e.g. 01-ATLAS). This mapping supersedes legacy agent/NN-short-scope names for this cohort. Legacy refs remain untouched; never delete, rename, rebase or force-push them.

| No. | Agent ID | Branch | Ownership |
|---:|---|---|---|
| AT | ATLAS-01 | 01-ATLAS | Fedora Base & Image Foundation |
| NO | NOVA-02 | 02-NOVA | Desktop Shell |
| PI | PIXEL-03 | 03-PIXEL | Theme Studio |
| TU | TUSKER-04 | 04-TUSKER | Core Lifecycle |
| OR | ORBIT-05 | 05-ORBIT | AI Runtime |
| AE | AEGIS-06 | 06-AEGIS | Security Gatekeeper |
| NE | NEXUS-07 | 07-NEXUS | System Integration |
| PI | PILOT-08 | 08-PILOT | Remote Control |
| FO | FORGE-09 | 09-FORGE | Ecosystem & Extensions |
| PH | PHOENIX-10 | 10-PHOENIX | Installer & Recovery |

## Dependencies
- Critical path: ATLAS → PHOENIX → NOVA runtime validation.
- Security: AEGIS ↔ NEXUS; no privileged mutation until approved and tested.
- Core: TUSKER ↔ NEXUS ↔ ORBIT; contract approval precedes shared semantics.
- Desktop: NOVA ↔ PIXEL; PIXEL resolves Issue #50 first.
- Ecosystem: FORGE consumes ATLAS package inputs and AEGIS/NEXUS authorization.
- Remote: PILOT stays disabled until owner decisions and security acceptance.

Parallelize isolated audits/tests/proposals. Do not parallel-edit shared contracts. Coordinator owns integration and merge order.

## Merge and engineering rules
1. Work only on assigned branch. No direct main commits, self-merge, force-push, history rewrite or branch deletion.
2. Record clean/dirty status, branch SHA and live main SHA before tasks. Launch base: 5162de364a2f0b7dcf8aa14251a4c5ce5cf57e6d; re-check main before implementation.
3. Use focused commits: area: imperative summary.
4. Inspect main and legacy branch work before editing; port only reviewed changes. Never blindly merge/cherry-pick divergent history.
5. Add positive, negative, boundary and failure tests. Record exact commands, exit codes, counts and tested SHA.
6. Open focused PRs to main with task ID, scope/non-goals, base/head SHA, contract impact, tests, security, rollback, limitations and evidence. Integrator reviews/merges.
7. Static/schema CI is not proof of image build, VM boot, live inference, desktop runtime, production broker, remote security, package installation or recovery.

## Safety / best practices
- Default deny. Low-risk trusted actions may be automatic; sensitive, privileged, destructive, irreversible or externally consequential actions require owner approval.
- No secrets/sensitive payloads in Git/logs. Validate and bound untrusted inputs, paths, time, memory and output.
- Never weaken/skip tests. Do not claim tests that were not run.
- Shared schemas, policy, privilege boundaries, package trust and lifecycle semantics require Chief Architect approval and compatibility/migration tests.
- Destructive tests only in disposable VMs/storage with approval. Keep unsafe/incomplete features disabled.
- Report PASS, FAIL, NOT RUN and UNVERIFIED distinctly.

## Completion logging
Read docs/agents/LAUNCH-LOGGING-2026-10-31.md. Each new agent chat uses logs/launch-2026-10-31/<AGENT-ID>.jsonl, starting at zero at the timestamp above. One substantive task-relevant assistant response in that chat equals one completion; status/ack/tool-only responses equal zero. One response cannot count twice. Use unique response UUID, sequential IDs, actual UTC write timestamp, exact branch and evidence. Preserve old logs. Coordinator alone validates/imports canonical records.

## Release target
A safe, evidence-backed alpha. No production-ready OS claim without actual image build, artifact integrity, UEFI VM boot, desktop runtime, installer/recovery and security acceptance evidence.
