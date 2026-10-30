from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas/model-manifest.schema.json").read_text())
FIXTURE = json.loads((Path(__file__).parent / "fixtures/model-manifest-valid.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(SCHEMA)


def test_synthetic_manifest_fixture_is_valid():
    assert list(VALIDATOR.iter_errors(FIXTURE)) == []


@pytest.mark.parametrize("mutate", [
    lambda value: value.update(schema_version="9.9.9"),
    lambda value: value["files"][0].update(sha256="not-a-sha256"),
    lambda value: value["files"][0].update(size_bytes=0),
    lambda value: value["license"].update(review_status="approved-ish"),
    lambda value: value["model"].update(modalities=["telepathy"]),
    lambda value: value.update(unexpected_field=True),
])
def test_invalid_manifest_variants_are_rejected(mutate):
    candidate = deepcopy(FIXTURE)
    mutate(candidate)
    assert list(VALIDATOR.iter_errors(candidate))


def test_invalid_uri_format_is_rejected():
    candidate = deepcopy(FIXTURE)
    candidate["source"] = "not a URI"
    assert list(VALIDATOR.iter_errors(candidate))
