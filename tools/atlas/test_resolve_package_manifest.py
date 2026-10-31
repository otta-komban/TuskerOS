"""Unit tests for the read-only ATLAS package resolver helpers."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

RESOLVER_PATH = Path(__file__).with_name("resolve-package-manifest.py")
SPEC = importlib.util.spec_from_file_location("atlas_package_resolver", RESOLVER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load resolver module from {RESOLVER_PATH}")
RESOLVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESOLVER)
parse_query_matches = RESOLVER.parse_query_matches
verify_pin = RESOLVER.verify_pin
write_json_atomic = RESOLVER.write_json_atomic
read_manifest = RESOLVER.read_manifest


class QueryResultTests(unittest.TestCase):
    def test_single_nevra_and_repository(self):
        result = parse_query_matches(
            "bash-0:5.2.26-3.fc44.x86_64\tfedora\n"
        )
        self.assertEqual(result, ("bash-0:5.2.26-3.fc44.x86_64", "fedora"))

    def test_duplicate_identical_rows_are_collapsed(self):
        row = "bash-0:5.2.26-3.fc44.x86_64\tfedora"
        self.assertEqual(parse_query_matches(f"{row}\n{row}\n"), tuple(row.split("\t")))

    def test_same_nevra_from_multiple_repositories_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "ambiguous repository"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora\n"
                "bash-0:5.2.26-3.fc44.x86_64\tthird-party\n"
            )

    def test_multiple_nevras_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "ambiguous NEVRA"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora\n"
                "bash-0:5.2.27-1.fc44.x86_64\tfedora\n"
            )

    def test_malformed_query_row_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected"):
            parse_query_matches("bash-5.2.26-3.fc44.x86_64")

    def test_empty_query_output_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "no available match"):
            parse_query_matches("  \n")

    def test_unrequested_package_name_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "outside requested name"):
            parse_query_matches(
                "bash-completion-0:2.11-1.fc44.noarch\tfedora", "bash"
            )

    def test_unsupported_architecture_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unsupported architecture"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.aarch64\tfedora", "bash"
            )


    def test_nonzero_epoch_is_preserved(self):
        self.assertEqual(
            parse_query_matches("kernel-core-2:6.12.1-1.fc44.x86_64\tfedora", "kernel-core"),
            ("kernel-core-2:6.12.1-1.fc44.x86_64", "fedora"),
        )

    def test_expected_package_accepts_full_nevra(self):
        self.assertEqual(
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora", "bash"
            ),
            ("bash-0:5.2.26-3.fc44.x86_64", "fedora"),
        )

    def test_expected_package_rejects_similarly_prefixed_package(self):
        with self.assertRaisesRegex(RuntimeError, "outside requested name"):
            parse_query_matches(
                "bash-completion-0:2.11-1.fc44.noarch\tfedora", "bash"
            )


class PinnedManifestTests(unittest.TestCase):
    def test_pin_requires_all_provenance_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text(
                "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_license,source_rpm,source_url\n"
                "base,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,GPL-3.0-or-later,bash-5.2.26-3.fc44.src.rpm,https://src.fedoraproject.org/rpms/bash\n",
                encoding="utf-8",
            )
            self.assertEqual(read_manifest(path, require_pins=True)[0]["pinned_nevra"], "bash-0:5.2.26-3.fc44.x86_64")

    def test_invalid_source_rpm_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text(
                "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_license,source_rpm,source_url\n"
                "base,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,GPL-3.0-or-later,bash.rpm,https://src.fedoraproject.org/rpms/bash\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "source_rpm"):
                read_manifest(path, require_pins=True)


class PinVerificationTests(unittest.TestCase):
    def setUp(self):
        self.row = {"pinned_nevra": "bash-0:5.2.26-3.fc44.x86_64", "repository_id": "fedora"}

    def test_exact_nevra_and_repository_are_accepted(self):
        verify_pin(self.row, "bash-0:5.2.26-3.fc44.x86_64", "fedora")

    def test_version_or_epoch_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match pinned NEVRA"):
            verify_pin(self.row, "bash-1:5.2.26-3.fc44.x86_64", "fedora")

    def test_repository_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match pinned repository"):
            verify_pin(self.row, "bash-0:5.2.26-3.fc44.x86_64", "updates")


class ManifestTests(unittest.TestCase):
    def read_text(self, content: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "manifest.csv"
        path.write_text(content, encoding="utf-8")
        return read_manifest(path)

    def test_valid_row_is_accepted(self):
        rows = self.read_text(
            "layer,package,owner,required,rationale\n"
            "desktop,bash,ATLAS-01,true,base shell\n"
        )
        self.assertEqual(rows[0]["package"], "bash")

    def test_empty_owner_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "owner must be non-empty"):
            self.read_text(
                "layer,package,owner,required,rationale\n"
                "desktop,bash,,true,base shell\n"
            )

    def test_empty_rationale_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "rationale must be non-empty"):
            self.read_text(
                "layer,package,owner,required,rationale\n"
                "desktop,bash,ATLAS-01,true,\n"
            )

    def test_duplicate_header_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unique, non-empty columns"):
            self.read_text(
                "layer,package,owner,required,rationale,rationale\n"
                "desktop,bash,ATLAS-01,true,base,duplicate\n"
            )

    def test_extra_csv_field_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "more fields than its header"):
            self.read_text(
                "layer,package,owner,required,rationale\n"
                "desktop,bash,ATLAS-01,true,base shell,unexpected\n"
            )

    def test_missing_csv_field_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "missing values"):
            self.read_text(
                "layer,package,owner,required,rationale\n"
                "desktop,bash,ATLAS-01,true\n"
            )

    def test_duplicate_package_in_layer_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Duplicate package in layer"):
            self.read_text(
                "layer,package,owner,required,rationale\n"
                "desktop,bash,ATLAS-01,true,base shell\n"
                "desktop,bash,ATLAS-01,true,duplicate request\n"
            )


class ResolverCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "manifest.csv"
        self.output = self.root / "nested" / "resolution.json"
        self.manifest.write_text(
            "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_license,source_rpm,source_url\n"
            "base-core,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,GPL-3.0-or-later,bash-5.2.26-3.fc44.src.rpm,https://src.fedoraproject.org/rpms/bash\n",
            encoding="utf-8",
        )

    def invoke_cli(self, run_side_effect):
        with (
            mock.patch.object(RESOLVER, "fedora_release", return_value="44"),
            mock.patch.object(RESOLVER.platform, "machine", return_value="x86_64"),
            mock.patch.object(RESOLVER, "shutil_which", return_value="/usr/bin/dnf5"),
            mock.patch.object(RESOLVER, "run", side_effect=run_side_effect),
            mock.patch("sys.argv", [
                "resolve-package-manifest.py",
                "--manifest", str(self.manifest),
                "--output", str(self.output),
            ]),
        ):
            return RESOLVER.main()

    def test_cli_success_writes_complete_json(self):
        query = "bash-0:5.2.26-3.fc44.x86_64\tfedora"
        result = self.invoke_cli([
            "enabled repo evidence",
            query,
            "dnf5 version 5.2",
        ])
        self.assertEqual(result, 0)
        payload = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(payload["packages"][0]["package"], "bash")
        self.assertEqual(payload["packages"][0]["repository_id"], "fedora")
        self.assertEqual(payload["enabled_repository_evidence"], "enabled repo evidence")

    def test_cli_resolution_failure_does_not_create_output(self):
        with self.assertRaisesRegex(RuntimeError, "Package resolution failed"):
            self.invoke_cli([
                "enabled repo evidence",
                "",
            ])
        self.assertFalse(self.output.exists())

    def test_cli_command_failure_does_not_create_output(self):
        failure = __import__("subprocess").CalledProcessError(1, ["dnf5", "repoquery"])
        with self.assertRaises(__import__("subprocess").CalledProcessError):
            self.invoke_cli([
                "enabled repo evidence",
                failure,
            ])
        self.assertFalse(self.output.exists())

    def test_atomic_writer_replaces_existing_file_with_valid_json(self):
        self.output.parent.mkdir(parents=True)
        self.output.write_text('{"old": true}\n', encoding="utf-8")
        write_json_atomic(self.output, {"new": True})
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), {"new": True})
        self.assertEqual(list(self.output.parent.glob("*.tmp")), [])

    def test_atomic_writer_preserves_previous_file_when_replace_fails(self):
        self.output.parent.mkdir(parents=True)
        self.output.write_text('{"old": true}\n', encoding="utf-8")
        with mock.patch.object(RESOLVER.os, "replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(OSError, "replace failed"):
                write_json_atomic(self.output, {"new": True})
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), {"old": True})
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])



if __name__ == "__main__":
    unittest.main()
