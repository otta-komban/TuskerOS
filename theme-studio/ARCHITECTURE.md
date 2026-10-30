

## 16. Persistent profile store reference implementation

`theme-studio/runtime/profile_store.py` persists declarative profile selections and token overrides as versioned JSON. It rejects unknown fields, malformed IDs, duplicate mixins, invalid mixin-winner references, duplicate JSON keys, symlink/non-regular store files and oversized documents (including a bounded read). Writes use a same-directory temporary file, mode 0600, file fsync, atomic replace and parent-directory fsync. Active-profile deletion requires an explicit existing fallback. The store is thread-safe within one process, not a cross-process transaction manager. Its parent directory must be private to the user; it does not itself verify package availability or token semantics. Profile activation here changes the persisted active-profile pointer only; preview/apply and desktop acknowledgement/rollback remain separate work.


## 17. Profile composition service

`theme-studio/runtime/profile_composer.py` joins the persisted profile format to an already validated, caller-supplied inert catalog and the deterministic token resolver. The catalog is keyed by pack ID and supplies `kind`, `version`, and declarative `tokens`; the base theme must match the exact version pinned by the profile. Selected mixins are resolved by ID from the catalog. Profile format v1 does not pin mixin versions, so reproducibility of mixin selection is bounded by the catalog snapshot supplied to composition; a future profile-format revision should pin mixin versions before marketplace updates can silently change them.

Composition rejects absent or wrong-kind packs, invalid catalog records, stale base-theme versions, invalid mixin winners and unresolved token conflicts. Precedence remains defaults < base theme < mixins < profile overrides < user overrides < enforced policy. It returns a detached token/provenance snapshot and does not mutate the profile store or catalog, read pack files, execute pack content, or apply desktop settings. The catalog provider remains responsible for manifest and asset validation before exposing records to this service.
