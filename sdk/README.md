# TuskerOS SDK (initial foundation)

This directory contains the versioned extension manifest contract, a metadata-only example, a dependency-free manifest validator, and deterministic dependency ordering.

## Validate an extension manifest

```sh
python3 sdk/tools/validate_manifest.py sdk/examples/hello-extension/manifest.json
```

The validator checks structure only and validates release versions using Semantic Versioning 2.0.0 identifier rules, including prerelease and build-metadata segments. The JSON Schema carries the same version pattern. It does not verify publisher identity, artifact signatures, dependency resolution, permission grants, archive safety or runtime isolation.

## Dependency planning

`sdk/tools/dependency_plan.py` orders an already-resolved dependency graph. It validates the entire supplied graph before planning, including disconnected entries, non-empty package ID keys, dependency declarations, duplicate edges and references to missing nodes. Roots and dependency declarations must contain non-empty package ID strings; text and mapping values are rejected where an iterable of IDs is expected. Malformed graph input raises `DependencyPlanError` rather than leaking raw type errors. Traversal is iterative rather than recursive, so valid deep dependency chains are not limited by Python's call-stack depth; ordering remains deterministic and cycle errors include the detected path. It does not select package versions, download packages, verify trust, authorize permissions, or install anything. Marketplace release selection and compatibility preview are implemented separately in `marketplace/tools/catalog_resolver.py`.

## Current status

Manifest v1 is a draft for cross-agent review. A production SDK must use the permission vocabulary and sandbox/API contract approved by AEGIS-06 and NEXUS-07. Theme/layout data formats require PIXEL-03 agreement. Marketplace metadata validation is provided separately in `marketplace/tools/validate_catalog_entry.py`; passing it does not confer trust or installation authority. Do not ship or install untrusted executable payloads based only on these validators.
