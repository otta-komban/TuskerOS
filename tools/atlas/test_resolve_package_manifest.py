"""Unit tests for the read-only ATLAS package resolver helpers."""
from __future__ import annotations

import importlib.util
import hashlib
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
            "bash-0:5.2.26-3.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm\n"
        )
        self.assertEqual(result, ("bash-0:5.2.26-3.fc44.x86_64", "fedora", "GPL-3.0-or-later", "bash-5.2.26-3.fc44.src.rpm", "https://www.gnu.org/software/bash/", "Packages/bash.rpm"))

    def test_duplicate_identical_rows_are_collapsed(self):
        row = "bash-0:5.2.26-3.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm"
        self.assertEqual(parse_query_matches(f"{row}\n{row}\n"), tuple(row.split("\t")))

    def test_same_nevra_from_multiple_repositories_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "ambiguous repository"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm\n"
                "bash-0:5.2.26-3.fc44.x86_64\tthird-party\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm\n"
            )

    def test_multiple_nevras_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "ambiguous NEVRA"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm\n"
                "bash-0:5.2.27-1.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.27-1.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm\n"
            )

    def test_malformed_query_row_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected"):
            parse_query_matches("bash-5.2.26-3.fc44.x86_64")

    def test_empty_query_output_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "no available match"):
            parse_query_matches("  \n")


    def test_missing_upstream_url_is_explicit_noassertion(self):
        result = parse_query_matches(
            "bash-0:5.2.26-3.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\t\tPackages/bash.rpm\n"
        )
        self.assertEqual(result[4], "NOASSERTION")
        self.assertEqual(result[5], "Packages/bash.rpm")

    def test_non_https_upstream_url_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "non-HTTPS upstream URL"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttp://example.invalid/bash\tPackages/bash.rpm"
            )

    def test_unrequested_package_name_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "outside requested name"):
            parse_query_matches(
                "bash-completion-0:2.11-1.fc44.noarch\tfedora\tGPL-2.0-or-later\tbash-2.11-1.fc44.src.rpm\thttps://github.com/scop/bash-completion\tPackages/bash-completion.rpm", "bash"
            )

    def test_unsupported_architecture_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unsupported architecture"):
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.aarch64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm", "bash"
            )


    def test_nonzero_epoch_is_preserved(self):
        self.assertEqual(
            parse_query_matches("kernel-core-2:6.12.1-1.fc44.x86_64\tfedora\tGPL-2.0-only\tkernel-6.12.1-1.fc44.src.rpm\thttps://www.kernel.org/\tPackages/kernel-core.rpm", "kernel-core"),
            ("kernel-core-2:6.12.1-1.fc44.x86_64", "fedora", "GPL-2.0-only", "kernel-6.12.1-1.fc44.src.rpm", "https://www.kernel.org/", "Packages/kernel-core.rpm"),
        )

    def test_expected_package_accepts_full_nevra(self):
        self.assertEqual(
            parse_query_matches(
                "bash-0:5.2.26-3.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm", "bash"
            ),
            ("bash-0:5.2.26-3.fc44.x86_64", "fedora", "GPL-3.0-or-later", "bash-5.2.26-3.fc44.src.rpm", "https://www.gnu.org/software/bash/", "Packages/bash.rpm"),
        )

    def test_expected_package_rejects_similarly_prefixed_package(self):
        with self.assertRaisesRegex(RuntimeError, "outside requested name"):
            parse_query_matches(
                "bash-completion-0:2.11-1.fc44.noarch\tfedora\tGPL-2.0-or-later\tbash-2.11-1.fc44.src.rpm\thttps://github.com/scop/bash-completion\tPackages/bash-completion.rpm", "bash"
            )


