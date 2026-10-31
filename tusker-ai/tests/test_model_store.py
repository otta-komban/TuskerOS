import hashlib
import os
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

    def install_fixture(self):
        with patch("tusker_ai.model_store._open_https", return_value=Response(self.payload)):
            return self.store.install(self.manifest, consent=True)

    def test_download_verifies_digest_and_atomically_activates(self):
        path = self.install_fixture()
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
        path = self.install_fixture()
        path.chmod(0o600)
        path.write_bytes(b"tampered")
        self.assertFalse(self.store.verify_active("fixture-model"))

    def test_failed_active_pointer_fsync_rolls_back_previous_revision(self):
        self.install_fixture()
        second_payload = b"second verified revision"
        second = dict(self.manifest)
        second["revision"] = "rev-002"
        second["files"] = [{"filename": "model.gguf", "size_bytes": len(second_payload), "sha256": hashlib.sha256(second_payload).hexdigest()}]
        with (
            patch("tusker_ai.model_store._open_https", return_value=Response(second_payload)),
            patch.object(self.store, "_fsync_dir", side_effect=[None, OSError("simulated directory fsync failure"), None]),
        ):
            with self.assertRaises(OSError):
                self.store.install(second, consent=True)
        self.assertEqual(self.store.active_revision("fixture-model")["revision"], "rev-001")
        self.assertTrue(self.store.verify_active("fixture-model"))

    def test_failed_rollback_preserves_both_revisions_for_operator_recovery(self):
        self.install_fixture()
        second_payload = b"second verified revision"
        second = dict(self.manifest)
        second["revision"] = "rev-002"
        second["files"] = [{
            "filename": "model.gguf",
            "size_bytes": len(second_payload),
            "sha256": hashlib.sha256(second_payload).hexdigest(),
        }]
        real_replace = os.replace
        replace_calls = 0

        def fail_rollback(source, target):
            nonlocal replace_calls
            replace_calls += 1
            if replace_calls == 3:
                raise OSError("simulated rollback pointer replacement failure")
            return real_replace(source, target)

        with (
            patch("tusker_ai.model_store._open_https", return_value=Response(second_payload)),
            patch("tusker_ai.model_store.os.replace", side_effect=fail_rollback),
            patch.object(self.store, "_fsync_dir", side_effect=[None, OSError("activation fsync failure")]),
        ):
            with self.assertRaises(OSError):
                self.store.install(second, consent=True)

        self.assertTrue((self.store.models / "fixture-model" / "rev-001" / "model.gguf").exists())
        self.assertTrue((self.store.models / "fixture-model" / "rev-002" / "model.gguf").exists())
        self.assertEqual(self.store.active_revision("fixture-model")["revision"], "rev-002")
        report = self.store.inspect_recovery()
        self.assertIn("fixture-model/rev-001", report["orphan_revisions"])
        self.assertTrue(any(name.endswith(".rollback") for name in report["activation_temporary_files"]))
        self.assertTrue(report["requires_operator_review"])

    def test_active_revision_cannot_be_removed(self):
        self.install_fixture()
        with self.assertRaises(TuskerRuntimeError) as ctx:
            self.store.remove_revision("fixture-model", "rev-001")
        self.assertEqual(ctx.exception.code, RuntimeErrorCode.PERMISSION_DENIED)

    def test_remote_target_rejects_loopback_and_http(self):
        from tusker_ai.model_store import _validate_remote_target
        with self.assertRaises(ValueError):
            _validate_remote_target("https://127.0.0.1/model.gguf")
        with self.assertRaises(ValueError):
            _validate_remote_target("http://models.example.test/model.gguf")

    def test_recovery_inspection_is_read_only_and_finds_interrupted_entries(self):
        self.install_fixture()
        (self.store.staging / "interrupted-transaction").mkdir()
        (self.store.active / ".fixture-model.abandoned.tmp").write_text("{}")
        (self.store.active / ".fixture-model.abandoned.rollback").write_text("{}")
        orphan = self.store.models / "fixture-model" / "rev-orphan"
        orphan.mkdir()
        (orphan / "model.gguf").write_bytes(b"unreferenced")
        before = sorted(str(path.relative_to(self.store.root)) for path in self.store.root.rglob("*"))
        report = self.store.inspect_recovery()
        after = sorted(str(path.relative_to(self.store.root)) for path in self.store.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertEqual(report["staging_entries"], ["interrupted-transaction"])
        self.assertEqual(report["activation_temporary_files"], [
            ".fixture-model.abandoned.rollback", ".fixture-model.abandoned.tmp"
        ])
        self.assertEqual(report["active_pointers"], [{"artifact_id": "fixture-model", "state": "valid"}])
        self.assertEqual(report["orphan_revisions"], ["fixture-model/rev-orphan"])
        self.assertTrue(report["requires_operator_review"])

    def test_recovery_inspection_reports_symlinked_and_unexpected_revision_entries(self):
        self.install_fixture()
        revision = self.store.models / "fixture-model" / "rev-001"
        unexpected = revision / "extra.bin"
        unexpected.write_bytes(b"not in active manifest")
        linked = revision / "linked.bin"
        linked.symlink_to(unexpected)
        report = self.store.inspect_recovery()
        findings = {(item["name"], item["reason"]) for item in report["unsafe_entries"]}
        self.assertIn(("extra.bin", "unexpected_revision_content"), findings)
        self.assertIn(("linked.bin", "symlink"), findings)
        self.assertTrue(report["requires_operator_review"])
        self.assertTrue(unexpected.exists())
        self.assertTrue(linked.is_symlink())

    def test_recovery_inspection_reports_invalid_active_pointer(self):
        pointer = self.store.active / "fixture-model.json"
        pointer.write_text("{not-json")
        report = self.store.inspect_recovery()
        self.assertEqual(report["active_pointers"], [
            {"artifact_id": "fixture-model", "state": "invalid_pointer"}
        ])
        self.assertTrue(report["requires_operator_review"])
        self.assertTrue(pointer.exists())


if __name__ == "__main__":
    unittest.main()
