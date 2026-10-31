# Hello Tusker extension example

This is a deliberately metadata-only starter package. It demonstrates the initial manifest contract without introducing executable code, install hooks, or permissions.

## Validate

From the repository root:

```sh
python3 sdk/tools/validate_manifest.py sdk/examples/hello-extension/manifest.json
```

Expected output: `valid: org.tuskeros.examples.hello (manifest v1)`.

## Safety notes

- The empty permission list requests no privileged capability.
- No executable payload is included.
- This is not yet installable into a live extension host. Sandbox/runtime integration is blocked on the AEGIS-06 and NEXUS-07 contracts.
