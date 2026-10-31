# ATLAS-01 Completion Ledger

Permanent identity: ATLAS-01  
Branch: `01-fedora-base`  
Target: 100 actual assistant responses  
Current verified count: 24

| Response | Completion ID | Phase | Category | Status | Evidence |
|---:|---|---|---|---|---|
| 1 | ATLAS-01-C0001 | P0 | documentation | partial | `os/ATLAS-01-P0-INTAKE.md`; intake commit `43b642fd8235fb531cdf0b5610bf922c446b7880` |
| 2 | ATLAS-01-C0002 | P1 | status | recorded | Standby/continuity acknowledgement; no repository changes |
| 3 | ATLAS-01-C0003 | P1 | architecture | partial | `os/BUILD-TOOL-EVALUATION.md`, `os/BASE-SYSTEM-CONTRACTS.md`, `os/HARDWARE-COMPATIBILITY.md`, updated intake; commit `57eeb34940bbf0ebfddee9140853f51712e86d8b`; comments on issues #2, #4, #5 and #12 |
| 4 | ATLAS-01-C0004 | P1 | implementation | partial | `tools/atlas/poc-preflight.sh` (`bash -n` passed); `image/kiwi/README.md`; commit `2bc4301ee4c078926ed45ede224225833eb37025` |
| 5 | ATLAS-01-C0005 | P1 | implementation | partial | `os/PACKAGE-MANIFEST.md`, `os/package-manifest.csv`, `tools/atlas/resolve-package-manifest.py`, `os/DBUS-SERVICE-PACKAGING.md`; Python syntax and manifest parser smoke tests passed; resolver not run against Fedora repos; commit `da9974d54e9235cc57453c80085a6c7f71921d14` |
| 6 | ATLAS-01-C0006 | P1 | implementation | partial | `image/kiwi/config.xml`, `os/FEDORA-44-KDE-PACKAGE-CANDIDATES.md`, refreshed `os/BASE-SYSTEM-CONTRACTS.md`; XML well-formedness checks passed; no KIWI build or DNF resolution; commit `620c4df0c3dfdc055e9193fedb50d480e932a25d` |
| 7 | ATLAS-01-C0007 | P1 | implementation | partial | Resolver rejects cross-repository ambiguity and incomplete manifest metadata; added focused unit tests (not executed); commits `757e09c`, `9c26ba5`, `2b92e9b` |
| 8 | ATLAS-01-C0008 | P1 | validation | partial | Fixed hyphenated resolver import; nine focused helper/manifest tests passed in isolated harness; no DNF5 run; commit `362615c` |
| 9 | ATLAS-01-C0009 | P1 | implementation | partial | Added branch-scoped GitHub Actions compile + unittest workflow; commit `ca64944`; workflow execution pending |
| 10 | ATLAS-01-C0010 | P1 | validation | partial | Hardened CSV shape validation; added four malformed/duplicate manifest regression tests; commits `0a36c3d`, `87d529e`; CI execution pending |
| 11 | ATLAS-01-C0011 | P1 | validation | partial | Fixed four CSV fixture newline bugs; GitHub Actions run `41116328126` compiled resolver/tests and passed the unittest step (13 test methods); audited DNF5 repo/repoquery command semantics; commit `1b5fa29`; Fedora DNF5 runtime resolution remains untested |
| 12 | ATLAS-01-C0012 | P1 | implementation | partial | Atomic JSON output; mocked CLI and atomic-write coverage; CI run 41117170559 passed compilation and all 18 tests; commits ee0beae, 9a35b95, a7d8a99, 1463b9c; Fedora DNF5 runtime still pending |
| 13 | ATLAS-01-C0013 | P1 | status | recorded | Adopted compact progress dashboard; record reconciled into JSONL during C0014; no code change |
| 14 | ATLAS-01-C0014 | P1 | implementation | partial | DNF5 resolver now rejects package-name mismatches and unsupported architectures; two regression tests; docs updated; CI runs 41124667670 and 41124688115 queued at check; Fedora DNF5 runtime pending; commits ace17cd, 415f1a7, ba5395e, 61534cd, ff8afe9, 5b90ee1, e670627; final CI run 41124925504 queued |

