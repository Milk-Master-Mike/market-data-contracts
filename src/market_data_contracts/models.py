"""Pydantic models forming the public market-data contract."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

CONTRACT_VERSION = "0.1.0"

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Symbol = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=32),
]
Confidence = Annotated[Decimal, Field(ge=0, le=1, decimal_places=6)]
NonNegativeDecimal = Annotated[Decimal, Field(ge=0)]
Score = Annotated[Decimal, Field(ge=0, le=100, decimal_places=6)]


class StrictModel(BaseModel):
    """Base configuration shared by all wire models."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class SourceEvidence(StrictModel):
    """Required provenance and quality metadata for a normalized fact."""

    evidence_id: NonEmptyString = Field(description="Stable ID unique within a research run.")
    source_name: NonEmptyString
    source_url: HttpUrl
    retrieved_at: AwareDatetime
    effective_date: date
    units: NonEmptyString = Field(
        description="Explicit units, such as shares, USD, ratio, or not_applicable."
    )
    parser_version: Annotated[
        str,
        StringConstraints(strip_whitespace=True, pattern=r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$"),
    ]
    confidence: Confidence = Field(
        description="Evidence quality from 0 to 1; never investment-performance probability."
    )
    warnings: tuple[NonEmptyString, ...] = ()
    source_record_id: NonEmptyString | None = None
    excerpt: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=500)
    ] | None = Field(
        default=None,
        description="Optional short evidence excerpt; never a republished full article.",
    )


class Company(StrictModel):
    kind: Literal["company"] = "company"
    company_id: NonEmptyString
    legal_name: NonEmptyString
    cik: Annotated[str, StringConstraints(pattern=r"^\d{10}$")] | None = None
    lei: Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{20}$")] | None = None
    aliases: tuple[NonEmptyString, ...] = ()
    jurisdiction: Annotated[str, StringConstraints(min_length=2, max_length=80)] | None = None
    evidence: SourceEvidence


class SecurityType(StrEnum):
    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    ETF = "etf"
    ADR = "adr"
    UNIT = "unit"
    WARRANT = "warrant"
    FUND = "fund"
    OTHER = "other"


class Instrument(StrictModel):
    kind: Literal["instrument"] = "instrument"
    instrument_id: NonEmptyString
    company_id: NonEmptyString | None = None
    symbol: Symbol
    exchange: NonEmptyString
    security_type: SecurityType
    currency: Annotated[str, StringConstraints(to_upper=True, pattern=r"^[A-Z]{3}$")] = "USD"
    active: bool = True
    evidence: SourceEvidence


class FilingEvent(StrictModel):
    kind: Literal["filing_event"] = "filing_event"
    filing_id: NonEmptyString
    company_id: NonEmptyString
    accession_number: Annotated[
        str, StringConstraints(pattern=r"^\d{10}-\d{2}-\d{6}$")
    ]
    form: NonEmptyString
    filed_date: date
    report_date: date | None = None
    accepted_at: AwareDatetime | None = None
    primary_document_url: HttpUrl
    event_tags: tuple[NonEmptyString, ...] = ()
    evidence: SourceEvidence


class FloatMeasure(StrEnum):
    ISSUER_REPORTED_PUBLIC_FLOAT = "issuer_reported_public_float"
    SHARES_OUTSTANDING = "shares_outstanding"
    TRADABLE_FREE_FLOAT = "tradable_free_float"
    OTHER = "other"


class FloatSnapshot(StrictModel):
    kind: Literal["float_snapshot"] = "float_snapshot"
    snapshot_id: NonEmptyString
    company_id: NonEmptyString
    instrument_id: NonEmptyString | None = None
    measure: FloatMeasure
    value: NonNegativeDecimal
    as_of_date: date
    currency: Annotated[str, StringConstraints(to_upper=True, pattern=r"^[A-Z]{3}$")] | None = None
    methodology: NonEmptyString
    evidence: SourceEvidence

    @model_validator(mode="after")
    def distinguish_public_float(self) -> FloatSnapshot:
        if self.measure == FloatMeasure.ISSUER_REPORTED_PUBLIC_FLOAT:
            warning_text = " ".join(self.evidence.warnings).lower()
            if "not current tradable free float" not in warning_text:
                raise ValueError(
                    "issuer-reported public float must warn that it is not current "
                    "tradable free float"
                )
        return self


