from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from market_data_contracts import (
    CollectorRequest,
    CollectorResponse,
    Company,
    FloatSnapshot,
    HorizonAssessment,
    ScoreComponent,
    ScrapeRun,
    SearchQuery,
    SourceEvidence,
)


def evidence(**changes: object) -> SourceEvidence:
    values: dict[str, object] = {
        "evidence_id": "ev-1",
        "source_name": "Synthetic source",
        "source_url": "https://example.com/source/1",
        "retrieved_at": datetime(2026, 1, 15, tzinfo=UTC),
        "effective_date": date(2026, 1, 14),
        "units": "shares",
        "parser_version": "0.1.0",
        "confidence": Decimal("0.9"),
        "warnings": (),
    }
    values.update(changes)
    return SourceEvidence.model_validate(values)


def test_every_normalized_record_requires_provenance() -> None:
    with pytest.raises(ValidationError):
        Company.model_validate(
            {
                "company_id": "sec:0000000001",
                "legal_name": "Acme Example Corporation",
                "cik": "0000000001",
            }
        )


def test_provenance_requires_timezone_and_explicit_units() -> None:
    with pytest.raises(ValidationError):
        evidence(retrieved_at=datetime(2026, 1, 15), units="")


def test_issuer_public_float_is_explicitly_distinguished() -> None:
    common = {
        "snapshot_id": "float-1",
        "company_id": "sec:0000000001",
        "measure": "issuer_reported_public_float",
        "value": "1000000",
        "as_of_date": "2025-06-30",
        "currency": "USD",
        "methodology": "Issuer filing cover page",
    }
    with pytest.raises(ValidationError, match="not current tradable free float"):
        FloatSnapshot.model_validate({**common, "evidence": evidence(units="USD")})

    snapshot = FloatSnapshot.model_validate(
        {
            **common,
            "evidence": evidence(
                units="USD",
                warnings=("Dated measure; not current tradable free float.",),
            ),
        }
    )
    assert snapshot.measure == "issuer_reported_public_float"


def test_source_settings_reject_secrets_at_any_depth() -> None:
    common = {
        "request_id": "11111111-1111-4111-8111-111111111111",
        "query": {"kind": "ticker", "value": "ACME"},
        "requested_datasets": ["quotes"],
        "as_of": "2026-01-15T15:00:00Z",
    }
    with pytest.raises(ValidationError, match="secret-like key"):
        CollectorRequest.model_validate(
            {**common, "source_settings": {"provider": {"api_key": "do-not-store"}}}
        )


def test_horizon_requires_one_duration_and_normalized_weights() -> None:
    component = ScoreComponent(
        name="recency",
        weight=Decimal("1"),
        value=Decimal("50"),
        contribution=Decimal("50"),
        explanation="Freshness component",
    )
    assessment = HorizonAssessment(
        assessment_id="a-1",
        company_id="sec:0000000001",
        horizon_label="short term",
        trading_days=10,
        research_relevance_score=Decimal("50"),
        evidence_strength_score=Decimal("50"),
        freshness_score=Decimal("50"),
        components=(component,),
        calculation_version="0.1.0",
        explanation="Evidence is incomplete and has moderate research relevance.",
        evidence=evidence(units="score_0_to_100"),
    )
    assert assessment.trading_days == 10

    with pytest.raises(ValidationError, match="exactly one horizon"):
        HorizonAssessment.model_validate(
            {
                **assessment.model_dump(mode="json"),
                "calendar_months": 6,
            }
        )


def test_partial_failures_do_not_erase_successful_records() -> None:
    company = Company(
        company_id="sec:0000000001",
        legal_name="Acme Example Corporation",
        cik="0000000001",
        evidence=evidence(units="not_applicable"),
    )
    run = ScrapeRun(
        run_id=UUID("22222222-2222-4222-8222-222222222222"),
        collector="test-collector",
        collector_version="0.1.0",
        mode="fixture",
        status="partial",
        started_at=datetime(2026, 1, 15, 15, tzinfo=UTC),
        finished_at=datetime(2026, 1, 15, 15, 0, 1, tzinfo=UTC),
        query=SearchQuery(kind="ticker", value="ACME"),
        requested_datasets=("identity", "quotes"),
    )
    response = CollectorResponse.model_validate(
        {
            "run": run,
            "records": [company],
            "partial_failures": [
                {
                    "failure_id": "quote-timeout-1",
                    "source_name": "Optional quote provider",
                    "dataset": "quotes",
                    "code": "timeout",
                    "message": "Fixture timeout",
                    "occurred_at": "2026-01-15T15:00:01Z",
                    "retryable": True,
                }
            ],
        }
    )
    assert len(response.records) == 1
    assert len(response.partial_failures) == 1
