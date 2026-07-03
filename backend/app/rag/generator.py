from openai import OpenAI

from app.core.config import get_llm_config

SYSTEM_PROMPT = (
    "你是一个技术文档知识库助手。只根据下面提供的资料回答问题，不要编造资料中没有的信息。"
    "如果资料不足以回答问题，请明确说明“当前资料依据不足”，不要强行回答。"
    "回答末尾必须列出实际引用的资料编号，例如：引用：[资料1][资料3]。"
)


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        parts.append(f"[资料{i}] 来源: {c['source']} 第{c['page']}页 (chunk_id={c['chunk_id']})\n{c['text']}")
    return "\n\n".join(parts)


def generate_answer(question: str, chunks: list[dict]) -> str:
    config = get_llm_config()
    client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])

    context = build_context(chunks)
    user_prompt = f"资料：\n{context}\n\n问题：{question}"

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
