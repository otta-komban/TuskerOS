# Fedora Base Package Manifest Workflow

**Owner:** ATLAS-01  
**Target:** Fedora 44 x86_64 (provisional until the release/build gate is revisited)  
**Status:** Manifest contract and resolver workflow; package names intentionally not frozen.

## Why the package list is not populated yet

The KDE/session package set is waiting on NOVA-02's exact Fedora 44 requirements. The system capability package set is waiting on NEXUS-07. Tusker privilege integration is waiting on AEGIS-06. Installer and recovery packages are waiting on PHOENIX-10. Guessing package names or service dependencies from another Fedora release would create a false build contract.

## Source manifest

The initial source of truth will be a CSV file with these columns:

| Column | Meaning |
|---|---|
| `layer` | Stable logical layer: `base-core`, `desktop-kde`, `diagnostics`, or an explicitly optional layer |
| `package` | Fedora RPM package name (not a display name, comps group, or arbitrary command) |
| `owner` | Agent responsible for the dependency request |
| `required` | `true` for the selected profile or `false` for an optional profile |
| `rationale` | Concrete runtime/build requirement and validation owner |

Keep optional layers separate from the default profile. AI runtime, developer toolchains and remote-control packages must not enter the base profile by accident.

## Resolution and lock procedure

1. Run the resolver only on a Fedora 44 x86_64 host with DNF5 and the intended Fedora repositories enabled.
2. Preserve enabled repository configuration and metadata evidence for the run.
3. Resolve each source package name with DNF5 `repoquery`; do not install packages or change repository configuration.
4. Record exact package NEVRA and repository ID for each resolution. Fail on missing or ambiguous results rather than silently selecting a guessed version.
5. Review the resolved set with the owning agent, then use the same resolved inputs for the KIWI ISO and virtual-disk profiles.
6. Refresh the lock only through a reviewed dependency update; record the source manifest revision and repository metadata evidence.

The resolver is an evidence-gathering tool, not a repository snapshotter. For reproducible release builds, the selected repository metadata and RPM payloads must also be retained or referenced by immutable snapshot/checksum.

## Build gating

- No KIWI description should consume a guessed or unresolved package list.
- No package layer is considered approved merely because DNF can resolve it.
- Package removal tests must prove that optional Tusker layers do not remove Fedora boot, login, networking, recovery or KDE dependencies.
- Record licenses and source repositories for third-party packages; Fedora official repositories remain the default.
