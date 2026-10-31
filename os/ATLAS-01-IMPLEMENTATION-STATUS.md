# ATLAS-01 Fedora Base & Image Foundation — Implementation Status

**Task ID:** ATLAS-01-FEDORA-BASE-001  
**Status:** In progress  
**Branch:** `agent/01-fedora-base`  
**Implementation base SHA:** `8bf66079f9e021244eda432fa8455e83b59e2165`  
**Latest verified head:** `e55e8a1944dc4e6e88bd496e236524530c6391c0`  
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
- Corrected the ATLAS workflow's branch filters so push validation runs on `agent/01-fedora-base` and PR validation targets `main`.

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
- One preceding CI iteration (run `41180611540`) failed one newly added source-lock test due to an incorrect test-field lookup; the test was corrected and the next run passed.

### Image/build/runtime status

- Image build: **not run**.
- Reproducibility comparison: **not run**.
- Image checksums: **not produced**.
- VM install/boot: **not tested**.
- Secure Boot: **not tested**.
- Physical hardware: **not tested**.

## Explicit blockers and boundaries

1. `os/package-manifest.csv` intentionally has no package rows. The base-system proposal defers exact package selection until NOVA-02 and NEXUS-07 confirm dependencies. The resolver/build script fail closed rather than inventing package names or licenses.
2. A repository snapshot identifier is required in each future package row, but the current resolver records that declared value and repo evidence; it does **not yet fetch or verify immutable Fedora repodata bytes**. Bit-for-bit reproducible release builds remain blocked until the build consumes an immutable repository snapshot and validates its metadata digest.
3. The upstream Fedora Forge commit is unsigned/unverified according to its branch API response. Content blob IDs are checked, but upstream signature trust remains unresolved.
4. PHOENIX-10's installer boundary remains a separate handoff. No Anaconda install or destructive storage behavior is implemented here.

## PHOENIX-10 handoff

The shared POC candidate is Fedora 44, mutable RPM/DNF, x86_64 UEFI ISO plus x86_64 UEFI QCOW2. The upstream source is `https://forge.fedoraproject.org/releng/kiwi-descriptions.git`, ref `f44`, commit `dfc49a5a10f69941179fdadd96aa6a5984f7c677`. Profile source is `teams/kde.xml`; profiles are `KDE-Desktop-Live` and `KDE-Desktop-Disk`. This is still a POC baseline, not a production image-format approval.

## Next actions

1. Obtain reviewed package rows and dependency ownership confirmation from NOVA-02/NEXUS-07.
2. Add immutable repository snapshot acquisition and digest verification before calling the image pipeline reproducible.
3. Run current resolver/image-lock CI on the latest branch head.
4. Run the build on a disposable Fedora 44 x86_64 builder, then execute PHOENIX's QEMU/UEFI ISO, QCOW2 and installer smoke matrix.
5. Record artifact checksums and VM evidence without promoting untested Secure Boot or hardware claims.
