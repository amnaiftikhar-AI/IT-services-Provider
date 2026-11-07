from langchain_openai import ChatOpenAI
from amna_rag.config import settings


def get_llm(temperature: float = 0):
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to your .env file.")
    return ChatOpenAI(model=settings.llm_model, api_key=settings.groq_api_key, base_url=settings.groq_base_url, temperature=temperature, max_tokens=1600)

def decompose_question(question: str) -> list[str]:
    """Ask the configured model for focused sub-queries; fallback keeps exact codes."""
    try:
        # prompt = ("Break this IT support question into 2-4 short search queries. "
        #           "Keep exact error codes, product names and device names unchanged. "
        #           "Return one query per line, no numbering.\n\nQuestion: " + question)
        prompt = (
                    "Break this IT support question into 2-3 DISTINCT search queries. "
                    "Each query must investigate a different aspect of the problem. "
                    "Avoid paraphrases or repeated meanings. "
                    "Preserve exact error codes, product names and device names. "
                    "Return one query per line, without numbering.\n\n"
                    "Question: " + question
)
        response = get_llm().invoke(prompt).content
        lines = [x.strip(" -*0123456789.	") for x in str(response).splitlines() if x.strip()]
        return list(dict.fromkeys([question] + lines[:4]))
    except Exception:
        return [question]

def answer_from_context(question: str, context: str, history: list[dict]) -> str:
    llm = get_llm()
    history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history[-6:])
    prompt = f"""You are an internal IT troubleshooting assistant. Use ONLY the supplied knowledge-base evidence for technical facts. Never invent procedures, error-code meanings, commands, URLs, or policy. If evidence is insufficient, say so and ask focused questions. Give safe, numbered steps. Mention source document and page/section inline where possible. Do not claim to have changed systems or tickets.

Conversation so far:
{history_text}

Knowledge-base evidence:
{context or 'No relevant knowledge-base evidence was found.'}

User question: {question}

Answer in clear, simple language."""
    return str(llm.invoke(prompt).content)
