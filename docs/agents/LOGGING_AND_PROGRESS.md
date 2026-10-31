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

## 6. New-cohort start boundary and historical records

The controlled new-cohort implementation window begins at **2026-10-31T07:39:00Z**, the verified suspension-lift time in Issue #34. Count only qualifying assistant responses after this timestamp. Responses and log entries before it belong to the frozen historical cohort, even if they appear in a replacement branch or use a new branch name.

Do not renumber, delete, or rewrite historical entries. In a legacy log whose IDs continue from the old cohort, derive the new-cohort dashboard count only from qualifying response records timestamped at or after the start boundary. The sequence label is not the count: for example, PHOENIX-10 C0010 at 07:42:02Z is new-cohort completion 1, and C0011 at 07:50:30Z is new-cohort completion 2. Earlier C0001-C0009 remain excluded.

If a qualifying post-boundary response was not logged at the time, the agent may append a clearly identified late-recorded entry using the actual current append timestamp and a reference to the original response evidence. Never backdate the record. The coordinator audits the original response time from the evidence reference and prevents duplicate counting.

Old-cohort figures 124/1,000 and 135/1,000 remain frozen, separate, and unreconciled. The new cohort starts at zero at the boundary above; only validated post-boundary response records count.


## 7. Coordinator completions and project target

The coordinator is a separate counted contributor. Its qualifying substantive responses are recorded directly in the canonical `progress/completions.jsonl` ledger with `agent_id: "COORDINATOR"`, `branch: "main"`, and sequential IDs `COORDINATOR-000001` onward. The validator treats this as a distinct actor; coordinator records must not be attributed to one of the ten specialist agents or written into their local files.

Coordinator completions count toward the shared 1,000-completion project target, while each specialist agent retains its own 100-completion sub-target. Report specialist-agent subtotal and coordinator subtotal separately, then show their combined project total. The denominator remains 1,000; do not increase it merely because coordinator work is counted. Late records use the actual append timestamp and evidence references to the original response/repository action. Do not backdate them.
