"""Shared response markers used by generation and deterministic evaluation."""

REFUSAL_PREFIX = "当前资料依据不足"
PREMISE_CORRECTION_INSTRUCTION = (
    "如果问题前提与资料冲突，不要使用拒答短语；应明确纠正前提并依据资料回答。"
)
GENERATION_SYSTEM_ERROR_PREFIXES = (
    "LLM未配置：",
    "LLM请求失败",
)
