# Proposed Desktop ↔ Theme Engine Contract

**Status:** Draft for NOVA-02 review; not yet agreed or implemented.

## Ownership

- PIXEL-03 owns the theme manifest, schema, validation, token resolution, profiles, preview/apply lifecycle and theme asset policy.
- NOVA-02 owns KDE/Qt shell components, Plasma integration, panel/dock/launcher/notification/quick-settings/lock-screen rendering, and desktop-specific adapters.

## Engine → Desktop

The engine provides:
- `ThemeSnapshot`: immutable resolved snapshot with `schema_version`, `theme_id`, `theme_version`, `revision`, semantic token maps, safe asset references and enforced accessibility flags.
- `ThemePreviewStarted(snapshot_id)`, `ThemePreviewEnded(snapshot_id)`.
- `ThemeApplyRequested(snapshot_id, revision)`.
- `ThemeApplyCommitted(revision)` or `ThemeApplyFailed(revision, surface, reason_code)`.
- `ThemeFallbackActivated(surface, fallback_id, reason_code)`.

Token namespaces proposed: `color`, `typography`, `spacing`, `shape`, `shadow`, `motion`, `surface`, `asset`.

## Desktop → Engine

Each adapter reports:
- Adapter ID and supported API version.
- Supported surface IDs and token namespaces.
- Capability flags (blur, transparency, animation, dynamic wallpaper, lock-screen theming, etc.).
- Prepare acknowledgement or a typed failure.
- Apply acknowledgement and effective fallback status.
- Runtime failure notification so the engine can restore/fallback.

## Transaction rules

1. Adapter prepares against an immutable staged snapshot without changing the visible active state.
2. Engine commits only after required adapters are ready.
3. Adapters switch to the new revision and acknowledge.
4. If a required adapter fails, engine asks all participating adapters to restore the previous revision.
5. Optional unsupported surfaces use a neutral system fallback and are reported in diagnostics.
6. Accessibility/security policy is applied by the engine and must also be enforced by desktop controls; theme data cannot disable it.

## Open questions for NOVA-02

- Which KDE Plasma and Qt versions are targeted by the first TuskerOS image?
- Which surfaces can be styled through supported APIs versus a TuskerOS-owned Qt/QML component?
- What IPC/event mechanism is preferred (D-Bus, local library/API, or in-process Qt interface)?
- Which adapters are required for the first MVP, and what is the fallback behavior for each?
- How should desktop shell restart/reload interact with a committed theme revision?

No Plasma config keys or API names are frozen until NOVA-02 confirms the supported stack and implementation approach.
