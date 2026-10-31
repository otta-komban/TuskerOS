# PIXEL-03 isolated accessibility audit

**Status:** Isolated test-only diagnostic; not a shared theme contract or pack-acceptance rule.

The test-only helper `tests/support/accessibility_audit.py` calculates contrast for the semantic color pairs currently present in theme-pack v1. It reports text-role pairs against a 4.5:1 threshold and focus pairs against a 3:1 threshold.

Alpha colors are marked `not_evaluated` because their effective luminance depends on the actual composited render surface. Border contrast is reported as `review`: the current pack data does not tell us whether a border is decorative or conveys a meaningful UI component boundary, so a rendered desktop review is required before applying a 3:1 criterion to it. Missing or malformed semantic roles raise a diagnostic error.

Run from the repository root:

```sh
python -m unittest theme-studio/tests/test_accessibility_audit.py -v
```

The test suite checks a known 21:1 reference pair, all three starter packs, a deliberately low-contrast pair, alpha handling, missing roles, malformed values and non-mapping input.

**Limitations:** This is not a complete WCAG audit. It does not inspect rendered text size, font weight, focus geometry, state changes, imagery, gradients, compositing, or the actual desktop output. It is test support only and is not imported by product runtime code; it does not gate pack validation or activation. Shared policy remains subject to Issue #50 and Chief Architect approval.
