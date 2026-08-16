# Market Data Contracts

> **Archived:** This package now lives in [`market-research-platform`](https://github.com/Milk-Master-Mike/market-research-platform/tree/main/packages/market-data-contracts). Its full Git history was preserved in the monorepo.

`market-data-contracts` is the shared, versioned boundary between independent
market-research collectors and their consumers. It provides strict Pydantic v2
models, generated JSON Schemas, sanitized examples, and deterministic fixtures.

The contracts describe research evidence. They do **not** express trade signals,
predicted returns, order instructions, or personalized financial advice.

## Why this package exists

Every normalized record carries evidence provenance: a source URL, retrieval
time, effective date, units, parser version, confidence, and warnings. Collector
responses may contain successful records and source-specific failures together,
so one unavailable source does not erase useful evidence from another.

The initial public contract covers:

- companies and listed instruments;
- SEC filing events and issuer-reported share/float facts;
- quotes, news events, and positioning snapshots;
- transparent horizon assessments;
- collector requests, scrape runs, responses, and partial failures.

## Install and use

```bash
python -m pip install -e .
market-contracts-schema --output schemas
```

```python
from market_data_contracts import CollectorResponse

response = CollectorResponse.model_validate_json(payload)
for record in response.records:
    print(record.kind, record.evidence.source_url)
```

All timestamps must include a UTC offset. Unknown or inapplicable units are
explicit strings such as `not_applicable`; they are never omitted. Confidence is
a bounded value from `0` to `1`, not a probability of investment performance.

## Versioning and compatibility

The package follows semantic versioning. Within a major version:

- adding optional fields or new record kinds is compatible;
- changing a field's meaning, removing a field, or making an optional field
  required is breaking;
- enum additions may require consumer work, so consumers should preserve unknown
  data when possible and pin an exact release for production deployments.

See [docs/compatibility.md](docs/compatibility.md) for the policy. JSON Schemas
are reproducibly generated from the public models and validated in CI.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
python -m build
market-contracts-schema --output build/schemas
```

Fixtures are deterministic and contain no credentials or uncontrolled live
responses. Review [docs/fixture-policy.md](docs/fixture-policy.md),
[docs/docker-conventions.md](docs/docker-conventions.md), and
[`source-acceptance.yaml`](source-acceptance.yaml) before adding a source.

## Security and responsible use

Credentials belong in ignored `.env.local` files or local Docker secrets, never
in contract payloads. `source_settings` rejects secret-like keys. Scraped text is
untrusted data; this project neither authorizes bypassing access controls nor
grants rights to redistribute third-party content. See [SECURITY.md](SECURITY.md).
