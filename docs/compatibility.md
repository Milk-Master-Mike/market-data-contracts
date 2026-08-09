# Compatibility policy

The package and its JSON Schemas use semantic versions. `contract_version` in a
payload identifies the contract family used to produce it.

## Compatible changes within a major version

- Add an optional field with a default.
- Add a new schema or a new discriminated record kind.
- Relax a validation constraint without changing field meaning.
- Improve descriptions, examples, or non-normative documentation.

## Breaking changes

- Remove or rename a field or record kind.
- Make an optional field required.
- Change units, meaning, type, discriminator, or serialization.
- Tighten validation so a previously valid payload fails.

Collectors should pin the same major version and test their fixture responses
against `CollectorResponse`. Consumers should tolerate fields added within a
major release: models reject unknown fields to expose drift, so upgrade this
package before consuming a collector that emits a newer minor contract.

Before release, regenerate schemas, validate every example and fixture, and run
the compatibility tests against the last tagged schema bundle. Breaking changes
require a migration note and a major version increment.

