# Response completion logs

Each specialist agent owns only `logs/completions/<AGENT-ID>.jsonl` on its assigned branch. Append exactly one record for each substantive, task-relevant assistant response, regardless of how many tasks, commits, tests, or milestones that response mentions. Do not count a response more than once. The `completion_id` sequence is a record identifier, not a count of work items.

The canonical aggregate `progress/completions.jsonl` is coordinator-owned. Agents must never edit it. The coordinator validates and imports local records. Run:

```sh
python -m unittest discover -s tools/completions -p 'test_*.py' -v
python tools/completions/validate_ledger.py progress/completions.jsonl
```
