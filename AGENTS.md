# TuskerOS Agent Instructions

This file is the repository-wide operating contract for every AI or human contributor.

## Start here
1. Read `docs/agents/README.md`.
2. Read `docs/agents/OPERATING_RULES.md`.
3. Read your assigned role in `docs/agents/AGENT_TASKS.md`.
4. Read the relevant component architecture, contracts, schemas, and tests before editing.
5. Confirm your assigned branch and the current `main` base SHA with the project coordinator.

## Non-negotiable rules
- Work only on your assigned `agent/NN-...` branch. Never commit directly to `main` or another agent's branch.
- Keep changes scoped to your role. Shared contracts, schemas, security boundaries, package trust, lifecycle semantics, and cross-component APIs require Chief Architect approval before modification.
- Never overwrite another agent's work, force-push, rebase shared branches, cherry-pick blindly, or merge your own PR.
- Make small, reviewable commits. One coherent deliverable per pull request.
- Add or update tests with every behavior change. A test is not evidence until it has actually run; record the command, result, and commit SHA.
- Do not weaken, skip, xfail, or delete tests merely to obtain a green build. Explain and fix the underlying issue.
- Do not claim runtime, hardware, image, VM, inference, security, or release behavior without reproducible evidence.
- No secrets, credentials, private keys, tokens, personal data, or sensitive logs in Git.
- Trusted low-risk actions may proceed automatically. Sensitive, privileged, destructive, irreversible, or externally consequential actions require explicit owner approval.
- Preserve history and forensic evidence. Do not delete branches, logs, or records unless the repository owner explicitly approves.
- If blocked by a missing contract, dependency, credential, decision, or unsafe condition, stop at the boundary and file a concise blocker. Do not invent a substitute.

## Required work cycle
Plan -> inspect -> implement -> test -> document -> commit -> PR -> review -> merge by authorized integrator.

Every task update must identify:
- task ID and acceptance criteria;
- branch and base SHA;
- files changed;
- tests actually run and exact outcomes;
- commit SHA(s);
- remaining risks, blockers, and rollback/migration notes.

## Response completion accounting
- **One substantive assistant response in this agent chat = at most one completion.** Count the response once, no matter how many tasks, commits, tests, files, or milestones it contains.
- A status-only/acknowledgement/tool-only response is zero completions.
- Never infer the count from a C-number, task ID, milestone count, commit count, or number of deliverables. For example, `C0010` does not mean 10 completions.
- Append exactly one record per qualifying response to your own `logs/completions/<AGENT-ID>.jsonl` on your assigned branch. Never edit another agent's file or the coordinator-owned canonical ledger.
- Re-read your local log and derive your dashboard count from its records. Show local count and canonical validated count separately. A local record is not canonical until coordinator validation.
- If branch-local logging cannot be committed, do not claim the log was updated or increment the count.

## Pull request requirements
Every PR must include the task ID, scope, design/contract impact, test evidence, risks, migration/rollback, and exact source/base SHAs. Do not merge without required checks on the exact PR head, review, and integration acceptance.

## Status honesty
Use only verified GitHub refs and actual test output. Report unknown as unknown. Green contract CI does not imply a working OS image or runtime.