class PinnedManifestTests(unittest.TestCase):
    def test_pin_requires_all_provenance_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text(
                "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_sha256,rpm_license,source_rpm,source_repository_url,upstream_url\n"
                "base,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,GPL-3.0-or-later,bash-5.2.26-3.fc44.src.rpm,https://src.fedoraproject.org/rpms/bash,https://www.gnu.org/software/bash/\n",
                encoding="utf-8",
            )
            self.assertEqual(read_manifest(path, require_pins=True)[0]["pinned_nevra"], "bash-0:5.2.26-3.fc44.x86_64")

    def test_invalid_rpm_sha256_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text(
                "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_sha256,rpm_license,source_rpm,source_repository_url,upstream_url\n"
                "base,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,not-a-digest,GPL-3.0-or-later,bash-5.2.26-3.fc44.src.rpm,https://src.fedoraproject.org/rpms/bash,https://www.gnu.org/software/bash/\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "rpm_sha256"):
                read_manifest(path, require_pins=True)

    def test_invalid_source_rpm_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text(
                "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_sha256,rpm_license,source_rpm,source_repository_url,upstream_url\n"
                "base,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,GPL-3.0-or-later,bash.rpm,https://src.fedoraproject.org/rpms/bash,https://www.gnu.org/software/bash/\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "source_rpm"):
                read_manifest(path, require_pins=True)


    def test_non_fedora_source_repository_url_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text(
                "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_sha256,rpm_license,source_rpm,source_repository_url,upstream_url\n"
                "base,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,GPL-3.0-or-later,bash-5.2.26-3.fc44.src.rpm,https://example.invalid/rpms/bash,https://www.gnu.org/software/bash/\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "Fedora dist-git"):
                read_manifest(path, require_pins=True)

    def test_non_https_upstream_url_is_rejected_in_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.csv"
            path.write_text(
                "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_sha256,rpm_license,source_rpm,source_repository_url,upstream_url\n"
                "base,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,GPL-3.0-or-later,bash-5.2.26-3.fc44.src.rpm,https://src.fedoraproject.org/rpms/bash,http://example.invalid/bash\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "upstream_url"):
                read_manifest(path, require_pins=True)


class PinVerificationTests(unittest.TestCase):
    def setUp(self):
        self.digest = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        self.row = {
            "pinned_nevra": "bash-0:5.2.26-3.fc44.x86_64",
            "repository_id": "fedora",
            "rpm_license": "GPL-3.0-or-later",
            "source_rpm": "bash-5.2.26-3.fc44.src.rpm",
            "upstream_url": "https://www.gnu.org/software/bash/",
            "rpm_sha256": self.digest,
        }

    def verify(self, **overrides):
        values = {
            "nevra": "bash-0:5.2.26-3.fc44.x86_64",
            "repository": "fedora",
            "license": "GPL-3.0-or-later",
            "source_rpm": "bash-5.2.26-3.fc44.src.rpm",
            "upstream_url": "https://www.gnu.org/software/bash/",
            "rpm_sha256": self.digest,
        }
        values.update(overrides)
        verify_pin(
            self.row, values["nevra"], values["repository"], values["license"],
            values["source_rpm"], values["upstream_url"], values["rpm_sha256"]
        )

    def test_exact_nevra_repository_and_checksum_are_accepted(self):
        self.verify()

    def test_version_or_epoch_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match pinned value"):
            self.verify(nevra="bash-1:5.2.26-3.fc44.x86_64")

    def test_repository_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match pinned value"):
            self.verify(repository="updates")

    def test_license_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match pinned value"):
            self.verify(license="MIT")

    def test_source_rpm_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match pinned value"):
            self.verify(source_rpm="wrong-5.2.26-3.fc44.src.rpm")

    def test_upstream_url_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match pinned value"):
            self.verify(upstream_url="https://example.invalid/bash")

    def test_rpm_checksum_mismatch_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match pinned value"):
            self.verify(rpm_sha256="b" * 64)


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



class OfflineManifestValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.manifest = Path(self.temporary.name) / "manifest.csv"
        self.manifest.write_text(
            "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_sha256,rpm_license,source_rpm,source_repository_url,upstream_url\n",
            encoding="utf-8",
        )

    def test_header_only_manifest_is_valid_in_validate_only_mode(self):
        self.assertEqual(read_manifest(self.manifest, require_pins=True, allow_empty=True), [])

    def test_empty_manifest_is_rejected_for_resolution(self):
        with self.assertRaisesRegex(RuntimeError, "contains no package rows"):
            read_manifest(self.manifest, require_pins=True)

    def test_validate_only_cli_does_not_require_fedora_or_dnf5(self):
        with mock.patch("sys.argv", [
            "resolve-package-manifest.py",
            "--manifest", str(self.manifest),
            "--validate-only",
        ]):
            self.assertEqual(RESOLVER.main(), 0)

    def test_validate_only_rejects_missing_provenance_columns(self):
        self.manifest.write_text(
            "layer,package,owner,required,rationale\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(RuntimeError, "Manifest header"):
            read_manifest(self.manifest, require_pins=True, allow_empty=True)


class ResolverCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.manifest = self.root / "manifest.csv"
        self.output = self.root / "nested" / "resolution.json"
        self.snapshot_root = self.root / "snapshot"
        self.gpg_key = self.root / "fedora-key"
        self.gpg_key.write_text("fixture key", encoding="utf-8")
        (self.snapshot_root / "fedora" / "repodata").mkdir(parents=True)
        (self.snapshot_root / "fedora" / "repodata" / "repomd.xml").write_text("<repomd/>", encoding="utf-8")
        rpm_path = self.snapshot_root / "fedora" / "Packages" / "bash.rpm"
        rpm_path.parent.mkdir(parents=True)
        rpm_path.write_bytes(b"fixture RPM payload")
        self.rpm_sha256 = hashlib.sha256(rpm_path.read_bytes()).hexdigest()
        self.manifest.write_text(
            "layer,package,owner,required,rationale,pinned_nevra,repository_id,repository_snapshot,rpm_sha256,rpm_license,source_rpm,source_repository_url,upstream_url\n"
            f"base-core,bash,ATLAS-01,true,base shell,bash-0:5.2.26-3.fc44.x86_64,fedora,compose-20261031,{self.rpm_sha256},GPL-3.0-or-later,bash-5.2.26-3.fc44.src.rpm,https://src.fedoraproject.org/rpms/bash,https://www.gnu.org/software/bash/\n",
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
                "--snapshot-root", str(self.snapshot_root),
                "--gpg-key", str(self.gpg_key),
            ]),
        ):
            return RESOLVER.main()

    def test_cli_success_writes_complete_json(self):
        query = "bash-0:5.2.26-3.fc44.x86_64\tfedora\tGPL-3.0-or-later\tbash-5.2.26-3.fc44.src.rpm\thttps://www.gnu.org/software/bash/\tPackages/bash.rpm"
        result = self.invoke_cli([
            "enabled repo evidence",
            query,
            "dnf5 version 5.2",
        ])
        self.assertEqual(result, 0)
        payload = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(payload["packages"][0]["package"], "bash")
        self.assertEqual(payload["packages"][0]["repository_id"], "fedora")
        self.assertEqual(payload["packages"][0]["rpm_sha256"], self.rpm_sha256)
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

    def test_repository_info_failure_does_not_create_output(self):
        failure = __import__("subprocess").CalledProcessError(1, ["dnf5", "repo", "info"])
        with self.assertRaises(__import__("subprocess").CalledProcessError):
            self.invoke_cli([failure])
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




class LocalSnapshotRepositoryTests(unittest.TestCase):
    def test_local_rpm_sha256_hashes_only_a_file_inside_the_local_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "fedora" / "Packages" / "bash.rpm"
            package.parent.mkdir(parents=True)
            package.write_bytes(b"local RPM payload")
            expected = hashlib.sha256(b"local RPM payload").hexdigest()
            self.assertEqual(RESOLVER.local_rpm_sha256(root, "fedora", "Packages/bash.rpm"), expected)

    def test_local_rpm_sha256_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fedora").mkdir()
            with self.assertRaisesRegex(RuntimeError, "Unsafe RPM package location"):
                RESOLVER.local_rpm_sha256(root, "fedora", "../outside.rpm")

    def test_local_rpm_sha256_rejects_missing_package_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "fedora").mkdir()
            with self.assertRaises(FileNotFoundError):
                RESOLVER.local_rpm_sha256(root, "fedora", "Packages/missing.rpm")

    def test_snapshot_args_select_only_local_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "fedora"
            key = root / "fedora-key"
            key.write_text("fixture", encoding="utf-8")
            (repo / "repodata").mkdir(parents=True)
            (repo / "repodata" / "repomd.xml").write_text("<repomd/>", encoding="utf-8")
            args = RESOLVER.snapshot_repo_args(root, {"fedora"}, key)
            self.assertEqual(len(args), 4)
            self.assertTrue(args[0].startswith("--repofrompath=fedora,file://"))
            self.assertIn("--setopt=fedora.gpgcheck=1", args)
            self.assertIn(f"--setopt=fedora.gpgkey={key.as_uri()}", args)
            self.assertIn("--repo=fedora", args)

    def test_snapshot_args_reject_missing_local_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / "fedora-key"
            key.write_text("fixture", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Local repository snapshot is missing"):
                RESOLVER.snapshot_repo_args(Path(directory), {"fedora"}, key)

    def test_snapshot_args_reject_invalid_repository_id(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / "fedora-key"
            key.write_text("fixture", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Invalid repository ID"):
                RESOLVER.snapshot_repo_args(Path(directory), {"../fedora"}, key)

    def test_snapshot_args_reject_empty_repository_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / "fedora-key"
            key.write_text("fixture", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "No package repositories"):
                RESOLVER.snapshot_repo_args(Path(directory), set(), key)


if __name__ == "__main__":
    unittest.main()
