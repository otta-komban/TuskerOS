from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import os
import re
import shutil
import socket
import ssl
import uuid
from pathlib import Path
from typing import Callable, Mapping
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, build_opener

from .types import CancellationToken, RuntimeError as TuskerRuntimeError, RuntimeErrorCode

_SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")
_ARTIFACT_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
_REVISION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_CHUNK = 1024 * 1024


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _resolve_public_address(host: str, port: int) -> str:
    """Resolve once, reject every non-public answer, and return the IP to pin."""
    try:
        addresses = {ipaddress.ip_address(host)} if _is_ip(host) else {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        }
    except (OSError, ValueError):
        raise ValueError("model source host could not be safely resolved") from None
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("model source must resolve only to globally routable addresses")
    # The selected IP is used for the TCP connection; TLS still authenticates
    # the original hostname via SNI and certificate hostname verification.
    return str(sorted(addresses, key=lambda address: (address.version, int(address)))[0])


def _validate_remote_target(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("model source and redirects must be credential-free HTTPS URLs")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith((".localhost", ".local")):
        raise ValueError("model source must not resolve to a local host")
    _resolve_public_address(host, parsed.port or 443)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to the public IP resolved for this connection."""

    def __init__(self, host, *args, **kwargs):
        parsed = urlsplit("//" + host)
        if not parsed.hostname:
            raise ValueError("invalid HTTPS host")
        self._tls_hostname = parsed.hostname
        self._pinned_address = _resolve_public_address(parsed.hostname, parsed.port or 443)
        super().__init__(host, *args, **kwargs)

    def connect(self):
        if self._tunnel_host:
            raise OSError("HTTPS proxy tunnels are disabled for model downloads")
        raw_socket = socket.create_connection(
            (self._pinned_address, self.port), self.timeout, self.source_address
        )
        context = self._context or ssl.create_default_context()
        self.sock = context.wrap_socket(raw_socket, server_hostname=self._tls_hostname)


class _PinnedHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(_PinnedHTTPSConnection, request)


class _HTTPSRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            _validate_remote_target(newurl)
        except ValueError:
            raise HTTPError(newurl, code, "Unsafe model download redirect", headers, fp) from None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_https(url: str, timeout: float):
    _validate_remote_target(url)
    opener = build_opener(ProxyHandler({}), _HTTPSRedirectHandler, _PinnedHTTPSHandler(context=ssl.create_default_context()))
    return opener.open(url, timeout=timeout)


class ModelStore:
    """Single-file, digest-pinned installer with explicit consent and fail-closed approval."""

    def __init__(self, root: str | Path, *, authorize: Callable[[str, str], bool] | None = None, max_artifact_bytes: int = 20 * 1024**3):
        self.root = Path(root).expanduser().absolute()
        self.authorize = authorize or (lambda _operation, _artifact: False)
        self.max_artifact_bytes = max_artifact_bytes
        if self.root.is_symlink():
            raise ValueError("managed model root must not be a symlink")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("managed model root must be a real directory")
        if self.root.stat().st_mode & 0o077:
            raise ValueError("managed model root must not be accessible by group or other users")
        self.models = self.root / "models"
        self.active = self.root / "active"
        self.staging = self.root / ".staging"
        for directory in (self.models, self.active, self.staging):
            directory.mkdir(mode=0o700, exist_ok=True)
            if directory.is_symlink() or not directory.resolve().is_relative_to(self.root.resolve()):
                raise ValueError("managed model directory escaped its root")
            if directory.stat().st_mode & 0o077:
                raise ValueError("managed model directories must be private")

    def install(self, manifest: Mapping, *, consent: bool, cancellation: CancellationToken | None = None) -> Path:
        artifact_id, revision, filename, size, digest, source = self._validate_manifest(manifest)
        token = cancellation or CancellationToken()
        if not consent:
            raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Explicit model download consent is required")
        if not self.authorize("model.install", artifact_id):
            raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Model installation was not authorized")
        if token.cancelled:
            raise TuskerRuntimeError(RuntimeErrorCode.CANCELLED, "Model installation was cancelled")

        txid = uuid.uuid4().hex
        stage = self.staging / txid
        stage.mkdir(mode=0o700)
        staged_file = stage / filename
        actual_size = 0
        hasher = hashlib.sha256()
        try:
            with _open_https(source, timeout=15) as response, staged_file.open("xb") as output:
                while True:
                    if token.cancelled:
                        raise TuskerRuntimeError(RuntimeErrorCode.CANCELLED, "Model installation was cancelled")
                    chunk = response.read(_CHUNK)
                    if not chunk:
                        break
                    actual_size += len(chunk)
                    if actual_size > size or actual_size > self.max_artifact_bytes:
                        raise TuskerRuntimeError(RuntimeErrorCode.INTEGRITY_CHECK_FAILED, "Downloaded model exceeds its declared size")
                    hasher.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if actual_size != size or hasher.hexdigest().lower() != digest.lower():
                raise TuskerRuntimeError(RuntimeErrorCode.INTEGRITY_CHECK_FAILED, "Downloaded model failed size or SHA-256 verification")
            os.chmod(staged_file, 0o400)
            if token.cancelled:
                raise TuskerRuntimeError(RuntimeErrorCode.CANCELLED, "Model installation was cancelled")

            pointer = self.active / f"{artifact_id}.json"
            previous_pointer = None
            if pointer.is_symlink():
                raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Active model pointer must not be a symlink")
            if pointer.exists():
                current = self.active_revision(artifact_id)
                if current is None or not self.verify_active(artifact_id):
                    raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Existing active model state is invalid; recovery is required")
                previous_pointer = pointer.read_bytes()

            destination = self.models / artifact_id / revision
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if destination.parent.is_symlink() or not destination.parent.resolve().is_relative_to(self.models.resolve()):
                raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Model destination escaped the managed root")
            if destination.exists() or destination.is_symlink():
                raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Model revision already exists")
            os.replace(stage, destination)
            self._fsync_dir(destination.parent)
            temporary = self.active / f".{artifact_id}.{txid}.tmp"
            payload = json.dumps({"artifact_id": artifact_id, "revision": revision, "filename": filename, "sha256": digest.lower()}, sort_keys=True).encode("utf-8")
            switched = False
            try:
                with temporary.open("xb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                # Cancellation is deferred across this atomic activation boundary.
                os.replace(temporary, pointer)
                switched = True
                self._fsync_dir(self.active)
            except Exception:
                if switched:
                    rollback = self.active / f".{artifact_id}.{txid}.rollback"
                    try:
                        if previous_pointer is None:
                            pointer.unlink(missing_ok=True)
                        else:
                            with rollback.open("xb") as handle:
                                handle.write(previous_pointer)
                                handle.flush()
                                os.fsync(handle.fileno())
                            os.replace(rollback, pointer)
                        self._fsync_dir(self.active)
                    except OSError:
                        # Leave both immutable revisions intact if rollback durability is uncertain.
                        pass
                raise
            finally:
                if temporary.exists():
                    temporary.unlink()
            return destination / filename
        except Exception:
            if stage.exists() and not stage.is_symlink():
                shutil.rmtree(stage)
            raise

    def active_revision(self, artifact_id: str) -> Mapping | None:
        if not _ARTIFACT_ID.fullmatch(artifact_id):
            raise ValueError("invalid artifact ID")
        pointer = self.active / f"{artifact_id}.json"
        if pointer.is_symlink() or not pointer.exists():
            return None
        try:
            data = json.loads(pointer.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None
        revision = data.get("revision")
        filename = data.get("filename")
        if data.get("artifact_id") != artifact_id or not isinstance(revision, str) or not _REVISION.fullmatch(revision):
            return None
        if not isinstance(filename, str) or Path(filename).name != filename or "/" in filename or "\\" in filename:
            return None
        candidate = self.models / artifact_id / revision
        if candidate.is_symlink() or not candidate.exists() or not candidate.resolve().is_relative_to(self.models.resolve()):
            return None
        if not isinstance(data.get("sha256"), str) or not _SHA256.fullmatch(data["sha256"]):
            return None
        return data

    def verify_active(self, artifact_id: str) -> bool:
        record = self.active_revision(artifact_id)
        if record is None:
            return False
        model_file = self.models / artifact_id / record["revision"] / record["filename"]
        if model_file.is_symlink() or not model_file.is_file():
            return False
        hasher = hashlib.sha256()
        try:
            with model_file.open("rb") as handle:
                for chunk in iter(lambda: handle.read(_CHUNK), b""):
                    hasher.update(chunk)
        except OSError:
            return False
        return hasher.hexdigest().lower() == record["sha256"].lower()

    def remove_revision(self, artifact_id: str, revision: str) -> None:
        if not _ARTIFACT_ID.fullmatch(artifact_id) or not _REVISION.fullmatch(revision):
            raise ValueError("invalid artifact ID or revision")
        if not self.authorize("model.remove", artifact_id):
            raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Model removal was not authorized")
        pointer = self.active / f"{artifact_id}.json"
        active = self.active_revision(artifact_id)
        if (pointer.exists() or pointer.is_symlink()) and active is None:
            raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Active model pointer is invalid; recovery is required")
        if active and active.get("revision") == revision:
            raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Deactivate a model before removing its active revision")
        target = self.models / artifact_id / revision
        if target.is_symlink() or not target.exists():
            raise TuskerRuntimeError(RuntimeErrorCode.MODEL_NOT_FOUND, "Model revision was not found")
        resolved = target.resolve()
        if not resolved.is_relative_to(self.models.resolve()):
            raise TuskerRuntimeError(RuntimeErrorCode.PERMISSION_DENIED, "Model path escaped the managed root")
        shutil.rmtree(resolved)
        self._fsync_dir(resolved.parent)

    def _validate_manifest(self, manifest: Mapping):
        try:
            artifact_id = manifest["artifact_id"]
            revision = manifest["revision"]
            source = manifest["source"]
            files = manifest["files"]
            license_info = manifest["license"]
            provenance = manifest["provenance"]
            review = manifest["review"]
            if not _ARTIFACT_ID.fullmatch(artifact_id) or not _REVISION.fullmatch(revision):
                raise ValueError
            parsed = urlsplit(source)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError
            if not isinstance(files, list) or len(files) != 1:
                raise ValueError
            file_info = files[0]
            filename = file_info["filename"]
            size = file_info["size_bytes"]
            digest = file_info["sha256"]
            if not isinstance(filename, str) or Path(filename).name != filename or filename in {"", ".", ".."} or "/" in filename or "\\" in filename or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,254}", filename):
                raise ValueError
            if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= self.max_artifact_bytes:
                raise ValueError
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                raise ValueError
            if license_info.get("review_status") != "approved" or review.get("catalog_status") not in {"candidate", "approved"}:
                raise ValueError
            if provenance.get("retrieved_from") != source or provenance.get("digest_verified") is not False:
                raise ValueError
            return artifact_id, revision, filename, size, digest, source
        except (KeyError, TypeError, AttributeError, ValueError):
            raise TuskerRuntimeError(RuntimeErrorCode.INVALID_REQUEST, "Model manifest is incomplete or does not meet installation policy") from None

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
