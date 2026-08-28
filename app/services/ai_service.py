"""
AI service layer. Wraps whichever provider is configured (OpenAI or Gemini)
behind one simple function: generate_text(prompt, system_prompt).

Swap providers purely via .env - no code changes needed elsewhere in the app.
"""
import json
import requests
from flask import current_app


class AIServiceError(Exception):
    pass


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    api_key = current_app.config["OPENAI_API_KEY"]
    model = current_app.config["OPENAI_MODEL"]
    if not api_key:
        raise AIServiceError("OPENAI_API_KEY is not configured on the server.")

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise AIServiceError(f"OpenAI API error ({resp.status_code}): {resp.text[:300]}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    api_key = current_app.config.get("GEMINI_API_KEY")

    if not api_key:
        raise AIServiceError("GEMINI_API_KEY is not configured on the server.")

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        model_name = current_app.config.get(
            "GEMINI_MODEL",
            "gemini-3.6-flash"
        )

        response = client.models.generate_content(
            model=model_name,
            contents=f"{system_prompt}\n\n{user_prompt}",
        )

        if not response or not response.text:
            raise AIServiceError("Gemini returned an empty response.")

        return response.text.strip()

    except Exception as e:
        current_app.logger.exception("Gemini AI call failed")
        raise AIServiceError(f"Gemini AI error: {str(e)}")
    
def generate_text(system_prompt: str, user_prompt: str) -> str:
    provider = current_app.config["AI_PROVIDER"].lower()
    if provider == "openai":
        return _call_openai(system_prompt, user_prompt)
    elif provider == "gemini":
        return _call_gemini(system_prompt, user_prompt)
    else:
        raise AIServiceError(f"Unknown AI_PROVIDER '{provider}'. Use 'openai' or 'gemini'.")


def generate_json(system_prompt: str, user_prompt: str) -> dict:
    """
    Asks the model to respond with ONLY JSON, then parses it defensively
    (models sometimes wrap JSON in ```json fences despite instructions).
    """
    strict_system = (
        system_prompt
        + "\n\nCRITICAL: Respond with ONLY valid JSON. No markdown fences, "
        "no explanations, no preamble or trailing text."
    )
    raw = generate_text(strict_system, user_prompt)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AIServiceError(f"AI did not return valid JSON: {e}. Raw output: {cleaned[:300]}")
