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

- `tools/atlas/build-image.sh` first verifies the committed remote snapshot lock, then uses `dnf5 reposync --download-metadata` to stage each locked repository under `build/atlas/repository-snapshot/<repo-id>` for `x86_64` and `noarch` packages. This mirrors the selected repositories in full and may require substantial disk space and network transfer.
- The build re-verifies the staged `repomd.xml` and primary metadata bytes against the lock. The package resolver uses DNF5 `--repofrompath` and `--repo` options to expose only those local copies, with RPM signature checking enabled.
- This closes the DNF5 package-resolution path only. The upstream Fedora `Fedora.kiwi` description still contains its own remote repository definitions, so **KIWI image construction is not yet consuming the staged local snapshot**. Build metadata records this as `repository_snapshot_consumed_by_kiwi: false`; no reproducibility claim is allowed.
- The build host must have the DNF5 `reposync` plugin (`dnf5-plugins`) installed. No actual full repository sync or KIWI image build has been run yet.

## Validation and build gate

- XML well-formedness can be checked with Python's standard-library XML parser.
- KIWI schema/runtime validation must be performed with the target KIWI NG version on a Fedora 44 build host.
- A successful parse is not a successful KIWI validation, package resolution, image build or boot test.
- Keep repository metadata snapshots and RPM payload checksums with build evidence; repository URLs alone do not make a build reproducible.

## Upstream references

- KIWI NG 11.1 image-description schema reference: https://osinside.github.io/kiwi/image_description/elements.html
- KIWI NG workflow: https://osinside.github.io/kiwi/overview/workflow.html
- Fedora 44 repository layout: https://download.fedoraproject.org/pub/fedora/linux/releases/44/Everything/x86_64/os/
