"""RFC 8785-compatible canonicalization for the supported I-JSON subset.
Strings are preserved exactly; floats, lone surrogates and unsafe integers fail closed.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any

class CanonicalizationError(ValueError):
    pass

def _string(value: str) -> str:
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError("invalid Unicode string") from exc
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

def _number(value: int | float) -> str:
    if isinstance(value, bool) or isinstance(value, float):
        raise CanonicalizationError("boolean or floating-point values are unsupported")
    if abs(value) > 9007199254740991:
        raise CanonicalizationError("integer outside interoperable safe range")
    return str(value)

def _encode(value: Any) -> str:
    if value is None: return "null"
    if value is True: return "true"
    if value is False: return "false"
    if isinstance(value, str): return _string(value)
    if isinstance(value, (int, float)): return _number(value)
    if isinstance(value, list): return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalizationError("object keys must be strings")
        for key in value: key.encode("utf-8", "strict")
        keys = sorted(value, key=lambda key: key.encode("utf-16-be", "strict"))
        return "{" + ",".join(_string(key) + ":" + _encode(value[key]) for key in keys) + "}"
    raise CanonicalizationError(f"unsupported JSON value: {type(value).__name__}")

def canonical_bytes(value: Any) -> bytes:
    try:
        return _encode(value).encode("utf-8", "strict")
    except (UnicodeEncodeError, TypeError) as exc:
        raise CanonicalizationError("value is not valid canonical JSON") from exc

def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()
