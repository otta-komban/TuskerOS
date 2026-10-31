import hashlib
import tempfile
import unittest
from unittest.mock import patch

from tusker_ai.model_store import ModelStore
from tusker_ai.types import CancellationToken, RuntimeError as TuskerRuntimeError, RuntimeErrorCode


class Response:
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def __enter__(self): return self
    def __exit__(self, *args): return False

    def read(self, size):
        part = self.data[self.offset:self.offset + size]
        self.offset += len(part)
        return part


class ModelStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.payload = b"verified local model fixture"
        self.manifest = {
            "artifact_id": "fixture-model", "revision": "rev-001", "source": "https://models.example.test/model.gguf",
            "files": [{"filename": "model.gguf", "size_bytes": len(self.payload), "sha256": hashlib.sha256(self.payload).hexdigest()}],
            "license": {"review_status": "approved"}, "provenance": {"digest_verified": False, "retrieved_from": "https://models.example.test/model.gguf"},
            "review": {"catalog_status": "approved"},
        }
        self.store = ModelStore(self.temp.name, authorize=lambda op, artifact: True)

    def tearDown(self):
        self.temp.cleanup()

    def test_download_verifies_digest_and_atomically_activates(self):
        with patch("tusker_ai.model_store._open_https", return_value=Response(self.payload)):
            path = self.store.install(self.manifest, consent=True)
        self.assertEqual(path.read_bytes(), self.payload)
        self.assertEqual(self.store.active_revision("fixture-model")["revision"], "rev-001")
        self.assertEqual(path.stat().st_mode & 0o777, 0o400)
        self.assertTrue(self.store.verify_active("fixture-model"))

    def test_digest_mismatch_never_activates(self):
        bad = dict(self.manifest)
        bad["files"] = [dict(self.manifest["files"][0], sha256="0" * 64)]
        with patch("tusker_ai.model_store._open_https", return_value=Response(self.payload)):
            with self.assertRaises(TuskerRuntimeError) as ctx:
                self.store.install(bad, consent=True)
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.INTEGRITY_CHECK_FAILED)
        self.assertIsNone(self.store.active_revision("fixture-model"))

    def test_download_requires_explicit_consent(self):
        with self.assertRaises(TuskerRuntimeError) as ctx:
            self.store.install(self.manifest, consent=False)
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.PERMISSION_DENIED)

    def test_download_requires_aegis_authorization_callback(self):
        denied = ModelStore(self.temp.name + "/denied")
        with self.assertRaises(TuskerRuntimeError) as ctx:
            denied.install(self.manifest, consent=True)
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.PERMISSION_DENIED)

    def test_cancel_before_download_does_not_stage(self):
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(TuskerRuntimeError) as ctx:
            self.store.install(self.manifest, consent=True, cancellation=token)
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.CANCELLED)
        self.assertEqual(list(self.store.staging.iterdir()), [])

    def test_cancel_during_download_cleans_staging(self):
        token = CancellationToken()
        class CancellingResponse(Response):
            def read(inner, size):
                part = super(CancellingResponse, inner).read(size)
                token.cancel()
                return part
        with patch("tusker_ai.model_store._open_https", return_value=CancellingResponse(self.payload)):
            with self.assertRaises(TuskerRuntimeError) as ctx:
                self.store.install(self.manifest, consent=True, cancellation=token)
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.CANCELLED)
        self.assertEqual(list(self.store.staging.iterdir()), [])

    def test_manifest_rejects_path_traversal(self):
        bad = dict(self.manifest)
        bad["files"] = [dict(self.manifest["files"][0], filename="../escape.gguf")]
        with self.assertRaises(TuskerRuntimeError):
            self.store.install(bad, consent=True)

    def test_verify_active_detects_post_install_tampering(self):
        with patch("tusker_ai.model_store._open_https", return_value=Response(self.payload)):
            path = self.store.install(self.manifest, consent=True)
        path.chmod(0o600)
        path.write_bytes(b"tampered")
        self.assertFalse(self.store.verify_active("fixture-model"))

    def test_active_revision_cannot_be_removed(self):
        with patch("tusker_ai.model_store._open_https", return_value=Response(self.payload)):
            self.store.install(self.manifest, consent=True)
        with self.assertRaises(TuskerRuntimeError) as ctx:
            self.store.remove_revision("fixture-model", "rev-001")
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.PERMISSION_DENIED)

    def test_remote_target_rejects_loopback_and_http(self):
        from tusker_ai.model_store import _validate_remote_target
        with self.assertRaises(ValueError):
            _validate_remote_target("https://127.0.0.1/model.gguf")
        with self.assertRaises(ValueError):
            _validate_remote_target("http://models.example.test/model.gguf")


if __name__ == "__main__":
    unittest.main()
