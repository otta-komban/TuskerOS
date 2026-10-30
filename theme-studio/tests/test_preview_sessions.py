import sys
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))
from profile_store import ProfileStore
from profile_composer import compose_profile
from preview_sessions import (
    PreviewCapacityError,
    PreviewSessionManager,
    PreviewSessionNotFound,
)


class FakeClock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class PreviewSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(Path(self.tmp.name) / "profiles.json")
        self.store.save_profile("work", {
            "name": "Work",
            "base_theme": {"id": "classic-glass", "version": "1.0.0"},
            "mixins": [],
            "mixin_winners": {},
            "overrides": {"colors": {"background": "#eeeeee"}},
        })
        self.store.activate_profile("work")
        self.catalog = {
            "classic-glass": {
                "kind": "theme", "version": "1.0.0",
                "tokens": {"colors": {"background": "#ffffff", "foreground": "#111111"}},
            }
        }
        self.clock = FakeClock()
        self.counter = iter(["preview-one", "preview-two", "preview-three"])
        self.manager = PreviewSessionManager(
            ttl_seconds=30, max_sessions=2, clock=self.clock,
            id_factory=lambda: next(self.counter),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_and_read_preview_without_changing_active_profile_or_store(self):
        before = self.store.path.read_bytes()
        result = compose_profile(self.store, self.catalog)
        preview = self.manager.create(result, owner_id="user-a")
        self.assertEqual(preview.profile_id, "work")
        self.assertEqual(preview.tokens["colors"]["background"], "#eeeeee")
        self.assertEqual(self.store.load()["active_profile"], "work")
        self.assertEqual(self.store.path.read_bytes(), before)
        fetched = self.manager.get(preview.session_id, owner_id="user-a")
        self.assertEqual(fetched.tokens, preview.tokens)

    def test_preview_is_detached_from_composition_and_returned_views(self):
        result = compose_profile(self.store, self.catalog)
        preview = self.manager.create(result, owner_id="user-a")
        preview.tokens["colors"]["background"] = "tampered"
        preview.provenance["colors.background"] = "tampered"
        result.tokens["colors"]["background"] = "also-tampered"
        fetched = self.manager.get("preview-one", owner_id="user-a")
        self.assertEqual(fetched.tokens["colors"]["background"], "#eeeeee")
        self.assertEqual(fetched.provenance["colors.background"], "profile")

    def test_owner_isolation_does_not_disclose_session(self):
        preview = self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        with self.assertRaises(PreviewSessionNotFound):
            self.manager.get(preview.session_id, owner_id="user-b")
        with self.assertRaises(PreviewSessionNotFound):
            self.manager.cancel(preview.session_id, owner_id="user-b")
        self.assertEqual(self.manager.count(), 1)

    def test_expired_session_is_unavailable_and_removed(self):
        preview = self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        self.clock.advance(30)
        with self.assertRaises(PreviewSessionNotFound):
            self.manager.get(preview.session_id, owner_id="user-a")
        self.assertEqual(self.manager.count(), 0)
        self.assertFalse(self.manager.cancel(preview.session_id, owner_id="user-a"))

    def test_cleanup_removes_only_expired_sessions(self):
        first = self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        self.clock.advance(20)
        second = self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        self.clock.advance(10)
        self.assertEqual(self.manager.cleanup_expired(), 1)
        self.assertEqual(self.manager.get(second.session_id, owner_id="user-a").session_id, "preview-two")
        with self.assertRaises(PreviewSessionNotFound):
            self.manager.get(first.session_id, owner_id="user-a")

    def test_capacity_is_bounded_and_expired_sessions_are_purged_before_rejecting(self):
        self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        with self.assertRaises(PreviewCapacityError):
            self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        self.clock.advance(30)
        replacement = self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        self.assertEqual(replacement.session_id, "preview-three")
        self.assertEqual(self.manager.count(), 1)

    def test_cancel_is_owner_scoped_and_idempotent_after_expiry(self):
        preview = self.manager.create(compose_profile(self.store, self.catalog), owner_id="user-a")
        self.assertTrue(self.manager.cancel(preview.session_id, owner_id="user-a"))
        self.assertFalse(self.manager.cancel(preview.session_id, owner_id="user-a"))
        self.assertEqual(self.manager.count(), 0)

    def test_invalid_configuration_and_owner_are_rejected(self):
        with self.assertRaises(ValueError):
            PreviewSessionManager(ttl_seconds=0)
        with self.assertRaises(ValueError):
            PreviewSessionManager(max_sessions=0)
        with self.assertRaises(ValueError):
            self.manager.create(compose_profile(self.store, self.catalog), owner_id=" ")

    def test_duplicate_session_id_is_rejected_without_overwriting(self):
        clock = FakeClock()
        manager = PreviewSessionManager(ttl_seconds=30, clock=clock, id_factory=lambda: "same-id")
        result = compose_profile(self.store, self.catalog)
        manager.create(result, owner_id="user-a")
        with self.assertRaisesRegex(Exception, "duplicate ID"):
            manager.create(result, owner_id="user-b")
        self.assertEqual(manager.count(), 1)


if __name__ == "__main__":
    unittest.main()
