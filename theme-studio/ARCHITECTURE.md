


## 15. Token resolver reference implementation

The pure-Python reference resolver is `theme-studio/runtime/token_resolver.py`. It applies the documented precedence (defaults, base theme, explicit mixins, profile, user, enforced policy), returns per-token provenance, and deep-copies values. Mixins are keyed by stable pack ID; unequal overlaps fail closed unless the caller supplies an explicit winning pack for that dotted token path. Sorting pack IDs makes disjoint resolution deterministic and avoids relying on manifest or dictionary insertion order. This is a resolver primitive, not yet connected to manifest validation, profile persistence, preview sessions, or desktop adapters. Enforced policy values are final in this function; the caller remains responsible for constructing that trusted policy input.
