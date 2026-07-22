from unittest.mock import MagicMock, patch

import openai

from app.rag.generator import build_context, generate_answer


def test_build_context_formats_chunks_with_citation_labels():
    """build_context() prepends a [资料N] label to each chunk and includes
    source/page/chunk_id so the LLM (and the user) can trace citations back.
    """
    chunks = [
        {"chunk_id": "a.pdf_p1_0", "source": "a.pdf", "page": 1, "text": "hello"},
        {"chunk_id": "b.md_p0_0", "source": "b.md", "page": 0, "text": "world"},
    ]
    context = build_context(chunks)

    assert "[资料1]" in context
    assert "[资料2]" in context
    assert "来源: a.pdf 第1页" in context
    assert "hello" in context
    assert "world" in context


def test_generate_answer_returns_friendly_message_when_api_key_missing(monkeypatch):
    """When get_llm_config() raises RuntimeError (missing API key), generate_answer
    should catch it and return a readable message instead of crashing.
    """
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    answer = generate_answer("some question", [{"chunk_id": "x", "source": "y", "page": 1, "text": "z"}])

    assert "LLM未配置" in answer


def test_generate_answer_returns_friendly_message_on_openai_error(monkeypatch):
    """When the OpenAI SDK call itself fails (network error, rate limit, etc.),
    generate_answer should catch openai.OpenAIError and return a readable
    message instead of crashing. The OpenAI client is mocked so this test runs
    instantly and doesn't need a real API key or network access.
    """
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")

    with patch("app.rag.generator.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = openai.OpenAIError("connection failed")
        mock_openai_cls.return_value = mock_client

        answer = generate_answer("q", [{"chunk_id": "x", "source": "y", "page": 1, "text": "z"}])

    assert "LLM请求失败" in answer


def test_generate_answer_returns_llm_content_on_success(monkeypatch):
    """Happy path: when the mocked client returns a normal response,
    generate_answer should return exactly the text content the LLM produced.
    """
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key-for-test")

    fake_response = MagicMock()
    fake_response.choices[0].message.content = "这是模拟的回答"

    with patch("app.rag.generator.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = fake_response
        mock_openai_cls.return_value = mock_client

        answer = generate_answer("q", [{"chunk_id": "x", "source": "y", "page": 1, "text": "z"}])

    assert answer == "这是模拟的回答"
