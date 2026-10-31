# TuskerOS Agent Instructions

This file is the repository-wide operating contract for every AI or human contributor.

## Start here
1. Read docs/agents/README.md.
2. Read docs/agents/OPERATING_RULES.md.
3. Read your assigned role in docs/agents/AGENT_TASKS.md.
4. Read docs/agents/LAUNCH-10-AGENTS-2026-10-31.md and your matching role guide under docs/agents/launch/.
5. Read the relevant component architecture, contracts, schemas and tests. Confirm your assigned branch and live main SHA.

## Non-negotiable rules
- For the 2026-10-31 launch cohort, work only on the exact NN-AGENT branch mapped in docs/agents/LAUNCH-10-AGENTS-2026-10-31.md. This owner-approved mapping supersedes legacy agent/NN-short-scope names for this cohort. Never commit directly to main or another agent branch.
- Keep changes scoped. Shared contracts, schemas, security boundaries, package trust, lifecycle semantics and cross-component APIs require Chief Architect approval before modification.
- Never overwrite another agent's work, force-push, rebase shared branches, cherry-pick blindly, or merge your own PR.
- Make small, reviewable commits. One coherent deliverable per pull request.
- Add/update tests with every behavior change. Record command, result and commit SHA.
- Do not weaken, skip, xfail or delete tests to obtain green build.
- Do not claim runtime, hardware, image, VM, inference, security or release behavior without reproducible evidence.
- No secrets, credentials, private keys, tokens, personal data or sensitive logs in Git.
- Trusted low-risk actions may proceed automatically. Sensitive, privileged, destructive, irreversible or externally consequential actions require explicit owner approval.
- Preserve history and forensic evidence. Do not delete branches, logs or records unless owner explicitly approves.
- If blocked by missing contract, dependency, credential, decision or safe condition, stop and file a concise blocker.

## Required work cycle
Plan -> inspect -> implement -> test -> document -> commit -> PR -> review -> merge by authorized integrator.

Every task update identifies task ID/acceptance, branch/base SHA, files changed, exact tests/results, commit SHAs, risks, blockers and rollback/migration notes.

## Response completion accounting
Follow docs/agents/LAUNCH-LOGGING-2026-10-31.md for this launch cohort. One substantive assistant response in that agent chat equals one completion; status-only/ack/tool-only equals zero. Append one record to your own launch log only. Coordinator validates/imports canonical records. Never backdate, duplicate, rewrite or infer counts from tasks/commits/tests.

## Pull requests
Every PR includes task ID, scope, design/contract impact, test evidence, risks, migration/rollback and exact source/base SHAs. Do not merge without required checks on exact PR head, review and integration acceptance.

## Status honesty
Use verified Git refs and actual test output. Report unknown as unknown. Green contract CI does not imply a working OS image or runtime.
