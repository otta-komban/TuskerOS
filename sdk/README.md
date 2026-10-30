# TuskerOS SDK (initial foundation)

This directory contains the versioned extension manifest contract, a metadata-only example and a dependency-free validator.

## Validate an example

```sh
python3 sdk/tools/validate_manifest.py sdk/examples/hello-extension/manifest.json
```

The validator checks structure only. It does not verify publisher identity, artifact signatures, dependency resolution, permission grants, archive safety or runtime isolation.

## Current status

Manifest v1 is a draft for cross-agent review. A production SDK must use the permission vocabulary and sandbox/API contract approved by AEGIS-06 and NEXUS-07. Theme/layout data formats require PIXEL-03 agreement. Do not ship or install untrusted executable payloads based only on this validator.
