# TuskerOS Developer Bundles

Bundles are declarative optional development environments. Their manifests enumerate package-manager coordinates and resource estimates; they do not execute arbitrary commands.

- Schema: `schemas/developer-bundle.schema.json`
- Initial proposal: `python-developer.json`

ATLAS-01 must verify repository/package availability for the target Fedora image before this bundle is considered release-ready. Installation/removal must use platform package transactions and preserve packages shared by other bundles or user workflows.