| 15 | ATLAS-01-C0015 | P1 | status | recorded | Resumed Fedora base-image work; verified branch comparison, 49-test/8-job CI evidence, pinned KIWI source and still-open NOVA/NEXUS package handoffs; no package rows or build claims added |

| 16 | ATLAS-01-C0016 | P1 | implementation | partial | Added Fedora repository snapshot capture/preflight, manifest snapshot binding, build gate and 20+ regression checks; ATLAS CI run 41185951919 passed 70 tests plus live Fedora 44 DNF5 smoke and unified run 41185951924 passed all 8 jobs on `8f594cb`; KIWI/DNF snapshot consumption, metadata signatures, RPM checksums and actual image build remain open |

| 17 | ATLAS-01-C0017 | P1 | implementation | partial | DNF5 now stages locked Fedora repositories locally, verifies local repomd/primary metadata, and resolves only from local DNF repo paths; 78 tests + Fedora 44 DNF5 smoke passed in run 41190197697; unified 8/8 passed in 41190201562; KIWI still uses upstream remotes; no image build |

| 18 | ATLAS-01-C0018 | P1 | implementation | partial | KIWI now builds from a clean pinned-source overlay whose Fedora repository definitions point only to verified local fedora/updates snapshots; metadata/package signature checks enabled with Fedora 44 primary key; CI run 41191712051 passed 86 tests plus real-source overlay smoke and DNF5 smoke; unified run 41191712054 passed 8/8; no full reposync or image build |

| 19 | ATLAS-01-C0019 | P1 | implementation | partial | Local snapshot verifier now checks every repomd-referenced metadata payload SHA-256. Corrected Fedora signature policy after official fedora/updates repomd.xml.asc endpoints returned 404: detached metadata signature verification is not claimed; RPM package GPG checks remain enabled. ATLAS run 41192287443 passed 85 tests + Fedora 44 DNF5 and pinned-source KIWI overlay smoke; unified run 41192287352 pending; no full reposync/image build. Supersedes C0018's metadata-signature assumption. |

| 20 | ATLAS-01-C0020 | P1 | implementation | partial | Package manifest now requires rpm_sha256; DNF5 repoquery returns local RPM location and resolver hashes that staged file, confines path to repository, and compares digest to pin. ATLAS run 41192831799 passed 90 tests, Fedora 44 DNF5 location smoke and KIWI overlay integration; unified run 41192831693 passed 8/8 on the same code head; no package rows/full sync/image build. Supersedes C0019's separate-RPM-lock limitation. |

Counts include only actual assistant responses. Never backfill or fabricate entries.

| 21 | ATLAS-01-C0021 | P1 | implementation | partial | KIWI build outputs now use a collision-resistant per-run directory; each ISO/QCOW2 build target clears stale result/intermediate directories before execution. Two regression tests added. ATLAS run 41197460809 passed 92 tests, Fedora 44 DNF5 5.4.3.0 queryformat/RPM-location smoke and pinned-source KIWI overlay integration; unified run 41197460810 passed 8/8. No full reposync/image build. |

| 22 | ATLAS-01-C0022 | P1 | implementation | partial | Build metadata now binds repository snapshot lock, resolved package report, generated KIWI repository overlay and exported SHA256SUMS manifest by SHA-256. Regression test added. ATLAS run 41197718324 passed 93 tests, Fedora 44 DNF5 smoke and KIWI overlay integration; unified run 41197718316 passed 8/8. No full reposync/image build. |

| 23 | ATLAS-01-C0023 | P1 | validation | partial | Fedora 44 CI now checks the exact DNF5 reposync flags and global repo-selection option used by the build script. Removed obsolete repomd.xml.asc fixture files; KIWI overlay test now explicitly passes without detached metadata signatures while RPM package GPG checks remain enabled. ATLAS run 41197942774 passed 93 tests and Fedora 44 smoke; unified run 41197942886 passed 8/8. No full reposync/image build. |

| 24 | ATLAS-01-C0024 | P1 | implementation | partial | Moved snapshot+manifest production preflight and DNF5 reposync plugin check before upstream KIWI clone/fetch; empty/invalid package inputs now fail before network/source work. Added two ordering regression tests. ATLAS run 41198325237 passed 95 tests and Fedora 44 DNF5 smoke; unified run 41198328542 passed 8/8 on same code head. No full reposync/image build. |
