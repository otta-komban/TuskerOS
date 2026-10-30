

## 16. Persistent profile store reference implementation

`theme-studio/runtime/profile_store.py` persists declarative profile selections and token overrides as versioned JSON. It rejects unknown fields, malformed IDs, duplicate mixins, invalid mixin-winner references, duplicate JSON keys, symlink/non-regular store files and oversized documents (including a bounded read). Writes use a same-directory temporary file, mode 0600, file fsync, atomic replace and parent-directory fsync. Active-profile deletion requires an explicit existing fallback. The store is thread-safe within one process, not a cross-process transaction manager. Its parent directory must be private to the user; it does not itself verify package availability or token semantics. Profile activation here changes the persisted active-profile pointer only; preview/apply and desktop acknowledgement/rollback remain separate work.
