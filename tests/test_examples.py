from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from market_data_contracts import CollectorRequest, CollectorResponse, HorizonAssessment

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    ("path", "model"),
    [
        (ROOT / "examples" / "collector_request.json", CollectorRequest),
        (ROOT / "examples" / "collector_response_partial.json", CollectorResponse),
        (ROOT / "examples" / "horizon_assessment.json", HorizonAssessment),
    ],
)
def test_documented_examples_validate(path: Path, model: type) -> None:
    instance = model.model_validate_json(path.read_text(encoding="utf-8"))
    assert instance.model_dump(mode="json")


def test_fixture_manifest_expectations() -> None:
    fixtures = ROOT / "tests" / "fixtures"
    manifest = json.loads((fixtures / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == 1
    for entry in manifest["fixtures"]:
        payload = (fixtures / entry["path"]).read_text(encoding="utf-8")
        if entry["expected"] == "valid":
            CollectorResponse.model_validate_json(payload)
        else:
            with pytest.raises(ValidationError):
                CollectorResponse.model_validate_json(payload)

