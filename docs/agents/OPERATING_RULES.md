# Agent Operating Rules

## 1. Branch and Git discipline
- One specialist, one assigned branch, one bounded ownership area.
- Branch naming: `agent/NN-short-scope`; never create ad-hoc permanent agent branches.
- Start each task by recording `git status --short --branch`, `git rev-parse HEAD`, and `git rev-parse origin/main`.
- Never work with uncommitted unrelated changes. Do not overwrite or discard user/agent changes.
- Commit format: `<area>: <imperative summary>` (example: `atlas: validate package manifest architecture`).
- Keep commits focused and explain non-obvious decisions in the body.
- No direct main commits, force pushes, branch deletion, history rewriting, or self-merging.
- Sync only by a reviewed fast-forward from approved main. If divergent, stop and ask the integrator.

## 2. Scope and interfaces
- Component ownership is defined in `AGENT_TASKS.md`.
- Cross-cutting changes require a proposal to the Chief Architect before implementation.
- Shared API/schema changes require: rationale, compatibility assessment, versioning, migration notes, valid/invalid examples, and positive/negative tests.
- Do not duplicate another component's responsibility. Use published interfaces and adapters.
- Every dependency on another agent must be written as a blocker/dependency, not silently mocked as complete.

## 3. Security and safety
- Default deny at privilege boundaries.
- Approval must be bound to the exact action, actor/session/device, target/resource, preconditions, and expiry/one-time use where the contract requires it.
- Approval is not implied by a user being logged in or by a previous approval for a different action.
- Low-risk trusted operations may be automatic; privileged, sensitive, destructive, irreversible, or externally consequential actions require explicit approval.
- Do not log secrets or sensitive payloads. Use redaction and stable correlation IDs.
- Validate all untrusted inputs, paths, package metadata, signatures, and IPC messages.
- No bypass switches in production paths. Test-only bypasses must be isolated and unmistakably unavailable in production.
- Report suspected security defects immediately; do not publish exploit details in public logs.

## 4. Quality and evidence
- Add tests before or alongside implementation.
- Include normal, boundary, malformed, failure, cancellation, retry, and authorization cases as relevant.
- Run the narrowest relevant test first, then the complete component suite, then unified CI where feasible.
- Record exact commands, exit codes, test counts, and artifact links. Never convert a not-run test into a pass.
- A mock or schema test proves only the behavior it exercises. Label mocks and static checks honestly.
- Update component docs, examples, and operational notes with behavior changes.
- No unexplained TODO, placeholder implementation, swallowed exception, or silent fallback in a completed task.

## 5. Pull requests
PR title: `[AGENT-ID] concise deliverable`.
PR description must contain:
- Task / issue ID and problem statement;
- in-scope and explicitly out-of-scope work;
- base SHA and head SHA;
- design and contract changes;
- implementation summary;
- exact test commands and results;
- security/privacy impact;
- migration, rollback, and compatibility notes;
- known limitations and follow-up issues.

PR must be focused, reviewable, and pass required checks on its current head. Resolve review comments with evidence. Only the integrator merges.

## 6. Blocker reporting
Create or update an issue with: blocker ID, owner, affected task, exact reproduction/evidence, impact, dependency, proposed options, and decision needed. Do not stall silently or work around a missing security/architecture decision.

## 7. Completion and progress records
- One valid completion per agent per user message maximum.
- A completion requires substantive, user-directed work and evidence; status-only replies do not count.
- Central coordinator validates records and is the sole writer of the canonical ledger.
- JSONL records are append-only, unique, sequential per agent, and UTC timestamped at write time.
- Never backdate, reorder, overwrite, delete, or silently repair a record. Flag anomalies for an audit.
- Commits, tests, PRs, files, and tool calls are not completion units.
- Dashboard counts must be derived from validated ledger records and verified Git refs, not estimates.

## 8. Stop conditions
Stop and escalate if the task requires changing a shared contract without approval, privileged/destructive action without approval, secrets or unavailable credentials, deleting/replacing data, weakening a test/security control, or making an unsupported runtime claim.
