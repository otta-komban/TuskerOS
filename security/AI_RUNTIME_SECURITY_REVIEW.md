# ORBIT-05 AI Runtime Security Review

**Owner:** AEGIS-06  
**Reviewed branch:** `05-ai-runtime`  
**Reviewed revision:** `a30ee3558e5d247d662027a176ad96c68988e3a6`  
**Status:** Security review completed with required revisions; not runtime approval  
**Request:** [Issue #28](https://github.com/otta-komban/TuskerOS/issues/28)

## Scope and evidence

Reviewed the ORBIT-05 provider and model-store proposals:

- `tusker-ai/docs/PROVIDER-CONTRACT.md`
- `tusker-ai/docs/MODEL-STORE-TRANSACTIONS.md`
- `tusker-ai/docs/PROVIDER-CONFORMANCE.md`
- `tusker-ai/schemas/model-manifest.schema.json`
- `tusker-ai/schemas/inference-event.schema.json`
- `tusker-ai/docs/CROSS-AGENT-ALIGNMENT.md`

This is a source/contract review. No provider, model downloader, archive extractor, service, or runtime security behavior was executed.

## Decisions

**Conditional acceptance of the architectural boundary; revisions required before adapter or ModelStore implementation is accepted.**

The following invariants are sound and should remain mandatory:

- Provider runs as the logged-in user, never root; inference is optional and local-only by default.
- Runtime does not execute tool calls, arbitrary shell commands, or model-provided callbacks.
- Provider cancellation may terminate only a process the adapter demonstrably owns; shared/external daemons must not be killed to cancel one request.
- Model bytes are staged, verified before activation, activated atomically, and recovered without guessing after interruption.
- Model output, tool proposals, manifests, archive metadata and provider diagnostics are untrusted inputs.
- Prompts, generated content, credentials and environment secrets are excluded from default logs.

## Findings requiring remediation

### AISEC-001 — Manifest trust claims are caller-controlled (High)

The model-manifest schema permits fields such as `provenance.digest_verified`, `provenance.signature_verified`, `license.review_status`, and `review.catalog_status` to be supplied in the manifest itself. A downloaded publisher-controlled manifest can therefore claim that bytes were verified, a signature was verified, or a model was approved.

**Required boundary:** Treat every downloaded manifest field as untrusted descriptive metadata. The trusted ModelStore verifier must independently hash the exact staged bytes and verify any publisher signature against a separately managed trust root. Catalog/license approval must come from a locally trusted review record or signed catalog, never from a manifest self-assertion. Store verifier outcomes separately from the downloaded manifest and bind them to the immutable artifact revision and digest. A schema-valid manifest must never be sufficient to mark an artifact verified or approved.

**Acceptance tests:**
1. A manifest claiming `digest_verified=true`, `signature_verified=true`, and approved review/license statuses cannot promote an artifact whose actual bytes fail digest/signature verification.
2. Changing the manifest after verification invalidates the verification record.
3. A publisher-supplied reviewer name or approval status cannot satisfy the local catalog review gate.

### AISEC-002 — Download source URI policy is underspecified (High)

The manifest schema accepts generic URI values for `source` and `provenance.retrieved_from`. The contract requires explicit consent but does not define a safe remote-fetch scheme, redirect policy, or protection against a manifest directing a downloader to local or internal services.

**Required boundary:** Separate remote catalog downloads from explicit local-file imports. For remote downloads, require HTTPS with certificate validation and a documented host/redirect policy. Reject unsupported schemes and redirects to loopback, link-local, private, or otherwise disallowed destinations; revalidate resolved destinations across redirects and connection establishment to resist DNS rebinding. A user-approved local import must use a separate local-file workflow and must not be silently triggered by a manifest URI.

**Acceptance tests:**
1. Reject `file:`, `ftp:`, plaintext HTTP, and unsupported schemes in the remote-download path.
2. Reject redirects to loopback/link-local/private destinations and verify the final connected peer against the approved policy.
3. Demonstrate that local import requires a separate explicit user action and cannot be initiated by a remote manifest.

### AISEC-003 — Archive extraction needs race-resistant containment (High)

The ModelStore contract already rejects traversal, links, special files, normalized-name collisions and requires containment checks. It should additionally specify descriptor-relative creation to close the time-of-check/time-of-use gap between path validation and file creation.

**Required boundary:** Extract beneath an opened staging-root directory descriptor using descriptor-relative operations; create files exclusively and without following symlinks. Revalidate each parent component without following links. Do not rely solely on string-prefix checks or a resolve-then-open sequence. Keep staging private to the transaction and reject hardlinks, symlinks, devices, FIFOs and sockets under the initial format policy.

**Acceptance tests:**
1. Traversal, absolute paths, alternate separators, NUL/control characters, duplicate normalized paths, case-folding collisions and Unicode-normalization collisions produce no writes outside staging.
2. Symlink replacement/race attempts between validation and creation cannot escape the opened staging root.
3. Link and special-file archive members are rejected without following or creating them.

### AISEC-004 — Effective provider listener ownership must be verified (High)

The provider contract says to verify the effective bind address and fail on unexpected non-loopback exposure, but does not define how to distinguish a provider's declared configuration from its actual kernel listener.

**Required boundary:** Verify the effective listening sockets and owning process/UID using OS-observed state, not only provider configuration or a self-reported health endpoint. Reject wildcard and non-loopback IPv4/IPv6 listeners. If listener ownership/address cannot be verified, do not dispatch inference requests. Detect unexpected listener changes while the provider is running and fail closed. If the provider is externally managed and its listener cannot be safely constrained/verified, keep the adapter unavailable rather than assuming it is local-only.

**Acceptance tests:**
1. A provider configured for loopback but actually bound to `0.0.0.0`, `::`, or a non-loopback interface is marked failed and receives no requests.
2. A listener whose PID/UID does not match the expected provider process is rejected.
3. A listener that changes after startup is detected and the adapter stops accepting requests.

### AISEC-005 — Owned-process cancellation and launch hardening need executable checks (Medium)

The contract correctly limits forced termination to an owned process, but adapter implementation should make ownership mechanically provable.

**Required boundary:** Launch only an approved absolute executable path with an argument vector (never a shell string), sanitized environment, controlled working directory, and explicit inherited-file-descriptor policy. Record the spawned PID/start identity and verify it before signaling. Never terminate a shared Ollama daemon or an unrelated process because a request timed out.

**Acceptance tests:**
1. Cancellation of one request does not terminate a shared provider or unrelated concurrent requests.
2. An adapter cannot signal a PID that it did not spawn/own, including after PID reuse.
3. Provider startup rejects an unexpected executable path, unsafe environment override, or inherited sensitive descriptor.

### AISEC-006 — Logging redaction should be allow-list based (Medium)

The prose excludes prompts, generated text, credentials and environment secrets from default logs. Require structured allow-listed fields rather than relying on best-effort redaction of arbitrary provider diagnostics.

**Required boundary:** Log only bounded event metadata (request/correlation IDs, provider/model identifiers, event type, safe error code, timings and coarse resource counters). Never persist prompt/completion bodies, tool arguments, authorization headers, session tokens, private paths containing secrets, or raw provider exceptions by default. Diagnostics that need richer detail require an explicit local opt-in and bounded redaction policy.

**Acceptance tests:**
1. Inject canary prompt text, tool arguments, API keys and environment secrets into provider errors and assert none appear in default logs.
2. Verify structured logs reject unknown fields or redact them before persistence.
3. Verify log size/rate limits under repeated provider failures.

## Cross-agent ownership

- ORBIT-05 owns provider adapters, ModelStore implementation and runtime-specific conformance.
- AEGIS-06 owns the policy/trust boundary and security acceptance requirements; model output never authorizes tools.
- TUSKER-04 owns orchestration and task lifecycle; tool proposals must cross its typed proposal boundary.
- NEXUS-07 owns approved system interfaces and any privileged broker/IPC boundary.
- ATLAS-01 owns Fedora service packaging, OS hardening and secure-storage availability.

## Exit conditions

Before AEGIS security review can be closed, ORBIT-05 should update the contracts/tests for AISEC-001–006 and provide executable evidence. Schema validation alone is insufficient. Real-provider listener checks must be run on the pinned Fedora target, and ModelStore path/race tests must exercise the actual filesystem APIs.

**No approval is granted for privileged tool execution, model installation, provider network exposure, or release readiness by this review.**


### AISEC-007 — Manifest file paths need a constrained grammar and collision tests (High)

The current `tusker-ai/schemas/model-manifest.schema.json` constrains `files[].filename` only to a non-empty string. It accepts traversal components (for example, `../../outside.gguf`), absolute-looking paths and platform-specific separators. The `files` array also has no uniqueness constraint. The existing `test_model_manifest_schema.py` tests digest, size, URI and metadata shape, but not path traversal, duplicate names or normalized/case-folding collisions.

The ModelStore transaction contract separately requires traversal rejection, canonical containment and collision rejection during extraction. That is a useful runtime requirement, but it is not reflected in manifest-level validation or its negative test suite.

**Required boundary:** Define a portable relative-path grammar for manifest filenames. Reject absolute, drive/UNC, empty, dot and dot-dot components, NUL/control characters and unsupported separators. Reject duplicate names and detect case-folding/Unicode-normalization collisions on the target filesystem. Independently canonicalize and containment-check every path immediately before file access; JSON Schema validation is not a filesystem security boundary.

**Acceptance tests:**
1. Schema/manifest tests reject `../`, nested traversal, absolute paths, drive-prefixed paths and backslash traversal.
2. Tests reject duplicate names and distinct names that collide after target-filesystem normalization/case folding.
3. Runtime tests prove a malicious manifest cannot cause reads, writes, digest checks or cleanup outside the canonical managed/staging root, including symlink/race cases.

**Evidence and limits:** Current manifest schema, model-store transaction contract and manifest tests were source-reviewed. No ModelStore implementation or archive extractor was present in the reviewed tree; this is a contract/test gap, not a demonstrated runtime write-escape exploit.
