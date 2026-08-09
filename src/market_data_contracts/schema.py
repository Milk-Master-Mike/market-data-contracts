"""Generate or verify checked-in JSON Schemas for public models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import CONTRACT_VERSION, PUBLIC_MODELS


def schema_documents() -> dict[str, dict[str, object]]:
    documents: dict[str, dict[str, object]] = {}
    for model in PUBLIC_MODELS:
        document = model.model_json_schema(mode="validation")
        document["$id"] = (
            "https://raw.githubusercontent.com/Milk-Master-Mike/market-data-contracts/"
            f"v{CONTRACT_VERSION}/schemas/{model.__name__}.schema.json"
        )
        document["x-contract-version"] = CONTRACT_VERSION
        documents[f"{model.__name__}.schema.json"] = document
    return documents


def rendered_documents() -> dict[str, str]:
    return {
        name: json.dumps(document, indent=2, sort_keys=True) + "\n"
        for name, document in schema_documents().items()
    }


def write_schemas(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    expected = rendered_documents()
    for stale in output.glob("*.schema.json"):
        if stale.name not in expected:
            stale.unlink()
    for name, content in expected.items():
        (output / name).write_text(content, encoding="utf-8", newline="\n")


def check_schemas(output: Path) -> list[str]:
    expected = rendered_documents()
    problems: list[str] = []
    actual_names = {path.name for path in output.glob("*.schema.json")}
    for name, content in expected.items():
        path = output / name
        if not path.exists():
            problems.append(f"missing {name}")
        elif path.read_text(encoding="utf-8") != content:
            problems.append(f"out of date {name}")
    for name in sorted(actual_names - expected.keys()):
        problems.append(f"unexpected {name}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("schemas"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        problems = check_schemas(args.output)
        if problems:
            parser.error("schema drift: " + ", ".join(problems))
        return
    write_schemas(args.output)


if __name__ == "__main__":
    main()

