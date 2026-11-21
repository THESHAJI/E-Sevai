import json
from pathlib import Path
from typing import Iterable

import pandas as pd


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes.json"

SOURCE_REGISTRY = {
    "Central": {
        "schemes": "https://www.myscheme.gov.in/",
        "india": "https://www.india.gov.in/my-government/schemes",
        "open_data": "https://www.data.gov.in/",
    },
    "Tamil Nadu": {"portal": "https://www.tn.gov.in/", "tenders_and_services": "https://tnesevai.tn.gov.in/"},
    "Maharashtra": {"portal": "https://maharashtra.gov.in/"},
    "Karnataka": {"portal": "https://www.karnataka.gov.in/"},
    "Kerala": {"portal": "https://kerala.gov.in/"},
    "Delhi": {"portal": "https://delhi.gov.in/"},
}


def load_schemes() -> list[dict]:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        schemes = json.load(handle)
    if not isinstance(schemes, list):
        raise ValueError("schemes.json must contain a JSON list")
    seen_ids = set()
    required_fields = {
        "id", "name", "category", "level", "states",
        "official_url", "application_url", "summary", "benefits",
        "documents", "application_steps", "criteria",
    }
    for scheme in schemes:
        if not isinstance(scheme, dict):
            raise ValueError("Each scheme record must be a JSON object")
        missing = required_fields - set(scheme)
        if missing:
            raise ValueError(
                f"Scheme record {scheme.get('id', '<unknown>')} is missing: "
                + ", ".join(sorted(missing))
            )
        if scheme["id"] in seen_ids:
            raise ValueError(f"Duplicate scheme id: {scheme['id']}")
        seen_ids.add(scheme["id"])
        if not scheme["official_url"].startswith("https://"):
            raise ValueError(f"Scheme {scheme['id']} has an invalid official URL")
        if not scheme["application_url"].startswith("https://"):
            raise ValueError(f"Scheme {scheme['id']} has an invalid application URL")
    return schemes


def search_schemes(schemes: Iterable[dict], query: str = "", category: str = "All") -> list[dict]:
    query = (query or "").strip().lower()
    category = category or "All"
    results = []
    for scheme in schemes:
        if category != "All" and scheme.get("category") != category:
            continue
        haystack = " ".join([
            str(scheme.get("name", "")),
            str(scheme.get("summary", "")),
            str(scheme.get("category", "")),
            " ".join(scheme.get("benefits", [])),
        ]).lower()
        if not query or query in haystack:
            results.append(scheme)
    return results


def schemes_to_dataframe(schemes: Iterable[dict]) -> pd.DataFrame:
    rows = []
    for scheme in schemes:
        rows.append({
            "Scheme": scheme["name"],
            "Category": scheme["category"],
            "Level": scheme["level"],
            "Summary": scheme["summary"],
        })
    return pd.DataFrame(rows)
