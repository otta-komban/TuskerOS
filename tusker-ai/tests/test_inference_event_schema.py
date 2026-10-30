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

def test_event_specific_required_fields_and_unknown_properties_are_rejected():
    check = validator()
    missing_provider = dict(FIXTURE[0])
    del missing_provider["provider_id"]
    extra_property = dict(FIXTURE[1], unexpected=True)
    assert list(check.iter_errors(missing_provider))
    assert list(check.iter_errors(extra_property))


@pytest.mark.parametrize("mutation", [
    {"input_tokens": -1},
    {"output_tokens": -1},
    {"finish_reason": "invented"},
    {"retryable": "yes"},
])
def test_invalid_typed_event_fields_are_rejected(mutation):
    kind = "completed" if "finish_reason" in mutation else ("failed" if "retryable" in mutation else "usage")
    event = {
        "request_id": "req-negative",
        "sequence": 5,
        "timestamp": "2026-01-01T00:00:01Z",
        "type": kind,
    }
    if kind == "completed":
        event.update(finish_reason="stop")
    elif kind == "failed":
        event.update(code="provider_error", retryable=False)
    event.update(mutation)
    assert list(validator().iter_errors(event))


def test_trace_timestamps_are_non_decreasing():
    from datetime import datetime

    timestamps = [datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00")) for event in FIXTURE]
    assert timestamps == sorted(timestamps)


def test_trace_has_no_events_after_terminal():
    events = list(FIXTURE) + [dict(FIXTURE[1], sequence=4)]
    types = [event["type"] for event in events]
    terminals = {"completed", "cancelled", "failed"}
    terminal_positions = [i for i, kind in enumerate(types) if kind in terminals]
    assert len(terminal_positions) == 1
    assert terminal_positions[0] < len(types) - 1
