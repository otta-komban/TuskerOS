# Build, Test, and CI Protocol

## Purpose
Keep builds repeatable and make every reported result traceable to a commit. The canonical baseline currently has a unified GitHub Actions workflow at `.github/workflows/unified-validation.yml`.

## Before changing code
From a clean checkout:
```bash
git status --short --branch
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
```
Confirm the task branch and record both SHAs. Do not start if the working tree contains unrelated changes or the branch base is unclear.

## Validation sequence
1. Read the component README and its workflow under `.github/workflows/`.
2. Run the exact narrow component test/validator locally using the command in that workflow.
3. Run all relevant component tests.
4. Run the unified workflow (or its exact constituent commands) before requesting merge.
5. For runtime work, add the appropriate disposable VM/container/device integration test; static tests are not a substitute.
6. Capture test logs and generated artifact checksums. Do not commit large generated artifacts unless the task explicitly requires them.

## Current unified CI coverage
The recorded baseline workflow has eight jobs:
- Core contract schemas/tests
- Security contract validation
- System integration contracts
- AI model/inference contracts
- Desktop static validation (Python tests, validators, JS syntax)
- Theme pack validation
- Fedora package resolver
- Marketplace transaction lifecycle

Baseline run `41174359784` passed 8/8 on main SHA `8bf66079f9e021244eda432fa8455e83b59e2165`. Before relying on this result, verify the workflow run and current branch SHA in GitHub.

## Required evidence record
For every validation command, record:
- command exactly as run;
- environment (OS, runtime/tool versions, architecture);
- tested commit SHA;
- start/end time in UTC;
- exit code;
- test count and pass/fail/skip counts when available;
- log/artifact URL or a short retained log reference;
- whether it is unit, contract, static, integration, VM, hardware, or manual evidence.

Example:
```text
Command: python -m pytest tusker-core/tests -q
Commit: <full SHA>
Environment: <OS / Python / architecture>
Result: exit=0; passed=<n>; failed=0; skipped=<n>
Evidence: <CI run or retained artifact URL>
Scope: component unit/contract tests (not runtime acceptance)
```

## Artifact discipline
- Name artifacts with component, version, commit short SHA, platform and build number.
- Record SHA-256 checksums and build provenance.
- Never overwrite a published artifact; create a new immutable version.
- Do not place secrets, credentials, private keys, or user data in artifacts/logs.
- Retain failed logs long enough to diagnose; redact sensitive values, never silently erase evidence.
- Separate reproducible build outputs from local caches and generated scratch files.

## Merge gate
A PR is eligible only when:
- current PR head has all required checks green;
- reviewer has inspected diff and evidence;
- tests cover changed behavior and relevant failure/security cases;
- docs and migration/rollback notes are updated;
- no unresolved blocking review or security finding remains;
- integrator confirms no conflicting cross-agent contract change.

A green contract/static workflow does not establish successful Fedora image build, VM boot, desktop runtime, live inference, production authorization broker, remote-control security, package transaction execution, or installer recovery. Those require their own explicit evidence.

## Failure handling
Do not hide failures with retries that are not recorded, broad exception handling, disabled tests, relaxed assertions, or workflow skips. If infrastructure is flaky, preserve the first failure and document subsequent retries separately. File a blocker when the failure is outside the agent's scope.
