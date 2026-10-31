# Work Logging and Progress Accounting

## 1. Source of truth
- GitHub branch refs and commit SHAs are the source of truth for code state.
- GitHub Actions run/job records and retained artifacts are the source of truth for CI state.
- The central completion ledger is the source of truth for response-completion counts.
- Agent-authored dashboards are summaries only and must never override these sources.

## 2. Task log
Each agent maintains task notes in its PR description or assigned issue. Use this format:

```markdown
## Task update
- Agent:
- Task ID:
- Status: planned | in_progress | blocked | review | done
- Branch:
- Base SHA:
- Head SHA:
- Scope:
- Files/components:
- Tests run:
- Results:
- Evidence links:
- Risks / blockers:
- Next action:
```

Update the issue/PR when status materially changes. Do not create noisy status-only commits.

## 3. Append-only completion ledger
Canonical location: `progress/completions.jsonl` (created by the coordinator when the new cohort is formally activated). One JSON object per line; UTF-8; no blank lines.

Required fields:
```json
{
  "completion_id": "ATLAS-01-000001",
  "agent_id": "ATLAS-01",
  "branch": "agent/01-fedora-base",
  "user_message_ref": "<stable conversation/message reference>",
  "response_summary": "<substantive work performed>",
  "evidence_refs": ["<commit, PR, issue, test run, or artifact URL>"],
  "recorded_at_utc": "2026-10-31T00:00:00Z",
  "record_version": 1
}
```
The timestamp above is illustrative only. Always write the actual UTC time when appending; never reuse the example.

Rules:
- IDs are sequential per agent, zero-padded to six digits, and never reused.
- One agent can receive at most one completion for one user message.
- A valid record requires substantive user-directed work and evidence. A status-only reply, acknowledgement, tool call, retry, commit, test, or file is not a completion by itself.
- The coordinator validates uniqueness, branch identity, user-message uniqueness, timestamp format, and evidence before append.
- Append only. Never edit, sort, renumber, backdate, delete, or silently repair existing records.
- Suspected duplicates or anomalies are flagged in an audit note and excluded pending review.
- Historical old-cohort records remain frozen and separate; do not merge their unresolved 124 vs 135 counts into the new cohort.

## 4. Dashboard
Every agent response ends with:

```text
### Progress
- Completions: X / 100 (X%)
- Remaining: 100 - X
- Commits: N (latest: <verified short SHA>)
- Branch: <assigned branch>
- Log: Updated | Pending

Progress bar: <20-cell bar computed from X%>
```

Only display a completion count after ledger validation. Commit count is the number of verified commits for that branch in the declared reporting interval; state the interval. If no verified commit exists, report `0 (latest: none)`. If ledger is not yet initialized, report `0 / 100` and `Log: Pending`; do not fabricate entries.

## 5. Audit
The coordinator periodically validates:
- JSONL parseability and required fields;
- unique completion IDs and unique agent/user-message pairs;
- strictly increasing sequence per agent;
- actual UTC timestamps and append order;
- evidence URLs/SHA references;
- branch-to-agent ownership;
- dashboard values against the ledger and Git refs.

Audit corrections are new append-only audit records; never rewrite source history.
