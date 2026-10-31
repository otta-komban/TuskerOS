"""Fail-closed inspection of untrusted Theme Pack assets.

This module validates one asset at a time. Call inspect_pack_assets() before
making any asset visible to a desktop adapter. The pack directory must already
be staged in a private, non-writable location.
"""
from __future__ import annotations

import hashlib
import os
import re
import stat
from pathlib import Path, PurePosixPath

class AssetInspectionError(ValueError):
    """Raised when an asset cannot be proven safe to consume."""

MAX_FILE_BYTES = {
    "wallpaper": 32 * 1024 * 1024,
    "icon": 4 * 1024 * 1024,
    "font": 8 * 1024 * 1024,
    "sound": 16 * 1024 * 1024,
    "illustration": 8 * 1024 * 1024,
}
MAX_PACK_BYTES = 128 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024

SIGNATURES = {
    "image/png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "image/webp": lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP",
    "font/ttf": lambda b: b.startswith(b"\x00\x01\x00\x00"),
    "font/otf": lambda b: b.startswith(b"OTTO"),
    "font/woff2": lambda b: b.startswith(b"wOF2"),
    "audio/ogg": lambda b: b.startswith(b"OggS"),
    "audio/wav": lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WAVE",
}
ALLOWED_KIND_TYPES = {
    "wallpaper": {"image/png", "image/jpeg", "image/webp"},
    "icon": {"image/png", "image/jpeg", "image/webp"},
    "illustration": {"image/png", "image/jpeg", "image/webp"},
    "font": {"font/ttf", "font/otf", "font/woff2"},
    "sound": {"audio/ogg", "audio/wav"},
}
SAFE_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*$")

def _safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not SAFE_PATH.fullmatch(value):
        raise AssetInspectionError("asset path is not a safe relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise AssetInspectionError("asset path contains traversal")
    return path

def _open_contained(root: Path, relative: PurePosixPath) -> tuple[int, Path]:
    root_real = root.resolve(strict=True)
    candidate = root_real.joinpath(*relative.parts)
    # Resolve every component before opening; reject symlinks, including links
    # that happen to point back inside the pack, to keep pack semantics simple.
    cursor = root_real
    for part in relative.parts:
        cursor = cursor / part
        try:
            mode = cursor.lstat().st_mode
        except OSError as exc:
            raise AssetInspectionError("asset path is missing or unreadable") from exc
        if stat.S_ISLNK(mode):
            raise AssetInspectionError("symlink assets are not permitted")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root_real)
    except ValueError as exc:
        raise AssetInspectionError("asset escapes pack root") from exc
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(resolved, flags)
    except OSError as exc:
        raise AssetInspectionError("asset could not be opened safely") from exc
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise AssetInspectionError("asset must be a regular file")
    return fd, resolved

def inspect_asset(pack_root: str | Path, asset: dict) -> dict:
    """Verify containment, regular-file status, bounded size, type and SHA-256."""
    kind, media_type = asset.get("kind"), asset.get("media_type")
    if kind not in ALLOWED_KIND_TYPES or media_type not in ALLOWED_KIND_TYPES[kind]:
        raise AssetInspectionError("asset kind and media type are incompatible")
    relative = _safe_relative_path(asset.get("path"))
    fd, resolved = _open_contained(Path(pack_root), relative)
    limit = MAX_FILE_BYTES[kind]
    digest = hashlib.sha256()
    total = 0
    prefix = b""
    try:
        info = os.fstat(fd)
        if info.st_size > limit:
            raise AssetInspectionError("asset exceeds per-kind size limit")
        while True:
            chunk = os.read(fd, CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > limit:
                raise AssetInspectionError("asset exceeds per-kind size limit")
            if len(prefix) < 32:
                prefix += chunk[:32 - len(prefix)]
            digest.update(chunk)
    finally:
        os.close(fd)
    if total == 0 or not SIGNATURES[media_type](prefix):
        raise AssetInspectionError("asset content does not match declared media type")
    expected = asset.get("sha256", "")
    actual = digest.hexdigest()
    if not re.fullmatch(r"[a-f0-9]{64}", expected) or actual != expected:
        raise AssetInspectionError("asset SHA-256 mismatch")
    return {"path": str(relative), "size_bytes": total, "sha256": actual,
            "media_type": media_type, "resolved_path": str(resolved)}

def inspect_pack_assets(pack_root: str | Path, assets: list[dict],
                        max_pack_bytes: int = MAX_PACK_BYTES) -> list[dict]:
    """Inspect all assets and enforce a cumulative unpacked-size ceiling."""
    results, seen_ids, total = [], set(), 0
    for asset in assets:
        asset_id = asset.get("id")
        if not isinstance(asset_id, str) or asset_id in seen_ids:
            raise AssetInspectionError("missing or duplicate asset ID")
        seen_ids.add(asset_id)
        result = inspect_asset(pack_root, asset)
        total += result["size_bytes"]
        if total > max_pack_bytes:
            raise AssetInspectionError("pack exceeds total unpacked asset limit")
        results.append({"id": asset_id, **result})
    return results
