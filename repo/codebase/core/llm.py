import os
from typing import Literal

try:
    import openai
except Exception:
    openai = None


def complete_json(prompt_id: str, variables: dict, schema: dict,
                  tier: Literal["fast", "main"] = "fast") -> dict:
    raise NotImplementedError("LLM structured output not implemented yet")


def simple_chat(user_message: str) -> str:
    """Send a simple chat message to OpenAI if key present, otherwise echo back.

    Returns assistant reply as text.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL_MAIN", "gpt-4o")
    if api_key and openai is not None:
        try:
            openai.api_key = api_key
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=300,
            )
            text = resp.choices[0].message.get("content", "").strip()
            return text
        except Exception as e:
            return f"(LLM error) {e}"
    # fallback echo
    return f"Echo: {user_message}"
