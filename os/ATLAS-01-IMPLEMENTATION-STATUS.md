# ATLAS-01 Fedora Base & Image Foundation — Implementation Status

**Task ID:** ATLAS-01-FEDORA-BASE-001  
**Status:** In progress  
**Branch:** `agent/01-fedora-base`  
**Implementation base SHA:** `8bf66079f9e021244eda432fa8455e83b59e2165`  
**Latest code/test evidence head:** `8f594cb13a9360eaa11a2f32e2d78654bf4d00fc` (ATLAS CI passed 70 tests; unified validation passed all 8 jobs; branch 82 commits ahead / 0 behind `main`)  
**Initial branch/base verification:** assigned branch and live `main` both pointed to the implementation base SHA above.

## Delivered in this milestone

- Added `os/image-source.lock.json` pinning Fedora's canonical KIWI descriptions source to the Fedora Forge `f44` branch commit `dfc49a5a10f69941179fdadd96aa6a5984f7c677`.
- Verified the upstream source contains `Fedora.kiwi`, `kiwi-build`, and `teams/kde.xml`; the KDE profile names are `KDE-Desktop-Live` (ISO) and `KDE-Desktop-Disk` (OEM disk).
- Recorded upstream Git blob IDs for the root description, wrapper and KDE profile in the lock. The upstream commit is **not GPG-verified**; the lock establishes immutable content identity, not a trusted signature.
- Added `tools/atlas/build-image.sh`. It checks Fedora 44/x86_64 prerequisites, checks out the immutable upstream commit, verifies the three source blob IDs, resolves the manifest, builds the ISO and disk targets, writes SHA-256 checksums and build metadata, and optionally compares a second build's checksums.
- Extended the package CSV header with exact NEVRA, repository ID/snapshot label, RPM license, source RPM and HTTPS source URL fields.
- Hardened the resolver's production path to require all provenance fields and compare the resolved NEVRA and repository against the exact manifest pins. Existing helper tests remain compatible with their smaller fixture format.
- Added nonzero-epoch, pin mismatch, repository mismatch, source RPM validation and source-lock structural tests.  
- Added CI checks for JSON lock parsing and `bash -n` validation of the image build script.
- Corrected the Fedora KIWI wrapper invocation: both image profiles now pass a fixed `--image-release=0`, which causes the wrapper to export result bundles into the requested output directories. Intermediate `*-build` trees are removed before checksum calculation; the script now requires an `.iso` and `.qcow2` bundle and hashes only exported artifacts.
- Added static build-script regression tests for the wrapper's output/export contract. These checks do not execute KIWI.
- Hardened DNF5 metadata parsing to use `%{full_nevra}` (which preserves epoch 0), `%{repoid}`, `%{license}`, `%{sourcerpm}` and `%{url}`. The resolver compares NEVRA, repository, license, source RPM and upstream URL metadata with the manifest pins. The manifest separately records the Fedora dist-git source repository URL and upstream project URL.
- The resolver preserves an empty fifth query field and normalizes a missing upstream URL to the explicit `NOASSERTION` sentinel rather than dropping the trailing tab or silently inventing a URL.
- Added offline `--validate-only` mode: CI validates the real manifest header and provenance columns even while it has zero rows; normal resolution still fails closed on an empty package list.
- Unit tests use mocked DNF5 output on Ubuntu, and a separate Fedora 44 container smoke now validates the real DNF5 queryformat and metadata fields. The production resolver still has not processed an owner-approved non-empty manifest.
- Changed build metadata so a matching second build is reported as `repeat_build_checksum_comparison: passed`; `reproducible_build_claim` remains `false` until KIWI/DNF consume a frozen repository snapshot and RPM payload checksums are locked.
- Corrected the ATLAS workflow's branch filters so push validation runs on `agent/01-fedora-base` and PR validation targets `main`.
- Added `os/repository-snapshot.lock.json` and `tools/atlas/verify-repository-snapshot.py` to capture and preflight-check Fedora 44 `repomd.xml` plus primary metadata SHA-256 identities. The verifier rejects digest drift, malformed/unsafe metadata paths, non-HTTPS URLs and repository-origin escapes.
- Added package-manifest snapshot binding: every build package row must reference the exact `snapshot_id` recorded for its repository in the lock.
- Gated `build-image.sh` on repository snapshot preflight verification and recorded `repository_snapshot_consumed_by_kiwi: false`; this deliberately does not claim the later KIWI/DNF package download is already frozen to those bytes. Metadata signature verification, RPM payload checksums and actual KIWI consumption of an immutable local snapshot remain open.

