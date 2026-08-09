from __future__ import annotations

import pytest
from pydantic import ValidationError

from market_data_contracts import CollectorRequest, CollectorResponse


def test_contract_version_is_fixed_to_current_release() -> None:
    request_schema = CollectorRequest.model_json_schema()
    response_schema = CollectorResponse.model_json_schema()
    assert request_schema["properties"]["contract_version"]["const"] == "0.1.0"
    assert response_schema["properties"]["contract_version"]["const"] == "0.1.0"


def test_models_reject_unknown_fields_to_expose_version_drift() -> None:
    request = {
        "request_id": "11111111-1111-4111-8111-111111111111",
        "query": {"kind": "ticker", "value": "ACME"},
        "requested_datasets": ["identity"],
        "as_of": "2026-01-15T15:00:00Z",
        "unknown_contract_field": True,
    }
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CollectorRequest.model_validate(request)
