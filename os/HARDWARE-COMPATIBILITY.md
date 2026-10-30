# ATLAS-01 Hardware Compatibility and Base Install Policy

**Phase:** P0 requirements / P1 package architecture  
**Date:** 2026-10-31  
**Status:** Requirements and validation matrix only. No physical device or boot compatibility has been tested by ATLAS-01 yet.

## 1. Support strategy

The first supported development and VM target is Fedora 44 on x86_64. Hardware compatibility is a tested support claim, not a package-presence assumption. A device is not declared supported merely because Linux has a driver or firmware package for it.

Initial architecture scope:
- x86_64: first-class build and VM validation target.
- aarch64: candidate follow-on target after build tooling, KDE session, firmware, installer and physical-device evidence exist.
- Other architectures: not in initial desktop support scope.

## 2. Required hardware categories

| Category | Required baseline | Validation evidence |
|---|---|---|
| Firmware/boot | UEFI boot; Secure Boot behavior explicitly tested; firmware setup remains user-controlled | UEFI VM boot, Secure Boot VM test, physical UEFI laptop results |
| Storage | SATA, NVMe and USB installation media; reliable device identification; SMART/NVMe diagnostics where available | Install/boot/read/write tests, installer target identity and health checks |
| Wi-Fi | NetworkManager-managed Wi-Fi with Fedora-supported firmware; common Intel/AMD/MediaTek/Realtek chipsets evaluated individually | Connect, reconnect, suspend/resume, airplane mode, offline boot |
| Bluetooth | Bluetooth controller discovery, pairing and reconnect | Pairing and reconnect tests with keyboard/headset |
| Audio | PipeWire/WirePlumber baseline; onboard and USB audio; headset microphone/output selection | Playback, capture, hotplug and suspend/resume tests |
| Graphics | Intel and AMD open drivers as baseline; NVIDIA evaluated separately, with clear proprietary/open driver trade-offs | Wayland login, external display, suspend/resume, video acceleration and recovery session |
| Display | Internal laptop panel, common resolutions, scaling and external monitor hotplug | Login, resolution, fractional scaling, hotplug and multi-monitor tests |
| Input | USB keyboard/mouse, laptop touchpad, function keys; touchscreen optional | Keyboard-only login, pointer, gestures fallback, suspend/resume |
| Power | ACPI, battery reporting, lid close/open, suspend and resume | Battery state, lid event, sleep/wake cycles, thermal and idle measurements |
| Firmware updates | fwupd/LVFS where device vendor supports it | Inventory and metadata availability; update only on explicit user action |
| Networking | Ethernet and USB tethering as recovery alternatives where hardware permits | DHCP, DNS, reconnect, firewall defaults and offline startup |

## 3. Hardware tiers from the TuskerOS master plan

These are capability planning tiers, not minimum hardware certification:

| Tier | Memory | Base OS expectation | AI expectation |
|---|---:|---|---|
| Low-end | 4 GB RAM | Lean KDE configuration, minimal autostart, small background footprint | Very small quantized models or limited local AI; no strong reasoning/vision promise |
| Standard | 8 GB RAM | Balanced desktop defaults and optional services | Small local models subject to measured performance |
| Powerful | 16 GB+ RAM, optional capable GPU | Full desktop experience and optional richer services | Larger models, coding/vision features only when benchmarks support them |

The installer and first boot should detect CPU, RAM, GPU, storage, firmware mode and relevant capabilities. Recommendations must be based on measured requirements and must not silently enable heavyweight services.

## 4. Base installation profiles

Profiles describe package composition, not separate unsupported Fedora forks:

1. **Minimal desktop:** Fedora core, KDE Plasma/Wayland session, network, storage, firmware, audio, accessibility and diagnostic essentials. No local model, developer toolchain or remote-control daemon.
2. **Recommended desktop:** minimal desktop plus carefully selected common desktop applications and user-facing system utilities. Tusker integration remains separately installable and non-critical.
3. **Optional feature bundles:** local AI runtime, developer tools, remote-control, additional applications and hardware-specific optional components. Each bundle has explicit dependencies, size/license/source metadata, enablement defaults and uninstall behavior.

The low-end/standard/powerful hardware tier may influence recommendations for optional bundles but must not create arbitrary package incompatibility.

## 5. Driver and firmware policy

- Fedora official repositories and Fedora-signed packages are the default.
- Firmware packages are included only where permitted by their distribution and package licenses; keep package/license inventory in release metadata.
- Open-source in-kernel Intel and AMD graphics drivers are the default desktop path.
- NVIDIA support requires a separately documented compatibility and trust decision; do not silently enable a third-party repository or install proprietary kernel modules in the base.
- Any third-party repository or vendor driver must have an explicit opt-in, a recorded signing-key trust decision, package scope, license review, update/rollback policy and uninstall path.
- Never disable RPM signature checking for convenience.
- A driver installation failure must not make the system unbootable; document a fallback boot/recovery procedure and preserve a generic display path where feasible.
- Secure Boot module signing/enrollment requirements must be disclosed before installing out-of-tree modules.
- fwupd/LVFS integration is optional and device/vendor dependent. Firmware updates are user-authorized and must not be bundled into routine unattended OS updates.

## 6. Validation environments

### VM baseline

- QEMU/KVM x86_64.
- UEFI firmware (OVMF); Secure Boot configuration tested separately.
- Virtio storage and network.
- At least one VM profile per memory tier: 4 GB, 8 GB, 16 GB.
- Test boot, login, KDE Wayland, networking, audio enumeration, storage, shutdown/reboot, update and recovery.
- VM results validate virtual hardware only; they do not certify Wi-Fi, Bluetooth, suspend/resume, battery, touchpad or vendor firmware.

### Physical laptop matrix

For each device, record:
- manufacturer/model and CPU/GPU class,
- RAM and storage,
- BIOS/UEFI version and Secure Boot state,
- Wi-Fi/Bluetooth chipset and firmware,
- audio codec/controller,
- display and touchpad,
- tested Fedora release and kernel version,
- exact tests and failures,
- whether the result is reproducible.

Do not publish serial numbers, machine identifiers, MAC addresses or other personal identifiers in public test evidence.

## 7. Current evidence status

| Test class | Status | Notes |
|---|---|---|
| Fedora 44 build-tool compatibility | Research only | See BUILD-TOOL-EVALUATION.md |
| x86_64 UEFI VM | Not run | Requires selected build tool and build host |
| Secure Boot VM | Not run | Must test signed artifact chain |
| 4/8/16 GB resource profiles | Not run | No image exists yet |
| Wi-Fi/Bluetooth/audio | Not run | Physical hardware not available in this agent context |
| GPU/display/Wayland | Not run | VM smoke test pending; physical GPU matrix pending |
| Touchpad/suspend/battery | Not run | Physical laptop testing required |
| Install/update/recovery | Not run | Coordinate with PHOENIX-10 |

## 8. Exit criteria

- [ ] Build and boot the Fedora 44 x86_64 development image in UEFI VM.
- [ ] Test KDE Wayland login and standard keyboard/mouse operation.
- [ ] Test Secure Boot with the selected signed boot chain.
- [ ] Test 4 GB, 8 GB and 16 GB VM memory profiles and publish actual measurements.
- [ ] Add at least one physical laptop to the hardware matrix before claiming laptop compatibility.
- [ ] Test Wi-Fi, Bluetooth, audio, GPU, touchpad and suspend/resume on physical hardware where available.
- [ ] Document unsupported chipsets and recovery paths.
- [ ] Verify the system remains usable with all Tusker services disabled.

This document defines what must be tested. It does not claim that any untested device or feature is already supported.
