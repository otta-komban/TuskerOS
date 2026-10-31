"""Isolated tests for semantic theme-color contrast diagnostics."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "theme-studio" / "runtime"))

from accessibility_audit import (  # noqa: E402
    AccessibilityAuditError,
    audit_theme_colors,
    contrast_ratio,
)


class AccessibilityAuditTests(unittest.TestCase):
    def setUp(self):
        self.colors = {
            "background": "#17212D",
            "surface": "#263748",
            "surface_alt": "#34495B",
            "foreground": "#F4F7FA",
            "muted": "#B5C2CE",
            "accent": "#83C9E8",
            "accent_foreground": "#10212B",
            "border": "#688094",
            "focus": "#A6E3FF",
        }

    def test_known_wcag_contrast_example(self):
        self.assertAlmostEqual(contrast_ratio("#FFFFFF", "#000000"), 21.0, places=6)

    def test_starter_themes_pass_static_semantic_pairs(self):
        for path in sorted((ROOT / "themes").glob("*/theme.json")):
            with self.subTest(theme=path.parent.name):
                pack = json.loads(path.read_text(encoding="utf-8"))
                checks = audit_theme_colors(pack["tokens"]["colors"])
                self.assertTrue(checks)
                required = [check for check in checks if check.foreground_role != "border"]
                self.assertTrue(
                    all(check.status == "pass" for check in required),
                    [(check.foreground_role, check.background_role, check.ratio)
                     for check in required if check.status != "pass"],
                )
                border = next(check for check in checks if check.foreground_role == "border")
                self.assertEqual(border.status, "review")

    def test_low_contrast_text_pair_is_reported_as_failure(self):
        colors = {**self.colors, "foreground": "#777777", "surface": "#FFFFFF"}
        checks = audit_theme_colors(colors)
        target = next(
            check for check in checks
            if check.foreground_role == "foreground"
            and check.background_role == "surface"
        )
        self.assertEqual(target.status, "fail")
        self.assertLess(target.ratio, target.minimum_ratio)

    def test_alpha_color_is_reported_not_evaluated(self):
        colors = {**self.colors, "surface": "#26374880"}
        checks = audit_theme_colors(colors)
        target = next(
            check for check in checks
            if check.foreground_role == "foreground"
            and check.background_role == "surface"
        )
        self.assertEqual(target.status, "not_evaluated")
        self.assertIsNone(target.ratio)

    def test_missing_semantic_role_is_rejected(self):
        colors = dict(self.colors)
        del colors["focus"]
        with self.assertRaisesRegex(AccessibilityAuditError, "missing semantic"):
            audit_theme_colors(colors)

    def test_malformed_color_is_rejected(self):
        colors = {**self.colors, "accent": "url(unsafe)"}
        with self.assertRaisesRegex(AccessibilityAuditError, "invalid hex"):
            audit_theme_colors(colors)

    def test_non_mapping_input_is_rejected(self):
        with self.assertRaises(AccessibilityAuditError):
            audit_theme_colors([])


if __name__ == "__main__":
    unittest.main()
