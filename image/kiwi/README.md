# KIWI Fedora 44 x86_64 description scaffold

**Status: schema-informed scaffold, not build-ready.** The description intentionally has no final image package set. Do not run a production build from this directory until the package manifest is populated, reviewed and resolved against the exact Fedora 44 repository metadata intended for the build.

## Current contents

- `config.xml`: one description with Fedora 44 Everything and Updates RPM-MD repositories, DNF5, x86_64 restriction, RPM signature checking, ISO and OEM image types.
- Bootstrap package: `filesystem`, following the KIWI NG package/bootstrap model.
- Image package group: intentionally empty. The package manifest and resolution lock are the only allowed sources for filling it.

## Build contract still open

1. NOVA-02 must review the Fedora KDE package candidates in `os/FEDORA-44-KDE-PACKAGE-CANDIDATES.md` and identify the desktop comps/profile or exact runtime package list.
2. ATLAS-01 must resolve every approved package to exact NEVRA and repository ID with DNF5 on a Fedora 44 x86_64 host.
3. PHOENIX-10 must confirm the required ISO/install/recovery behavior and the disk artifact format. The OEM type is not yet a verified QCOW2 output contract.
4. AEGIS-06 must review signature/trust policy before any Secure Boot claim. `firmware="efi"` does not assert Secure Boot support.
5. KIWI NG's installed version must be recorded and the description validated with that exact version before build.

## Repository snapshot consumption boundary

- `tools/atlas/build-image.sh` verifies the committed repository lock, then stages each locked repository under `build/atlas/repository-snapshot/<repo-id>` with DNF5 `reposync --download-metadata` for `x86_64` and `noarch`. Both RPM package and repository metadata signature checks are enabled during sync.
- The staged `repomd.xml` and primary metadata bytes are checked against the lock, and `repomd.xml.asc` must be present. DNF5 package resolution uses only local `--repofrompath` repositories, with `gpgcheck=1`, `repo_gpgcheck=1`, and the Fedora 44 primary key explicitly configured.
- The build exports the pinned upstream Git commit into a clean derived KIWI source tree. `tools/atlas/prepare-kiwi-snapshot.py` resolves the pinned `repositories/core.xml` symlink, requires the repository aliases to match the lock exactly, and rewrites the Fedora 44 `fedora` and `updates` source paths to local `file://` snapshot directories. It preserves the Fedora signing-key references, resolves the `$releasever` macro to the Fedora 44 key file, and enables KIWI `repository_gpgcheck` and `package_gpgcheck`.
- Both DNF5 resolution and KIWI image construction are therefore configured to consume the same staged local repositories. Build metadata sets `repository_snapshot_consumed_by_kiwi: true` and records successful signature enforcement only after the full build succeeds. The signing-key fingerprint is not separately recorded in the snapshot lock, and RPM payload checksums are not yet individually pinned.
- The build host must have the DNF5 `reposync` plugin (`dnf5-plugins`) and Fedora 44 `distribution-gpg-keys` installed. Full repository sync and KIWI image build have not yet been run; the full sync may require substantial disk space and network transfer.

## Validation and build gate

- XML well-formedness can be checked with Python's standard-library XML parser.
- KIWI schema/runtime validation must be performed with the target KIWI NG version on a Fedora 44 build host.
- A successful parse is not a successful KIWI validation, package resolution, image build or boot test.
- Keep repository metadata snapshots and RPM payload checksums with build evidence; repository URLs alone do not make a build reproducible.

## Upstream references

- KIWI NG 11.1 image-description schema reference: https://osinside.github.io/kiwi/image_description/elements.html
- KIWI NG workflow: https://osinside.github.io/kiwi/overview/workflow.html
- Fedora 44 repository layout: https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/
