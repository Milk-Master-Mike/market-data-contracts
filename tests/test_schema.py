from __future__ import annotations

from market_data_contracts import PUBLIC_MODELS, CollectorResponse, SourceEvidence
from market_data_contracts.schema import schema_documents


def test_schema_documents_cover_public_models() -> None:
    documents = schema_documents()
    assert set(documents) == {f"{model.__name__}.schema.json" for model in PUBLIC_MODELS}


def test_provenance_schema_keeps_required_fields() -> None:
    required = set(SourceEvidence.model_json_schema()["required"])
    assert {
        "evidence_id",
        "source_name",
        "source_url",
        "retrieved_at",
        "effective_date",
        "units",
        "parser_version",
        "confidence",
    } <= required


def test_collector_response_uses_record_discriminator() -> None:
    schema_text = str(CollectorResponse.model_json_schema())
    for kind in (
        "company",
        "instrument",
        "filing_event",
        "float_snapshot",
        "quote_snapshot",
        "news_event",
        "positioning_snapshot",
        "horizon_assessment",
    ):
        assert kind in schema_text
