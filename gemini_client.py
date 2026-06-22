"""
Minimal Gemini API client.

Uses the REST endpoint directly via `requests` rather than the
google-generativeai SDK, so the project has one less dependency to install.
Docs: https://ai.google.dev/api/generate-content
"""

import requests
from flask import current_app


class GeminiError(Exception):
    pass


def generate_content(prompt, system_instruction=None, temperature=0.6, max_output_tokens=1024):
    """
    Send a single-turn prompt to Gemini and return the generated text.
    Raises GeminiError with a human-readable message on any failure --
    callers should catch this and show it in the UI instead of crashing.
    """
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError(
            "No Gemini API key configured. Add GEMINI_API_KEY to your .env file."
        )

    model = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash")
    url = current_app.config["GEMINI_API_URL"].format(model=model)

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise GeminiError(f"Could not reach Gemini API: {exc}") from exc

    if response.status_code != 200:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except ValueError:
            detail = response.text
        raise GeminiError(f"Gemini API error ({response.status_code}): {detail}")

    data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        block_reason = data.get("promptFeedback", {}).get("blockReason")
        raise GeminiError(
            f"Gemini returned no candidates (blockReason={block_reason})."
            if block_reason
            else "Gemini returned an empty response."
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise GeminiError("Gemini returned an empty response.")
    return text