class QuoteSnapshot(StrictModel):
    kind: Literal["quote_snapshot"] = "quote_snapshot"
    snapshot_id: NonEmptyString
    instrument_id: NonEmptyString
    as_of: AwareDatetime
    currency: Annotated[str, StringConstraints(to_upper=True, pattern=r"^[A-Z]{3}$")]
    price: NonNegativeDecimal | None = None
    open: NonNegativeDecimal | None = None
    high: NonNegativeDecimal | None = None
    low: NonNegativeDecimal | None = None
    close: NonNegativeDecimal | None = None
    volume: NonNegativeDecimal | None = None
    adjusted: bool = False
    evidence: SourceEvidence

    @model_validator(mode="after")
    def require_a_quote_value(self) -> QuoteSnapshot:
        values = (self.price, self.open, self.high, self.low, self.close, self.volume)
        if all(value is None for value in values):
            raise ValueError("a quote snapshot must contain at least one price or volume value")
        if self.low is not None and self.high is not None and self.low > self.high:
            raise ValueError("low cannot exceed high")
        return self


class CatalystCategory(StrEnum):
    FILING = "filing"
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    CAPITAL = "capital"
    GOVERNANCE = "governance"
    PRODUCT = "product"
    REGULATORY = "regulatory"
    MACRO = "macro"
    OTHER = "other"


class NewsEvent(StrictModel):
    kind: Literal["news_event"] = "news_event"
    event_id: NonEmptyString
    canonical_url: HttpUrl
    title: NonEmptyString
    publisher: NonEmptyString
    published_at: AwareDatetime
    company_ids: tuple[NonEmptyString, ...] = ()
    instrument_ids: tuple[NonEmptyString, ...] = ()
    catalyst_categories: tuple[CatalystCategory, ...] = ()
    duplicate_cluster_id: NonEmptyString | None = None
    content_hash: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")] | None = None
    evidence: SourceEvidence


class CorrectionStatus(StrEnum):
    ORIGINAL = "original"
    CORRECTED = "corrected"
    SUPERSEDED = "superseded"
    UNKNOWN = "unknown"


class PositioningSnapshot(StrictModel):
    kind: Literal["positioning_snapshot"] = "positioning_snapshot"
    snapshot_id: NonEmptyString
    market_name: NonEmptyString
    report_family: NonEmptyString
    contract_code: NonEmptyString
    report_date: date
    publication_date: date
    reporting_lag_days: Annotated[int, Field(ge=0)]
    correction_status: CorrectionStatus = CorrectionStatus.UNKNOWN
    long_positions: NonNegativeDecimal | None = None
    short_positions: NonNegativeDecimal | None = None
    spreading_positions: NonNegativeDecimal | None = None
    open_interest: NonNegativeDecimal | None = None
    long_percent_open_interest: Score | None = None
    short_percent_open_interest: Score | None = None
    evidence: SourceEvidence

    @model_validator(mode="after")
    def require_position_value(self) -> PositioningSnapshot:
        values = (
            self.long_positions,
            self.short_positions,
            self.spreading_positions,
            self.open_interest,
            self.long_percent_open_interest,
            self.short_percent_open_interest,
        )
        if all(value is None for value in values):
            raise ValueError("a positioning snapshot must contain a positioning value")
        if self.publication_date < self.report_date:
            raise ValueError("publication_date cannot precede report_date")
        if (self.publication_date - self.report_date).days != self.reporting_lag_days:
            raise ValueError("reporting_lag_days must match report_date and publication_date")
        return self


class ScoreComponent(StrictModel):
    name: NonEmptyString
    weight: Confidence
    value: Score
    contribution: Score
    evidence_ids: tuple[NonEmptyString, ...] = ()
    explanation: NonEmptyString


class EvidenceConflict(StrictModel):
    description: NonEmptyString
    evidence_ids: tuple[NonEmptyString, ...] = Field(min_length=2)
    effect: NonEmptyString


