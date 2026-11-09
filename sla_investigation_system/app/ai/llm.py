from openai import OpenAI
from app.config import settings

def get_client():
    if not settings.llm_api_key or not settings.llm_base_url:
        raise RuntimeError("LLM_API_KEY and LLM_BASE_URL must be configured.")
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

def ask_llm(system_prompt, user_prompt):
    client = get_client()
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content or ""
