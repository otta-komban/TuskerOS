"""Installer-side regression fixtures for the AEGIS RFC 8785 Unicode vectors.

These string-only checks are not a general JCS implementation or a production
approval-digest integration test.
"""
import hashlib
import json
import unittest


def canonical_string_object(value):
    """Serialize this deliberately limited string-only fixture as canonical UTF-8."""
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in value.items()
    ):
        raise TypeError("fixture accepts string-only JSON objects")
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    # Strict UTF-8 encoding rejects lone surrogate code points.
    return serialized.encode("utf-8", errors="strict")


class InstallerJCSUnicodeVectorTests(unittest.TestCase):
    def test_precomposed_unicode_vector_001(self):
        canonical = canonical_string_object({"name": "\u00e9"})
        self.assertEqual(canonical.hex(), "7b226e616d65223a22c3a9227d")
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(),
            "2f16b8477146a1b2ba7d6bb7cf7c9979c191cc2838a107dbf5f0d920b4cb3ba1",
        )

    def test_decomposed_unicode_vector_002(self):
        canonical = canonical_string_object({"name": "e\u0301"})
        self.assertEqual(canonical.hex(), "7b226e616d65223a2265cc81227d")
        self.assertEqual(
            hashlib.sha256(canonical).hexdigest(),
            "6a547588c4055916e090ed61467326046dd52810679d03bfb84d862a7123522e",
        )

    def test_canonically_equivalent_strings_remain_distinct(self):
        precomposed = canonical_string_object({"name": "\u00e9"})
        decomposed = canonical_string_object({"name": "e\u0301"})
        self.assertNotEqual(precomposed, decomposed)
        self.assertNotEqual(hashlib.sha256(precomposed).digest(),
                            hashlib.sha256(decomposed).digest())

    def test_unpaired_surrogate_is_rejected_before_digest(self):
        with self.assertRaises(UnicodeEncodeError):
            canonical_string_object({"name": "\ud800"})


if __name__ == "__main__":
    unittest.main()
