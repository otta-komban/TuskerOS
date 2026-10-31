# Fedora D-Bus Service Packaging Review (ATLAS-01)

**Status:** Review guidance for NEXUS-07 proposal; not an approved interface or installable unit.  
**Scope:** Fedora packaging and lifecycle only. NEXUS-07 owns API identifiers and implementation; AEGIS-06 owns authorization and security policy.

## Review of the NEXUS candidate

NEXUS-07 proposes a read-only system-bus API at:

- Bus: system
- Name: `org.tuskeros.SystemTools1`
- Object: `/org/tuskeros/SystemTools1`
- Interface: `org.tuskeros.SystemTools1.Manager`

**ATLAS-01 review: conditionally compatible.** A narrow, unprivileged, on-demand D-Bus service is compatible with Fedora packaging conventions, provided the project first confirms control of the reverse-DNS namespace and AEGIS-06 approves the trust boundary. These names must remain provisional until then.

## Recommended Fedora packaging shape

If NEXUS confirms a separate daemon is necessary (prefer direct library calls or existing system services for one-shot reads):

1. Package the D-Bus system service activation file under the distribution's configured data directory, conventionally `/usr/share/dbus-1/system-services/<well-known-name>.service`.
2. Use a `SystemdService=` entry to request systemd activation. The referenced unit should use `Type=dbus`, set `BusName=` to the exact well-known name and run a foreground process.
3. For an on-demand-only service, do **not** add a `[Install]` section or enable it through `multi-user.target`. D-Bus activation and boot enablement are separate controls.
4. Run under a dedicated, unprivileged service identity. The identity name and UID/GID allocation must be supplied by NEXUS and reviewed by AEGIS; ATLAS will not invent it. Prefer Fedora `sysusers.d` integration when a static package-owned account is required, subject to the final account contract.
5. Keep the unit independently disableable and the package removable. It must not be in the dependency chain of boot, networking, display-manager, logind, or KDE login.
6. Install only the minimum D-Bus policy required to own the service name and expose the intended interface. D-Bus bus policy is not a substitute for method-level authorization, trusted peer identity, or AEGIS policy.
7. Keep methods read-only and bounded. No arbitrary command execution, arbitrary file access, raw process execution, or privileged mutation belongs in this service contract.
8. Add package scriptlet/trigger behavior only if required by Fedora packaging; do not enable or start a resident daemon during package installation.

The exact Fedora D-Bus policy directory and packaging macros must be confirmed against the target Fedora 44 build environment and its selected D-Bus implementation before packaging. Do not copy a policy path from a generic upstream example without validating it.

## Required tests before approval

- D-Bus activation starts the service on first call and the service acquires only its approved name.
- No systemd boot target pulls the service in; it is inactive after a clean boot until called.
- The service runs as the approved non-root identity.
- Untrusted callers cannot own the service name or invoke methods outside the approved policy.
- Method responses are bounded, sanitized and do not disclose serials or stable personal identifiers by default.
- Service crash, timeout, missing dependency and disabled state produce an unavailable capability, not OS/login failure.
- Package removal removes activation/unit/policy files without breaking Fedora or KDE.
- AEGIS-06 reviews the bus policy, caller identity, authorization boundary and audit behavior.

## References

- D-Bus Specification, service activation and `SystemdService=`: https://dbus.freedesktop.org/doc/dbus-specification.html
- D-Bus daemon documentation, integrating system services: https://dbus.freedesktop.org/doc/dbus-daemon.1.html
- systemd.service, bus-activatable services: https://www.freedesktop.org/software/systemd/man/261/systemd.service.html

## Decision

No D-Bus name, unit name, account name, package name, or policy filename is approved by this review. NEXUS-07 must confirm whether a daemon is justified and provide the controlled namespace; AEGIS-06 must approve the security model. ATLAS-01 can then package the agreed files and test Fedora integration.
