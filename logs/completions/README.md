# Response completion logs

Each specialist agent owns only `logs/completions/<AGENT-ID>.jsonl` on its assigned branch. Append exactly one record for each substantive, task-relevant assistant response, regardless of how many tasks, commits, tests, or milestones that response mentions. Do not count a response more than once. The `completion_id` sequence is a record identifier, not a count of work items.

The canonical aggregate `progress/completions.jsonl` is coordinator-owned. Agents must never edit it. The coordinator validates and imports local records. Run:

```sh
python -m unittest discover -s tools/completions -p 'test_*.py' -v
python tools/completions/validate_ledger.py progress/completions.jsonl
```


## Coordinator records

The coordinator records its own qualifying responses in the canonical `progress/completions.jsonl` ledger using `agent_id: "COORDINATOR"`, `branch: "main"`, and sequential IDs `COORDINATOR-000001`, `COORDINATOR-000002`, and so on. These records count toward the project target but are reported separately from the ten specialist-agent quotas. Do not create a fake specialist-agent identity or write coordinator entries into an agent-local log. Late-recorded responses use the actual append timestamp and evidence links to the original repository actions.
