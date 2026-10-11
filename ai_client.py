
import os
import requests


def get_ai_settings():
    """Read AI configuration from environment variables or Streamlit secrets."""
    api_key = os.getenv("AI_API_KEY", "").strip()
    base_url = os.getenv(
        "AI_BASE_URL",
        "https://api.groq.com/openai/v1"
    ).strip().rstrip("/")
    model = os.getenv(
        "AI_MODEL",
        "llama-3.3-70b-versatile"
    ).strip()

    if not api_key:
        try:
            import streamlit as st
            api_key = str(st.secrets.get("AI_API_KEY", "")).strip()
            base_url = str(
                st.secrets.get("AI_BASE_URL", base_url)
            ).strip().rstrip("/")
            model = str(
                st.secrets.get("AI_MODEL", model)
            ).strip()
        except Exception:
            pass

    return api_key, base_url, model


def chat(messages, temperature=0):
    """Send a chat request to the configured OpenAI-compatible API."""
    api_key, base_url, model = get_ai_settings()

    if not api_key:
        raise RuntimeError(
            "AI_API_KEY is missing. Configure it in Streamlit Cloud Secrets."
        )

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=90,
    )

    response.raise_for_status()
    result = response.json()

    return result["choices"][0]["message"]["content"].strip()
