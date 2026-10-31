# Response Completion Logging and Progress Accounting

## 1. The unit being counted

**One completion = one substantive, task-relevant assistant response in this agent chat.**

Count responses, not tasks, subtasks, commits, tests, files, milestones, log lines, or completion IDs:
- If one assistant response completes five tasks, it is still **1 completion**.
- If one assistant response reports several commits or test runs, it is still **1 completion**.
- A response labelled `C0010` is not automatically ten completions. It is only an identifier; the dashboard count is the number of validated response records.
- A substantive response to one user turn can contribute at most one completion for that agent.
- Acknowledgements, empty "continuing" messages, tool-only activity, retries, and status-only messages contribute **0**.

A completion is counted when the response has delivered a meaningful task-relevant result, such as an implementation/change, a verified investigation or decision, a tested fix, or a concrete blocker report with evidence. Do not inflate counts to reach 100.

## 2. Two-level append-only logging

### Agent-local response log

Each agent owns exactly one append-only file on its assigned branch:

`logs/completions/<AGENT-ID>.jsonl`

The agent appends **exactly one JSON object for each qualifying assistant response**, and never more than one for the same response. The file is the basis for that agent's local dashboard. The agent may write only its own file on its assigned branch.

### Canonical project ledger

The coordinator owns:

`progress/completions.jsonl`

This is the validated project-wide ledger. Agents must not edit it. The coordinator imports a local record only after checking the response evidence, branch, unique response ID, sequence, and one-record-per-response rule. The canonical ledger is append-only. The initial empty file means zero validated records, not a missing logging system.

The agent-local and canonical ledgers use the same record shape:

```json
{
  "completion_id": "PHOENIX-10-000001",
  "response_id": "unique UUID for this assistant response",
  "agent_id": "PHOENIX-10",
  "branch": "agent/10-installer-recovery",
  "response_summary": "One concise description of the substantive result in this response",
  "evidence_refs": [
    "https://github.com/otta-komban/TuskerOS/commit/<verified-sha>"
  ],
  "recorded_at_utc": "2026-10-31T00:00:00Z",
  "record_version": 1
}
```

The timestamp is illustrative. Use the actual UTC time. Never invent a timestamp, SHA, test result, URL, or response evidence. Use a UUID for `response_id`; it identifies one assistant response, not a task or milestone. Sequence `completion_id` per agent from 000001. If the response has no verifiable evidence yet, use a concrete issue/comment or branch-local artifact URL; otherwise do not claim a logged completion.

## 3. Exact counting procedure for every agent response

At the end of each substantive response:
1. Decide whether the response itself contains a meaningful task-relevant result. If not, add no record and do not increment.
2. If yes, append exactly one record to your own `logs/completions/<AGENT-ID>.jsonl` on your assigned branch.
3. Re-read the file and count valid JSONL records for your agent. Do not count task IDs, commits, tests, C-numbers, or milestones separately.
4. Report that count in the dashboard as the **agent-local count**. State `Log: Updated (branch-local; coordinator validation pending)` until imported into the canonical ledger.
5. If you cannot write the branch-local log, report `Log: Pending` and do not increment the displayed validated count. Explain the exact blocker.
6. The coordinator periodically validates and appends records to `progress/completions.jsonl`. Only then is the count marked canonical/validated.

Never claim that writing an issue comment or saying "C0010 recorded" updates the canonical ledger. A response record is not a task-completion record.

## 4. Dashboard

Every agent response ends with:

```text
### Progress
- Completions: X / 100 (Y%) — agent-local; Z canonical
- Remaining: 100 - X
- Commits: N (latest: <verified short SHA or none>)
- Branch: <assigned branch>
- Log: Updated (branch-local; coordinator validation pending) | Canonical | Pending

Progress bar: [<20 cells computed from X%>] Y%
```

Use `X` from the count of that agent's valid local response records, not from the current response's number of tasks. `Z` is the number of that agent's records present in the canonical ledger. If the local log does not exist or cannot be read, show `0 / 100` only if zero is verified; otherwise say `unknown` and `Log: Pending`. The remaining count is based on X. Percent is X percent because the target is 100.

Commit count is separate from completion count. Report only verified commits on the assigned branch and specify the reporting interval when it is not obvious. Never make up a commit count.

## 5. Coordinator validation

The coordinator validates:
- JSONL parseability and required fields;
- allowed agent ID and exact branch mapping;
- unique completion IDs and response IDs;
- sequential per-agent IDs with no gaps or reuse;
- UTC timestamps and append order;
- evidence references and actual GitHub state;
- at most one record per assistant response;
- dashboard values against local and canonical ledgers.

The coordinator must not turn one response into multiple completions because it mentions multiple deliverables. Duplicate or unsupported records are flagged and excluded; source logs are never rewritten to hide the issue.

## 6. Historical cohort

Old-cohort records remain frozen and separate. Do not merge the unresolved historical 124 vs 135 figures into this new cohort. The new cohort starts at zero canonical records; only verifiable new-cohort responses may be added.
