import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/inference-event.schema.json").read_text())
FIXTURE = json.loads((ROOT / "tests/fixtures/inference-events-valid.json").read_text())


def validator():
    Draft202012Validator.check_schema(SCHEMA)
    return Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def test_valid_event_trace_matches_schema():
    check = validator()
    for event in FIXTURE:
        assert list(check.iter_errors(event)) == []


def test_trace_has_single_start_and_terminal_last():
    types = [event["type"] for event in FIXTURE]
    assert types.count("started") == 1
    terminals = {"completed", "cancelled", "failed"}
    terminal_positions = [i for i, kind in enumerate(types) if kind in terminals]
    assert len(terminal_positions) == 1
    assert terminal_positions[0] == len(types) - 1


def test_trace_sequence_is_strictly_increasing_and_request_scoped():
    assert len({event["request_id"] for event in FIXTURE}) == 1
    sequences = [event["sequence"] for event in FIXTURE]
    assert sequences == sorted(set(sequences))


@pytest.mark.parametrize("mutation", [
    {"sequence": -1},
    {"request_id": ""},
    {"type": "shell_command"},
    {"timestamp": "not-a-date"},
])
def test_invalid_event_envelopes_are_rejected(mutation):
    event = dict(FIXTURE[1])
    event.update(mutation)
    assert list(validator().iter_errors(event))
