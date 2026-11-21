from typing import Any


def _profile_value(profile: Any, field: str):
    if hasattr(profile, "model_dump"):
        return profile.model_dump().get(field)
    if isinstance(profile, dict):
        return profile.get(field)
    return getattr(profile, field, None)


def evaluate_condition(profile: Any, condition: dict) -> dict:
    field = condition["field"]
    operator = condition["operator"]
    value = condition.get("value")
    actual = _profile_value(profile, field)
    label = condition.get("label", f"{field} condition")

    if condition.get("verification_status") == "needs_official_verification":
        return {
            "label": label,
            "status": "unknown",
            "evidence": "This condition needs official verification and is not treated as matched or failed",
        }

    if operator == "not_empty":
        if actual is not None and str(actual).strip():
            status = "matched"
            evidence = f"{field} is {actual}"
        else:
            status = "unknown"
            evidence = f"{field} was not provided"
    elif actual is None:
        status = "unknown"
        evidence = f"{field} was not provided"
    elif operator == "eq":
        status = "matched" if actual == value else "failed"
        evidence = f"{field} is {actual}; required {value}"
    elif operator == "in":
        status = "matched" if actual in value else "failed"
        evidence = f"{field} is {actual}; allowed values: {', '.join(map(str, value))}"
    elif operator == "gte":
        status = "matched" if actual >= value else "failed"
        evidence = f"{field} is {actual}; minimum is {value}"
    elif operator == "lte":
        status = "matched" if actual <= value else "failed"
        evidence = f"{field} is {actual}; maximum is {value}"
    elif operator == "between":
        status = "matched" if value[0] <= actual <= value[1] else "failed"
        evidence = f"{field} is {actual}; expected range is {value[0]} to {value[1]}"
    else:
        status = "unknown"
        evidence = f"Unsupported rule operator: {operator}"

    return {"label": label, "status": status, "evidence": evidence}


def evaluate_scheme(profile: Any, scheme: dict) -> dict:
    results = [evaluate_condition(profile, condition) for condition in scheme.get("criteria", [])]
    if scheme.get("verification_status") == "needs_official_verification":
        for item in results:
            if item["status"] == "failed":
                item["status"] = "unknown"
                item["evidence"] = "This scheme criterion needs official verification and is not treated as failed"
        results.append({
            "label": "Official verification",
            "status": "unknown",
            "evidence": "The scheme record has unverified details that require official confirmation",
        })
    selected_state = _profile_value(profile, "state")
    restricted_states = scheme.get("states", ["All India"])
    if "All India" not in restricted_states:
        if selected_state is None:
            location_result = {
                "label": "Resident location",
                "status": "unknown",
                "evidence": "State/Union Territory was not provided",
            }
        elif selected_state in restricted_states:
            location_result = {
                "label": "Resident location",
                "status": "matched",
                "evidence": f"User residence is {selected_state}; scheme applies to {', '.join(restricted_states)}",
            }
        else:
            location_result = {
                "label": "Resident location",
                "status": "failed",
                "evidence": f"User residence is {selected_state}; scheme is restricted to {', '.join(restricted_states)}",
            }
        results.insert(0, location_result)
    failed = [item for item in results if item["status"] == "failed"]
    unknown = [item for item in results if item["status"] == "unknown"]

    if failed:
        status = "Not Eligible"
    elif unknown:
        status = "Potentially Eligible"
    elif results:
        status = "Eligible"
    else:
        status = "Potentially Eligible"
        unknown = [{"label": "Eligibility criteria", "status": "unknown", "evidence": "No verifiable rules are configured"}]

    return {
        "status": status,
        "matched": [item for item in results if item["status"] == "matched"],
        "failed": failed,
        "unknown": unknown,
    }


def evaluate_schemes(profile: Any, schemes: list[dict]) -> list[dict]:
    output = []
    for scheme in schemes:
        result = evaluate_scheme(profile, scheme)
        output.append({**scheme, "eligibility": result})
    return sorted(output, key=lambda item: {"Eligible": 0, "Potentially Eligible": 1, "Not Eligible": 2}[item["eligibility"]["status"]])
