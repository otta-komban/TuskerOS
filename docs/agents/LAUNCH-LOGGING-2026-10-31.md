# Launch cohort response logging

Cohort start UTC: 2026-10-31T13:23:57.715Z

One substantive, task-relevant assistant response in one agent chat = exactly one completion (maximum one per response). Count implementation, verified investigation/decision, tested fix or evidence-backed blocker. Do not count acknowledgements, empty continuations, status-only, tool-only work, retries, tasks, commits, tests, files, milestones or PRs.

Each agent writes only logs/launch-2026-10-31/<AGENT-ID>.jsonl. These new-chat logs start empty at this launch boundary. Earlier cohort logs remain preserved in their original paths and are not reset or rewritten.

Append exactly one JSON object per qualifying response:

{"completion_id":"ATLAS-01-000001","response_id":"<unique UUID>","agent_id":"ATLAS-01","branch":"01-ATLAS","response_summary":"Substantive result in this response","evidence_refs":["<verified commit/issue/PR URL>"],"recorded_at_utc":"<actual ISO-8601 UTC append time>","record_version":1}

Use actual values and a real UUID. Never invent SHA, tests, evidence or dates. Never backdate. If no commit exists, cite a verified issue/PR/file or blocker evidence.

## Procedure after each substantive response
1. Decide whether it qualifies; otherwise do not append/increment.
2. Append exactly one record to your own file.
3. Re-read/parse the full file; verify required fields, unique response IDs and sequential IDs.
4. Count valid records; report as agent-local. Canonical count is pending until coordinator validates/imports.
5. If write/validation fails, report Log: Pending; do not claim count updated.

Never edit progress/completions.jsonl or another agent's log. Coordinator alone validates/imports canonical records. Keep legacy logs unchanged.

## Dashboard

### Progress
- Completions: X / 100 (Y%) — launch-local; Z canonical
- Remaining: 100 - X
- Commits: N (latest: <verified short SHA or none>)
- Branch: <assigned NN-AGENT>
- Log: Updated (local; coordinator validation pending) | Canonical | Pending

Progress bar: [<20 cells computed from X%>] Y%

Compute X from valid records, not sequence labels or tasks. Commit count is separate. First read/ack response is not automatically a completion; it counts only if substantive work is delivered. Never guess.
