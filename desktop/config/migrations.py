"""Pure, fail-closed desktop settings schema migrations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any
CURRENT_SCHEMA_VERSION = 1

def migrate_settings(value: Any) -> tuple[dict[str, Any], list[str], bool]:
    """Return a v1 candidate, errors, and whether a legacy document was upgraded."""
    if not isinstance(value, dict):
        return {}, ["settings root must be a JSON object"], False
    source = deepcopy(value)
    version = source.pop("schema_version", 0)
    if isinstance(version, bool) or not isinstance(version, int):
        return {}, ["schema_version must be an integer"], False
    if version > CURRENT_SCHEMA_VERSION or version < 0:
        return {}, [f"unsupported settings schema version: {version}"], False
    if version == 0:
        source["schema_version"] = CURRENT_SCHEMA_VERSION
        return source, [], True
    source["schema_version"] = version
    return source, [], False
