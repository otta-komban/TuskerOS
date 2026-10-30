# TuskerOS Model Catalog Admission Policy

Owner: ORBIT-05  
Status: Proposal; security and legal review required  
Applies to: every model artifact offered by the first-party catalog or imported into a managed catalog

## 1. Admission is not inference compatibility

A manifest passing JSON Schema validation proves only that its metadata has the expected shape. It does not establish that the publisher is authentic, the artifact is safe, the license permits a proposed use, the model performs well, or a runtime can load it. Keep these decisions separate and visible.

## 2. Required evidence before approval

- [ ] Immutable upstream revision or content-addressed source recorded; mutable aliases such as `latest` are not catalog identities.
- [ ] Every managed file has an exact byte size and SHA-256 digest; verification is performed on the downloaded bytes before activation.
- [ ] Publisher and source provenance are recorded, with retrieval time and the exact retrieval origin.
- [ ] The actual weights license text and identifier are captured. Code/runtime license is recorded separately when applicable.
- [ ] Redistribution and commercial-use terms are reviewed independently; unknown or ambiguous terms remain restricted pending human review.
- [ ] Model architecture, tokenizer/chat template where known, context length, modalities and quantization are checked against upstream metadata.
- [ ] Runtime compatibility is demonstrated against a pinned runtime version; metadata claims alone are insufficient.
- [ ] Hardware requirements are evidence-backed or explicitly unknown; no universal RAM/VRAM fit is inferred from parameter count alone.
- [ ] Security review covers archive/path behavior, untrusted tokenizer/template/config content, provenance and supply-chain risks.
- [ ] Quality and performance claims link to reproducible benchmark evidence and identify the test host.

## 3. Approval state machine

`draft -> candidate -> approved -> deprecated` is the normal path. `blocked` may be applied from any state. Only a designated reviewer may move a candidate to approved, and the review record must identify reviewer, date and evidence. A schema field saying `approved` is not itself authorization; catalog publication must be gated by the review workflow and repository permissions.

Unknown license terms, missing provenance, digest mismatch, mutable-only revision, unresolved security findings or missing required evidence prevent approval. A blocked artifact cannot be installed from the first-party catalog. Local user override, if ever implemented, must be explicit, scoped and separately audited; it must not silently change catalog status.

## 4. License interpretation

- Treat model weights, code, tokenizer, dataset and bundled assets as potentially separately licensed.
- Do not infer an OSI-approved software license from a model card badge or a short license label.
- Record restrictions on field of use, user count, geography, redistribution, attribution, acceptable use and downstream derivatives.
- If the license is custom, unclear, or unavailable, set review status to `review_required`; do not provide legal conclusions.
- Re-review when the artifact revision, license text, publisher terms or intended distribution changes.

## 5. Artifact integrity and safe installation

- Stage downloads outside the active model directory with bounded size and time limits.
- Reject path traversal, absolute paths, duplicate normalized paths, symlink/hardlink escape and unexpected file types during archive extraction.
- Verify every declared digest and size before atomic activation. A mismatch quarantines or deletes staging data and never replaces the active revision.
- Keep the previous working revision until a replacement passes integrity, metadata and runtime health checks, subject to available disk space.
- Never execute files from a model artifact as installer scripts. Runtime loading is an untrusted-input boundary and must remain least-privileged.

## 6. Catalog user interface requirements

Display publisher, exact revision, quantization, artifact size, weights license, review status, supported modalities, runtime compatibility and evidence-backed hardware guidance before download. Explain that `unknown` means not verified, not zero or supported. Ask consent before large downloads and show required/free storage. No telemetry or cloud inference is required for local use.

## 7. Change control

Changes to this policy, schema approval semantics or catalog publication gates require ORBIT-05 review and AEGIS-06 security review. License-policy changes also require a designated legal/policy reviewer. Keep the original manifest and review evidence associated with each immutable revision.
