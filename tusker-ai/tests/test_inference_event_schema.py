import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/inference-event.schema.json").read_text())
FIXTURE = json.loads((ROOT / "tests/fixtures/inference-events-valid.json").read_text())


def validator():
    Draft202012Validator.check_schema(SCHEMA)
    return Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def trace_errors(events):
    """Return trace-level contract violations not expressible in per-event JSON Schema."""
    errors = []
    if not events:
        return ["trace is empty"]

    types = [event.get("type") for event in events]
    terminals = {"completed", "cancelled", "failed"}
    terminal_positions = [i for i, kind in enumerate(types) if kind in terminals]
    start_positions = [i for i, kind in enumerate(types) if kind == "started"]

    if start_positions != [0]:
        errors.append("trace must begin with exactly one started event")
    if len(terminal_positions) != 1:
        errors.append("trace must contain exactly one terminal event")
    elif terminal_positions[0] != len(events) - 1:
        errors.append("terminal event must be last")

    request_ids = {event.get("request_id") for event in events}
    if len(request_ids) != 1:
        errors.append("all events must share one request_id")

    sequences = [event.get("sequence") for event in events]
    if any(not isinstance(value, int) for value in sequences):
        errors.append("all sequence values must be integers")
    elif any(right <= left for left, right in zip(sequences, sequences[1:])):
        errors.append("sequence values must be strictly increasing")

    try:
        timestamps = [
            datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
            for event in events
        ]
        if any(right < left for left, right in zip(timestamps, timestamps[1:])):
            errors.append("timestamps must be non-decreasing")
    except (KeyError, TypeError, ValueError):
        errors.append("timestamps must be valid date-time strings")

    return errors


def test_valid_event_trace_matches_schema():
    check = validator()
    for event in FIXTURE:
        assert list(check.iter_errors(event)) == []


def test_valid_fixture_satisfies_trace_contract():
    assert trace_errors(FIXTURE) == []


@pytest.mark.parametrize("mutate", [
    lambda events: events.pop(0),
    lambda events: events.insert(1, deepcopy(events[0])),
    lambda events: events.append(deepcopy(events[1])),
    lambda events: events.append(deepcopy(events[-1])),
    lambda events: events[1].update(request_id="another-request"),
    lambda events: events[1].update(sequence=events[0]["sequence"]),
    lambda events: events[1].update(timestamp="2025-01-01T00:00:00Z"),
])
def test_invalid_trace_invariants_are_reported(mutate):
    events = deepcopy(FIXTURE)
    mutate(events)
    assert trace_errors(events)


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
