import os
import re

import requests


def get_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        return api_key

    try:
        import streamlit as st

        api_key = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
        if api_key:
            return api_key
    except Exception:
        pass

    try:
        import streamlit as st

        api_key = str(st.secrets.get("openai", {}).get("api_key", "")).strip()
        if api_key:
            return api_key
    except Exception:
        pass

    return ""


def deterministic_explanation(scheme: dict, result: dict) -> str:
    lines = [f"Deterministic result for {scheme['name']}: **{result['status']}**."]
    if result["matched"]:
        lines.append("Matched: " + "; ".join(item["label"] for item in result["matched"]) + ".")
    if result["failed"]:
        lines.append("Failed: " + "; ".join(item["label"] for item in result["failed"]) + ".")
    if result["unknown"]:
        lines.append("Unknown: " + "; ".join(item["label"] for item in result["unknown"]) + ".")
    lines.append("Please verify final eligibility on the official source because implementation rules may change.")
    return "\n".join(lines)


def _llm_response_is_consistent(text: str, result: dict) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    if re.search(r"https?://|www\.", text, re.IGNORECASE):
        return False

    lowered = text.lower()
    status = result["status"]
    if status == "Eligible":
        return bool(re.search(r"\beligible\b", lowered)) and "potentially eligible" not in lowered and "not eligible" not in lowered
    if status == "Potentially Eligible":
        return "potentially eligible" in lowered and "not eligible" not in lowered
    if status == "Not Eligible":
        return "not eligible" in lowered
    return False


def explain_with_llm(scheme: dict, result: dict, question: str = "") -> dict:
    fallback = deterministic_explanation(scheme, result)
    api_key = get_api_key()
    if not api_key:
        return {"text": fallback, "mode": "deterministic", "source_used": True}

    evidence = {
        "status": result["status"],
        "matched": result["matched"],
        "failed": result["failed"],
        "unknown": result["unknown"],
        "official_url": scheme["official_url"],
        "application_url": scheme["application_url"],
        "verification_status": scheme.get("verification_status", "unverified"),
        "benefits": scheme["benefits"],
        "documents": scheme["documents"],
        "application_steps": scheme["application_steps"],
    }
    prompt = (
        "You are an Indian government scheme assistant. Explain only the provided evidence. "
        "Do not decide eligibility and do not invent benefits, links or criteria. "
        "Clearly separate matched, failed and unknown conditions. "
        "Clearly label any need_official_verification information as unconfirmed. "
        f"Scheme: {scheme['name']}\nEvidence: {evidence}\n"
        f"User question: {question or 'Explain this result'}"
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "system", "content": "Be concise, factual and transparent."},
                             {"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=12,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        if not _llm_response_is_consistent(text, result):
            return {"text": fallback, "mode": "deterministic", "source_used": True}
        return {"text": text, "mode": "llm", "source_used": True}
    except Exception as exc:
        return {"text": fallback + f"\n\nLLM unavailable: {type(exc).__name__}.", "mode": "deterministic", "source_used": True}