class HorizonAssessment(StrictModel):
    kind: Literal["horizon_assessment"] = "horizon_assessment"
    assessment_id: NonEmptyString
    company_id: NonEmptyString
    horizon_label: NonEmptyString
    trading_days: Annotated[int, Field(gt=0)] | None = None
    calendar_months: Annotated[int, Field(gt=0)] | None = None
    calendar_years: Annotated[int, Field(gt=0)] | None = None
    research_relevance_score: Score
    evidence_strength_score: Score
    freshness_score: Score
    components: tuple[ScoreComponent, ...]
    conflicts: tuple[EvidenceConflict, ...] = ()
    missing_inputs: tuple[NonEmptyString, ...] = ()
    calculation_version: Annotated[
        str,
        StringConstraints(strip_whitespace=True, pattern=r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$"),
    ]
    explanation: NonEmptyString = Field(
        description="Explains research evidence, never a buy/sell instruction or return forecast."
    )
    evidence: SourceEvidence

    @model_validator(mode="after")
    def validate_horizon_and_weights(self) -> HorizonAssessment:
        horizons = (self.trading_days, self.calendar_months, self.calendar_years)
        if sum(value is not None for value in horizons) != 1:
            raise ValueError("exactly one horizon duration must be set")
        weight_sum = sum((component.weight for component in self.components), Decimal(0))
        if self.components and abs(weight_sum - Decimal(1)) > Decimal("0.000001"):
            raise ValueError("component weights must sum to 1")
        prohibited = re.compile(r"\b(buy|sell|guaranteed return|price target)\b", re.IGNORECASE)
        if prohibited.search(self.explanation):
            raise ValueError("assessment explanation cannot contain investment instructions")
        return self


NormalizedRecord: TypeAlias = Annotated[
    Company
    | Instrument
    | FilingEvent
    | FloatSnapshot
    | QuoteSnapshot
    | NewsEvent
    | PositioningSnapshot
    | HorizonAssessment,
    Field(discriminator="kind"),
]


class QueryKind(StrEnum):
    TICKER = "ticker"
    COMPANY_NAME = "company_name"
    IDENTIFIER = "identifier"


class SearchQuery(StrictModel):
    kind: QueryKind
    value: NonEmptyString


class RunMode(StrEnum):
    LIVE = "live"
    FIXTURE = "fixture"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScrapeRun(StrictModel):
    run_id: UUID
    collector: NonEmptyString
    collector_version: NonEmptyString
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    mode: RunMode
    status: RunStatus
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    query: SearchQuery
    requested_datasets: tuple[NonEmptyString, ...] = Field(min_length=1)
    source_names: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def validate_timing(self) -> ScrapeRun:
        terminal = {RunStatus.SUCCEEDED, RunStatus.PARTIAL, RunStatus.FAILED, RunStatus.CANCELLED}
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        if self.status in terminal and self.finished_at is None:
            raise ValueError("terminal runs require finished_at")
        return self


def _contains_secret_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = re.sub(r"[^a-z]", "", str(key).lower())
            secret_markers = ("secret", "password", "token", "apikey", "credential")
            if any(marker in normalized for marker in secret_markers):
                return str(key)
            found = _contains_secret_key(nested)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _contains_secret_key(item)
            if found:
                return found
    return None


class CollectorRequest(StrictModel):
    request_id: UUID
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    query: SearchQuery
    resolved_entity: Company | None = None
    requested_datasets: tuple[NonEmptyString, ...] = Field(min_length=1)
    as_of: AwareDatetime
    source_settings: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Non-secret source behavior only; credentials come from runtime secrets.",
    )

    @field_validator("source_settings")
    @classmethod
    def reject_secret_settings(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        key = _contains_secret_key(value)
        if key:
            raise ValueError(f"source_settings cannot contain secret-like key: {key}")
        return value


class FailureCode(StrEnum):
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    BLOCKED = "blocked"
    MALFORMED = "malformed"
    NOT_FOUND = "not_found"
    STALE = "stale"
    CANCELLED = "cancelled"
    INTERNAL = "internal"


class PartialFailure(StrictModel):
    failure_id: NonEmptyString
    source_name: NonEmptyString
    dataset: NonEmptyString
    code: FailureCode
    message: NonEmptyString
    occurred_at: AwareDatetime
    retryable: bool
    source_url: HttpUrl | None = None
    warnings: tuple[NonEmptyString, ...] = ()


class CollectorResponse(StrictModel):
    contract_version: Literal[CONTRACT_VERSION] = CONTRACT_VERSION
    run: ScrapeRun
    records: tuple[NormalizedRecord, ...] = ()
    partial_failures: tuple[PartialFailure, ...] = ()

    @model_validator(mode="after")
    def validate_status(self) -> CollectorResponse:
        if self.run.contract_version != self.contract_version:
            raise ValueError("response and run contract versions must match")
        if self.partial_failures and self.records and self.run.status != RunStatus.PARTIAL:
            raise ValueError("mixed records and failures require partial run status")
        if self.run.status == RunStatus.SUCCEEDED and self.partial_failures:
            raise ValueError("succeeded response cannot contain partial failures")
        if self.run.status == RunStatus.FAILED and self.records:
            raise ValueError("failed response cannot contain normalized records")
        if self.run.status == RunStatus.PARTIAL and not self.partial_failures:
            raise ValueError("partial response requires at least one partial failure")
        return self


PUBLIC_MODELS: tuple[type[BaseModel], ...] = (
    SourceEvidence,
    Company,
    Instrument,
    FilingEvent,
    FloatSnapshot,
    QuoteSnapshot,
    NewsEvent,
    PositioningSnapshot,
    ScoreComponent,
    EvidenceConflict,
    HorizonAssessment,
    SearchQuery,
    ScrapeRun,
    CollectorRequest,
    PartialFailure,
    CollectorResponse,
)
