from groq import Groq
from backend.app.core.config import settings

client = Groq(api_key=settings.groq_api_key)


def generate_text(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_completion_tokens=3000,
    )
    return response.choices[0].message.content or ""


def extract_preferences(original: str, revised: str) -> list[dict]:
    system_prompt = (
        "You extract cautious writing preferences from revisions. "
        "Return only a JSON array. Each item must have preference_type, "
        "preference_value, confidence, evidence. Do not infer client facts. "
        "Only report style patterns directly supported by the edit."
    )
    user_prompt = (
        "Original draft:\n" + original[:12000] +
        "\n\nUser revision:\n" + revised[:12000] +
        "\n\nReturn up to three candidate writing preferences as JSON."
    )
    raw = generate_text(system_prompt, user_prompt).strip()
    raw = raw.removeprefix("```json").removesuffix("```").strip()
    import json
    data = json.loads(raw)
    return data if isinstance(data, list) else []