## Repository snapshot preflight

- Lock: `os/repository-snapshot.lock.json`; it is intentionally empty until NOVA-02/NEXUS-07 approve package inputs and the selected Fedora repository endpoints are reviewed.
- Capture reviewed endpoints with `python3 tools/atlas/verify-repository-snapshot.py --capture REPO_ID=REPOMD_URL --lock os/repository-snapshot.lock.json`. Repeat `--capture` for each approved repository in one invocation; the command fetches `repomd.xml` and its primary metadata and records SHA-256 identities.
- Verify the committed lock and manifest pins with `python3 tools/atlas/verify-repository-snapshot.py --lock os/repository-snapshot.lock.json --manifest os/package-manifest.csv`.
- Current verifier pins `repomd.xml` and primary metadata only, and uses HTTPS transport during capture; it does not verify Fedora GPG signatures or freeze the later KIWI/DNF downloads.

## Pull request

- Draft PR: [#59 — ATLAS-01 Fedora base resolver and KIWI image foundation](https://github.com/otta-komban/TuskerOS/pull/59)
- Last validated code head: `8f594cb13a9360eaa11a2f32e2d78654bf4d00fc`; PR base: `8bf66079f9e021244eda432fa8455e83b59e2165`.
- Draft remains open for review. ATLAS run 41185951919 passed 70 tests and live Fedora 44 DNF5 smoke; unified validation run 41185951924 passed all 8 jobs on this exact head. Later changes update only status and completion logs. It is intentionally not merge-ready until package rows are approved, KIWI/DNF consume the frozen repository snapshot, metadata signatures and RPM payload checksums are verified, the image is built, and PHOENIX VM install/boot evidence is available.

## Evidence

### Resolver CI

- Run: [41180559864](https://github.com/otta-komban/TuskerOS/actions/runs/41180559864)
- Tested commit: `65b75c540dc4e461244378836517a87441da65fb`
- Runner: Ubuntu 24.04, CPython 3.12.15
- Exact commands:
  - `python -m py_compile tools/atlas/resolve-package-manifest.py tools/atlas/test_resolve_package_manifest.py`
  - `python -m unittest discover -s tools/atlas -p 'test_*.py' -v`
- Result: **28 tests passed**, exit code 0.
- Follow-up run: [41180649544](https://github.com/otta-komban/TuskerOS/actions/runs/41180649544), commit `e55e8a1944dc4e6e88bd496e236524530c6391c0`, passed all jobs.
- Exact follow-up commands:
  - `python -m py_compile tools/atlas/resolve-package-manifest.py tools/atlas/test_resolve_package_manifest.py tools/atlas/test_image_source_lock.py`
  - `python -m json.tool os/image-source.lock.json > /dev/null`
  - `bash -n tools/atlas/build-image.sh`
  - `python -m unittest discover -s tools/atlas -p 'test_*.py' -v`
- Result: **32 tests passed**, exit code 0; JSON lock validation and shell syntax validation also passed.
- Latest run: [41181333587](https://github.com/otta-komban/TuskerOS/actions/runs/41181333587), tested commit `32fba3efc6ab715e739cb6213944fcf61a4d24a9`.
- Exact commands: `python -m py_compile tools/atlas/resolve-package-manifest.py tools/atlas/test_resolve_package_manifest.py tools/atlas/test_image_source_lock.py tools/atlas/test_build_image_script.py`; `python -m json.tool os/image-source.lock.json > /dev/null`; `bash -n tools/atlas/build-image.sh`; `python -m unittest discover -s tools/atlas -p 'test_*.py' -v`.
- Result: **36 tests passed**, exit code 0. JSON and shell syntax checks passed. Four new tests are static build-script contract checks, not image-build tests.
- Resolver metadata pin run: [41181625107](https://github.com/otta-komban/TuskerOS/actions/runs/41181625107), commit `44bfe6b6350c79d9ab9caec5a0d613983ed5931b`, passed **39 tests** after fixing test fixtures for the expanded DNF5 query format.
- Latest previous run: [41181689969](https://github.com/otta-komban/TuskerOS/actions/runs/41181689969), commit `81e44a5adfddbc6781c24319b7920de67e3192e2`, passed **40 tests**, JSON validation and shell syntax validation.
- Current run: [41183352032](https://github.com/otta-komban/TuskerOS/actions/runs/41183352032), exact PR head `f763cd56a382a31c6206f42a3ecd402f077bd13d`, passed **49 tests**, package-manifest offline validation (0 rows), image-lock JSON validation, shell syntax, upstream source commit/blob verification and live Fedora 44 DNF5 smoke.
- Current PR unified validation: [41183355869](https://github.com/otta-komban/TuskerOS/actions/runs/41183355869), all 8 jobs passed on the same exact head.
- Current PR ATLAS validation: [41183355823](https://github.com/otta-komban/TuskerOS/actions/runs/41183355823), all steps passed on the same exact head.
- Exact current command set: `python -m py_compile tools/atlas/resolve-package-manifest.py tools/atlas/test_resolve_package_manifest.py tools/atlas/test_image_source_lock.py tools/atlas/test_build_image_script.py`; `python tools/atlas/resolve-package-manifest.py --validate-only --manifest os/package-manifest.csv`; `python -m json.tool os/image-source.lock.json > /dev/null`; `bash -n tools/atlas/build-image.sh`; `python -m unittest discover -s tools/atlas -p 'test_*.py' -v`.
- Exact latest commands: `python -m py_compile tools/atlas/resolve-package-manifest.py tools/atlas/test_resolve_package_manifest.py tools/atlas/test_image_source_lock.py tools/atlas/test_build_image_script.py`; `python -m json.tool os/image-source.lock.json > /dev/null`; `bash -n tools/atlas/build-image.sh`; `python -m unittest discover -s tools/atlas -p 'test_*.py' -v`.
- Two intermediate CI runs (`41181567432`, `41181595588`) failed because test fixtures still used the old two-column DNF query output / two-argument pin helper after the resolver began validating license and source RPM. Fixtures were corrected; subsequent 39- and 40-test runs passed.
- One preceding CI iteration (run `41180611540`) failed one newly added source-lock test due to an incorrect test-field lookup; the test was corrected and the next run passed.

### Pinned Fedora KIWI source verification

- The CI job fetches the immutable upstream commit `dfc49a5a10f69941179fdadd96aa6a5984f7c677` from Fedora Forge and verifies Git blob IDs for `Fedora.kiwi`, `kiwi-build` and `teams/kde.xml`.
- Latest evidence: run [41183352032](https://github.com/otta-komban/TuskerOS/actions/runs/41183352032); all three blob checks and commit identity passed.

### Live Fedora 44 DNF5 smoke

- Workflow job: [41183021284](https://github.com/otta-komban/TuskerOS/actions/runs/41183021284), job `fedora44-dnf5-smoke`, Fedora 44 container.
- DNF5/libdnf5: `5.4.3.0`.
- Exact query format exercised: `%{full_nevra}\t%{repoid}\t%{license}\t%{sourcerpm}\t%{url}`.
- Actual result: `bash-0:5.3.9-3.fc44.x86_64`, repository `fedora`, source RPM `bash-5.3.9-3.fc44.src.rpm`; the upstream URL field parsed successfully.
- This validates the DNF5 metadata format against a real Fedora 44 repository. It is not a full package-manifest resolution because the manifest has zero package rows, and it is not an image build.

### PR-head validation

- Unified validation: [41182404765](https://github.com/otta-komban/TuskerOS/actions/runs/41182404765), exact PR head `7c5b9ba6ddc130b8c625ba8af4a17c9ea4e65203`; all 8 jobs passed:
  - System integration contracts
  - Security contract validation
  - Fedora package resolver
  - Core contract schemas
  - AI model and inference contracts
  - Theme pack validation
  - Marketplace transaction lifecycle
  - Desktop static validation
- ATLAS PR workflow: [41182404795](https://github.com/otta-komban/TuskerOS/actions/runs/41182404795), same exact PR head; compile, JSON lock validation, shell syntax and all **45 tests** passed.

### Image/build/runtime status

- Image build: **not run**.
- Reproducibility comparison: **not run**.
- Image checksums: **not produced**.
- VM install/boot: **not tested**.
- Secure Boot: **not tested**.
- Physical hardware: **not tested**.

## Cross-agent review updates

- NEXUS-07 issue #5: ATLAS reviewed the provisional system-bus read-only API and service activation/packaging assumptions. Review comment: [6540691529](https://github.com/otta-komban/TuskerOS/issues/5#issuecomment-6540691529). The proposed reverse-DNS name remains provisional until project namespace ownership is confirmed; ATLAS will not invent NEXUS D-Bus identifiers or AEGIS Polkit action IDs.
- NOVA-02 issue #12: ATLAS reviewed Fedora 44 / Plasma 6 / Qt 6 / KF6 as the POC platform baseline, Wayland-first, and called out Plasma Login Manager/Setup rather than assuming SDDM-only behavior. Review comment: [6540691845](https://github.com/otta-komban/TuskerOS/issues/12#issuecomment-6540691845). A correction comment [6540716164](https://github.com/otta-komban/TuskerOS/issues/12#issuecomment-6540716164) supersedes the earlier 6.6.4 version citation: Fedora's current package index lists 6.7.5-1.fc44 stable for Plasma workspace, login manager and setup. Exact RPM NEVRAs remain snapshot-derived; no image/login test is claimed. ATLAS requested NOVA's explicit minimal-desktop package/comps list and Plasma Setup lifecycle in [comment 6540959722](https://github.com/otta-komban/TuskerOS/issues/12#issuecomment-6540959722); response pending.
- NEXUS-07 issue #5: ATLAS requested NEXUS-owned direct RPM dependencies for system capabilities/diagnostics, split by required/base, Tusker integration and optional layers in [comment 6540960034](https://github.com/otta-komban/TuskerOS/issues/5#issuecomment-6540960034); response pending.
- Issue #51 is retained as a CI configuration follow-up because `protect-main` currently lists no required status checks. Repository instructions do not prohibit assigned-branch commits on that basis; implementation has resumed. This does not authorize merging or bypassing PR review/check requirements.

## Explicit blockers and boundaries

1. `os/package-manifest.csv` intentionally has no package rows. The base-system proposal defers exact package selection until NOVA-02 and NEXUS-07 confirm dependencies. The resolver/build script fail closed rather than inventing package names or licenses.
2. A repository snapshot identifier is required in each future package row, but the current resolver records that declared value and repo evidence; it does **not yet fetch or verify immutable Fedora repodata bytes**. Bit-for-bit reproducible release builds remain blocked until the build consumes an immutable repository snapshot and validates its metadata digest.
3. The upstream Fedora Forge commit is unsigned/unverified according to its branch API response. Content blob IDs are checked, but upstream signature trust remains unresolved.
4. `source_url` is currently checked for HTTPS syntax but is not independently resolved/verified against Fedora dist-git. `repository_snapshot` is currently a required declaration, not a verified repodata digest. The build metadata explicitly prevents a reproducibility claim until those are implemented.
5. The Fedora 44 package index currently lists stable `6.7.5-1.fc44` for `plasma-workspace`, `plasma-login-manager` and `plasma-setup`; the earlier 6.6.4 release-article reference is stale for current package resolution. Exact RPM NEVRAs still come from the selected repository snapshot.
6. PHOENIX-10's installer boundary remains a separate handoff. No Anaconda install or destructive storage behavior is implemented here.

## PHOENIX-10 handoff

The shared POC candidate is Fedora 44, mutable RPM/DNF, x86_64 UEFI ISO plus x86_64 UEFI QCOW2. The upstream source is `https://forge.fedoraproject.org/releng/kiwi-descriptions.git`, ref `f44`, commit `dfc49a5a10f69941179fdadd96aa6a5984f7c677`. Profile source is `teams/kde.xml`; profiles are `KDE-Desktop-Live` and `KDE-Desktop-Disk`. This is still a POC baseline, not a production image-format approval.

## Work log (UTC)

| Task ID | UTC timestamp | Changed file(s) | Test/evidence outcome | Commit |
|---|---|---|---|---|
| ATLAS-01-FB-001 | 2026-10-31T07:24:36Z | `os/image-source.lock.json` | Source branch, commit and upstream blob IDs inspected; structural CI test later passed | `3d4832eb6379658e9b9f1b8917688590c16885d7` |
| ATLAS-01-FB-002 | 2026-10-31T07:24:49Z | `tools/atlas/build-image.sh` | Pinned clone/build/checksum/metadata automation added; shell syntax later passed | `5d5facc04f56f0e8640a6361e459940d836cfe7b` |
| ATLAS-01-FB-003 | 2026-10-31T07:25:12Z | `tools/atlas/resolve-package-manifest.py` | Production resolver now requires exact NEVRA and provenance fields; 28-test CI passed | `b638353f35d68e4cb924b271e0e01a1d02a524ea` |
| ATLAS-01-FB-004 | 2026-10-31T07:25:25Z | `tools/atlas/test_resolve_package_manifest.py` | Epoch, version, repository and provenance tests added; 28-test CI passed | `f160fc0e9fd2a2fd115551b7105825911f28df1b` |
| ATLAS-01-FB-005 | 2026-10-31T07:25:33Z | `os/package-manifest.csv` | Pinned NEVRA, repo snapshot, RPM license and source provenance columns added; package rows remain owner-blocked | `890080390a79627f13dfcf025352a3fd8feff829` |
| ATLAS-01-FB-006 | 2026-10-31T07:25:36Z | `.github/workflows/atlas-package-resolver.yml` | Assigned-branch push CI enabled; run 41180559864 passed | `6c545f2eefe0954e5507e8768fad7fd2b24743c4` |
| ATLAS-01-FB-007 | 2026-10-31T07:25:39Z | `tools/atlas/build-image.sh` | Repeat-build checksum paths normalized; `bash -n` passed in run 41180649544 | `65b75c540dc4e461244378836517a87441da65fb` |
| ATLAS-01-FB-008 | 2026-10-31T07:26:22Z | `tools/atlas/test_image_source_lock.py` | Four source-lock tests added; first CI iteration exposed one incorrect test-field lookup | `8f5788df20d87a7841d5c65ab3fcf041083f8576` |
| ATLAS-01-FB-009 | 2026-10-31T07:26:27Z | `.github/workflows/atlas-package-resolver.yml` | Added JSON lock and shell syntax checks; run 41180611540 failed only the source-lock assertion | `687c029b5a24e913d7d172dcc3582726cdfa9b80` |
| ATLAS-01-FB-010 | 2026-10-31T07:26:49Z | `os/ATLAS-01-IMPLEMENTATION-STATUS.md` | Implementation boundaries, evidence and blockers documented | `a1f008659708b05a232cbc57f75590889ccb820b` |
| ATLAS-01-FB-011 | 2026-10-31T07:27:05Z | `tools/atlas/test_image_source_lock.py` | Corrected assertion; run 41180649544 passed all 32 tests | `e55e8a1944dc4e6e88bd496e236524530c6391c0` |
| ATLAS-01-FB-012 | 2026-10-31T07:27:37Z | `os/ATLAS-01-IMPLEMENTATION-STATUS.md` | Recorded current CI evidence and follow-up actions | `ef7bda771bc791a7f52ff6fd554d0a189fefbf7f` |

| ATLAS-01-FB-013 | 2026-10-31T07:36:56Z | `tools/atlas/build-image.sh` | Fixed KIWI wrapper result export with `--image-release=0`, removed intermediate trees before hashing, and added ISO/QCOW2 output assertions. CI run 41181310460 passed shell/JSON and 32 tests. | `d15951d3abbce8f6f2bae829d96269a1371c5b5b` |
| ATLAS-01-FB-014 | 2026-10-31T07:37:11Z | `tools/atlas/test_build_image_script.py` | Added four static regression tests for KIWI bundle export and checksum scope. CI run 41181327409 passed 36 tests. | `2af6fec981c40824816c90dccbcbf0db69d18211` |
| ATLAS-01-FB-015 | 2026-10-31T07:37:17Z | `.github/workflows/atlas-package-resolver.yml` | Added the new test file to Python compilation; CI run 41181333587 passed 36 tests, JSON validation and Bash syntax. | `32fba3efc6ab715e739cb6213944fcf61a4d24a9` |
| ATLAS-01-FB-016 | 2026-10-31T07:37:30Z | GitHub issue comments #5 and #12 | Completed NEXUS system service/activation review and NOVA Fedora/Plasma platform review. No shared contracts changed. | N/A — review comments [#5](https://github.com/otta-komban/TuskerOS/issues/5#issuecomment-6540691529), [#12](https://github.com/otta-komban/TuskerOS/issues/12#issuecomment-6540691845) |

| ATLAS-01-FB-017 | 2026-10-31T07:41:03Z | `tools/atlas/resolve-package-manifest.py` | Switched to DNF5 `full_nevra` and added exact repository/license/source-RPM metadata verification. DNF5 tag semantics checked against its repoquery man page. | `da34e8f031f6c2f802f8cd452612dc35ebf897df` |
| ATLAS-01-FB-018 | 2026-10-31T07:41:30Z | `tools/atlas/test_resolve_package_manifest.py` | Added license and source RPM mismatch tests; first CI attempts exposed stale two-column fixtures, corrected in next milestone. | `a93cbbf8b53be7131795185233b9073491c08a5f` |
| ATLAS-01-FB-019 | 2026-10-31T07:41:57Z | `tools/atlas/test_resolve_package_manifest.py` | Repaired four-column DNF metadata fixtures and added repo-info failure coverage; run 41181625107 passed 39 tests. | `44bfe6b6350c79d9ab9caec5a0d613983ed5931b` |
| ATLAS-01-FB-020 | 2026-10-31T07:42:50Z | `tools/atlas/build-image.sh` | Separated repeat-build hash comparison from the reproducible-build claim; metadata now explicitly reports reproducible_build_claim=false until immutable repo metadata and RPM payload digests are pinned. | `fd64b020dd2128ebb6c38c9024f1c598467ac93c` |
| ATLAS-01-FB-021 | 2026-10-31T07:42:58Z | `tools/atlas/test_build_image_script.py` | Added regression assertion preventing false reproducibility claims; run 41181689969 passed 40 tests. | `81e44a5adfddbc6781c24319b7920de67e3192e2` |
| ATLAS-01-FB-022 | 2026-10-31T07:42:35Z | GitHub issue #12 comment | Corrected earlier Plasma 6.6.4 package-version statement using live Fedora package index; current stable is 6.7.5-1.fc44 for workspace/login/setup. | N/A — [review correction](https://github.com/otta-komban/TuskerOS/issues/12#issuecomment-6540716164) |

| ATLAS-01-FB-023 | 2026-10-31T07:46:09Z | `tools/atlas/resolve-package-manifest.py` | Added RPM upstream URL query metadata and pin comparison; manifest now separates Fedora source repository URL from upstream project URL. | `1577f1115389887aff5c6e26900d07905ff36a7a` |
| ATLAS-01-FB-024 | 2026-10-31T07:48:48Z | `tools/atlas/test_resolve_package_manifest.py`, `os/package-manifest.csv` | Expanded provenance fixtures and manifest columns; run 41182076591 passed 41 tests before blank-URL edge-case coverage was added. | `a070f618e1c4a2a720159760ead0cd50417a0f3c`; `666b54929c6ee373947136a8e9fd0b715b3424cc` |
| ATLAS-01-FB-025 | 2026-10-31T07:50:28Z | `tools/atlas/resolve-package-manifest.py`, `tools/atlas/test_resolve_package_manifest.py` | Preserved empty URL fields, normalized them to `NOASSERTION`, and added source-repository/upstream-URL negative cases. Run 41182178235 passed 45 tests. | `5b0c247b7f4db9c0aff714b6eb9b85d7f24b6fb1`; `368828c5dc1d125257353e2ae4b99f074cb849f9`; `1d72c7e40862d8c6cfdf8dd8e7573c9923c639a4` |

| ATLAS-01-FB-026 | 2026-10-31T07:51:21Z | `tools/atlas/build-image.sh` | Build metadata now explicitly lists the unverified Fedora dist-git source URL limitation; run 41182234800 passed 45 tests. | `67c027879f3f7f77dc9a7a86c97e38799c31baf6` |
| ATLAS-01-FB-027 | 2026-10-31T07:51:30Z | `tools/atlas/test_build_image_script.py` | Added a regression assertion for the source-repository limitation disclosure; run 41182244823 passed 45 tests. | `5bfd033ec71b5c3b8c8aaa9507843f645fb15247` |

| ATLAS-01-FB-028 | 2026-10-31T07:53:29Z | Draft pull request #59 | Opened reviewable draft PR against main with task/base/head, scope, test evidence, contract impact, limitations and no-merge acceptance conditions. PR-head CI subsequently passed. | [PR #59](https://github.com/otta-komban/TuskerOS/pull/59) |
| ATLAS-01-FB-029 | 2026-10-31T07:56:41Z | `tools/atlas/resolve-package-manifest.py` | Added offline `--validate-only` mode; permits schema-only validation with zero rows while normal resolution still rejects an empty package list. | `458ba169f9a0d723cdc03c88aaf7ad8d4cac44f6` |
| ATLAS-01-FB-030 | 2026-10-31T07:56:57Z | `tools/atlas/test_resolve_package_manifest.py` | Added empty-manifest schema, production-empty rejection and validate-only CLI tests. Run 41182587372 passed 49 tests. | `873c9f0891284bafe1a64c05263c6d03cf66af1b` |
| ATLAS-01-FB-031 | 2026-10-31T07:57:04Z | `.github/workflows/atlas-package-resolver.yml` | CI now validates the actual package manifest header/provenance columns. Run 41182598005 passed 49 tests plus manifest, JSON and shell checks; PR unified validation 41182601497 passed all 8 jobs. | `f56a0df7d07e05bd29e29f0e87f15b3f4dc45973` |

| ATLAS-01-FB-032 | 2026-10-31T08:00:42Z | `os/package-manifest.csv` | Documented the immutable snapshot, Fedora dist-git source URL and upstream URL semantics directly beside the CSV header. Run 41182830193 passed 49 tests and manifest/JSON/shell validation; PR unified run 41182834842 passed all 8 jobs. | `14b211967a6bb390050d8c233df1bd5508e1007d` |

| ATLAS-01-FB-033 | 2026-10-31T08:03:20Z | `.github/workflows/atlas-package-resolver.yml` | Added Fedora 44 container smoke using live DNF5/libdnf5 5.4.3.0 and a real `bash` repoquery result. PR run 41183021284 passed 49 unit tests plus the live DNF5 smoke; unified run 41183021170 passed all 8 jobs. | `b499f54621b6d6aa61c5879b74c2d2291b7ed91d` |

| ATLAS-01-FB-034 | 2026-10-31T08:02:50Z | GitHub issue comments #5 and #12 | Requested owner-approved desktop and system-capability package names/layering from NOVA-02 and NEXUS-07; package manifest remains empty pending their input. | N/A — [NOVA request](https://github.com/otta-komban/TuskerOS/issues/12#issuecomment-6540959722), [NEXUS request](https://github.com/otta-komban/TuskerOS/issues/5#issuecomment-6540960034) |

| ATLAS-01-FB-035 | 2026-10-31T08:08:14Z | `.github/workflows/atlas-package-resolver.yml` | Added CI fetch/verification of the pinned Fedora KIWI commit and three source blobs. Run 41183352032 passed 49 tests, live Fedora 44 DNF5 smoke and source lock verification; unified run 41183355869 passed all 8 jobs. | `f763cd56a382a31c6206f42a3ecd402f077bd13d` |

**Engineering status:** resolver/source-lock/build automation foundation implemented; package inventory, immutable repository snapshot enforcement, actual image build and VM validation remain open. These engineering subtasks are not coordinator response completions.

## Next actions

1. Obtain reviewed package rows and dependency ownership confirmation from NOVA-02/NEXUS-07.
2. Add immutable repository snapshot acquisition and digest verification before calling the image pipeline reproducible.
3. Run current resolver/image-lock CI on the latest branch head.
4. Run the build on a disposable Fedora 44 x86_64 builder, then execute PHOENIX's QEMU/UEFI ISO, QCOW2 and installer smoke matrix.
5. Record artifact checksums and VM evidence without promoting untested Secure Boot or hardware claims.
