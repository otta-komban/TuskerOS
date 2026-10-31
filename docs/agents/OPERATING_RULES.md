# Agent Operating Rules

## 1. Branch and Git discipline
- One specialist, one assigned branch, one bounded ownership area. For the 2026-10-31 launch, use the exact NN-AGENT branch in docs/agents/LAUNCH-10-AGENTS-2026-10-31.md; this owner-approved mapping supersedes legacy branch names.
- Start each task by recording git status --short --branch, git rev-parse HEAD and git rev-parse origin/main.
- Never overwrite or discard unrelated work. Commit format: area: imperative summary. Keep commits focused.
- No direct main commits, force pushes, branch deletion, history rewriting or self-merging. Sync only by reviewed fast-forward from approved main; if divergent, stop and ask integrator.

## 2. Scope and interfaces
- Component ownership is in AGENT_TASKS.md and the launch-specific guide. Cross-cutting changes require Chief Architect approval.
- Shared API/schema changes require rationale, compatibility assessment, versioning, migration notes, valid/invalid examples and positive/negative tests.
- Do not duplicate another component's responsibility. Record dependencies/blockers explicitly.

## 3. Security and safety
- Default deny at privilege boundaries. Approval binds exact action, actor/session/device, target/resource, preconditions and expiry/one-time use where required.
- Low-risk trusted operations may be automatic; privileged, sensitive, destructive, irreversible or externally consequential actions require explicit owner approval.
- Do not log secrets or sensitive payloads. Validate untrusted inputs, paths, package metadata, signatures and IPC messages. No production bypass switches.

## 4. Quality and evidence
- Add tests with behavior changes; cover normal, boundary, malformed, failure, cancellation, retry and authorization cases as relevant.
- Run narrow tests, component suite and unified CI. Record exact commands, exit codes, counts, tested SHA and evidence.
- Mocks/static/schema tests prove only what they exercise. Never claim runtime/image/VM/inference/security/release behavior without reproducible evidence.
- Update component docs and rollback/migration notes. No unexplained TODO, placeholder, swallowed exception or silent fallback in completed work.

## 5. Pull requests
PR title: [AGENT-ID] concise deliverable. Include task ID, scope/non-goals, base/head SHAs, design/contract impact, implementation, exact tests/results, security/privacy impact, migration/rollback, limitations and blockers. Only integrator merges after review and checks on exact PR head.

## 6. Blocker reporting
Record blocker ID, owner, task, exact evidence/reproduction, impact, dependency, options and decision needed. Do not silently stall or invent workarounds.

## 7. Completion and progress records
Follow docs/agents/LAUNCH-LOGGING-2026-10-31.md. One substantive assistant response per agent chat is one completion; status-only/ack/tool-only is zero. Logs are append-only, unique, sequential and UTC timestamped at write time. Coordinator alone validates/imports canonical records. Commits, tests, PRs, files and tool calls are not completion units.

## 8. Stop conditions
Stop and escalate for unapproved shared-contract changes, privileged/destructive action without approval, missing credentials/decisions, data deletion, weakened security controls or unsupported runtime claims.
