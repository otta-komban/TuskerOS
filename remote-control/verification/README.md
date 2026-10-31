# Remote-control conformance verification

This directory contains implementation-neutral security conformance specifications and
a small documentation-integrity validator. The validator checks that the case tables
remain structurally complete; it is **not** a runtime security test suite.

## Validate the specification tables

Run from the repository root:

```sh
python remote-control/verification/validate_conformance_specs.py
```

The validator checks these specification tables and their expected case counts:

| Prefix | Specification | Expected cases |
| --- | --- | ---: |
| PAIR | `DEVICE-IDENTITY-AND-PAIRING-CONFORMANCE.md` | 22 |
| SESS | `SESSION-PROOF-AND-REVOCATION-CONFORMANCE.md` | 40 |
| NET | `TRANSPORT-AND-EXPOSURE-CONFORMANCE.md` | 42 |

It rejects malformed or cross-specification case IDs, duplicate or missing IDs,
non-contiguous numbering, malformed table rows, and empty conditions or assertions.
Fenced and indented Markdown code examples are ignored, so illustrative pipe rows
do not count as specification cases.
Duplicate-ID diagnostics include every source line containing the repeated ID.
Markdown pipes escaped with an odd number of immediately preceding backslashes are
treated as cell content; an even run leaves the pipe as a table delimiter.

To validate a different checkout or fixture tree, pass its repository root:

```sh
python remote-control/verification/validate_conformance_specs.py --root /path/to/repository
```

## Machine-readable output

Use `--json` for a single JSON object on standard output:

```sh
python remote-control/verification/validate_conformance_specs.py --json
python remote-control/verification/validate_conformance_specs.py --root /path/to/repository --json
```

The result contains `ok`, `scope`, and `runtime_security_tested`. The latter is
always `false`: a successful result means only that the documentation tables passed
the structural checks. A validation failure (including unreadable files and invalid UTF-8) exits with status 1.


The repository check evaluates PAIR, SESS, and NET independently in that order,
then reports all discovered specification failures together. Missing files, filesystem
read errors, and UTF-8 decoding errors are reported as controlled validation failures;
the validator does not stop after the first broken specification. Text diagnostics
retain the specification prefix and stable per-specification ordering. In JSON mode,
all failures are returned in the `error` field of the same failure object, with
`ok: false` and exit status 1.

## Run the validator's unit tests

```sh
python -m unittest discover -s remote-control/verification -p 'test_*.py' -v
```

The tests cover parser behavior, backslash parity, case-ID integrity, repository-root
validation, JSON CLI success/failure paths, and controlled text/JSON CLI handling of
invalid UTF-8 specification files.

## Scope and release gate

These checks do not prove pairing, cryptographic authentication, session expiry,
revocation, request authorization, transport security, broker behavior, or safe task
execution. They do not freeze shared contracts or authorize runtime implementation.
The owner has authorized scoped, branch-isolated implementation by the replacement
agent cohort (Issue #35 comments 6540346389 and 6540745614). That workforce
authorization does not close PILOT-08's cross-agent P0 contracts or authorize remote
runtime, listeners, protected routes, or privileged dispatch. Treat runtime security
as unverified until those P0 contracts are resolved and the separately required runtime
security tests have been implemented and executed with reviewable evidence.
