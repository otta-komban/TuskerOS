"""Static WCAG-style contrast checks for resolved theme color roles.

This is an isolated diagnostic utility. It does not change pack acceptance,
activation policy, or the shared theme contract. Alpha colors are reported as
not evaluated because their effective contrast depends on the rendered surface.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re


class AccessibilityAuditError(ValueError):
    """Raised when required semantic color roles are missing or malformed."""


@dataclass(frozen=True)
class ContrastCheck:
    foreground_role: str
    background_role: str
    minimum_ratio: float
    ratio: float | None
    status: str
    reason: str | None = None


_REQUIRED_ROLES = (
    "background",
    "surface",
    "surface_alt",
    "foreground",
    "muted",
    "accent",
    "accent_foreground",
    "border",
    "focus",
)
_HEX_COLOR = re.compile(r"^#[0-9A-Fa-F]{6}(?:[0-9A-Fa-f]{2})?$")


def _linear_channel(channel: int) -> float:
    value = channel / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _relative_luminance(color: str) -> float:
    if not isinstance(color, str) or not _HEX_COLOR.fullmatch(color):
        raise AccessibilityAuditError("colors must be #RRGGBB or #RRGGBBAA hex strings")
    if len(color) == 9:
        raise AccessibilityAuditError("alpha colors do not have a context-free luminance")
    red, green, blue = (
        _linear_channel(int(color[index:index + 2], 16))
        for index in (1, 3, 5)
    )
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """Return the WCAG relative-luminance contrast ratio for opaque sRGB colors."""
    first_luminance = _relative_luminance(first)
    second_luminance = _relative_luminance(second)
    lighter, darker = sorted((first_luminance, second_luminance), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def audit_theme_colors(colors: Mapping[str, str]) -> list[ContrastCheck]:
    """Audit semantic text, accent, focus and boundary color pairs.

    Text pairs use a 4.5:1 diagnostic threshold. Focus and boundary pairs use
    3:1. These are conservative static checks, not a substitute for rendered
    component testing or a complete WCAG conformance assessment.
    """
    if not isinstance(colors, Mapping):
        raise AccessibilityAuditError("colors must be a mapping")

    missing = [role for role in _REQUIRED_ROLES if role not in colors]
    if missing:
        raise AccessibilityAuditError("missing semantic color roles: " + ", ".join(missing))

    for role in _REQUIRED_ROLES:
        value = colors[role]
        if not isinstance(value, str) or not _HEX_COLOR.fullmatch(value):
            raise AccessibilityAuditError(f"invalid hex color for role: {role}")

    pairs = (
        ("foreground", "background", 4.5),
        ("foreground", "surface", 4.5),
        ("foreground", "surface_alt", 4.5),
        ("muted", "background", 4.5),
        ("muted", "surface", 4.5),
        ("accent_foreground", "accent", 4.5),
        ("focus", "background", 3.0),
        ("focus", "surface", 3.0),
        ("border", "surface", 3.0),
    )

    checks: list[ContrastCheck] = []
    for foreground_role, background_role, minimum in pairs:
        foreground = colors[foreground_role]
        background = colors[background_role]
        if len(foreground) == 9 or len(background) == 9:
            checks.append(ContrastCheck(
                foreground_role, background_role, minimum, None,
                "not_evaluated",
                "alpha channel requires the actual composited render surface",
            ))
            continue
        ratio = contrast_ratio(foreground, background)
        checks.append(ContrastCheck(
            foreground_role, background_role, minimum, ratio,
            "pass" if ratio >= minimum else "fail",
        ))
    return checks
