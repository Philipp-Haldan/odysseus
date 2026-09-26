"""Thinking must actually be off for local reasoning models on Ollama /v1.

Ollama's OpenAI-compatible route ignores the native `think` field
(ollama/ollama#15029), so sending it alone left qwen3 reasoning on every
call — thousands of generated tokens for work that needs dozens, and on a
small context window it consumed the whole budget and returned empty
content. `reasoning_effort` is the field that route honours.
"""

from src.llm_core import _suppress_ollama_thinking

OLLAMA_V1 = "http://host.docker.internal:11434/v1/chat/completions"


def test_sets_both_switches_for_a_thinking_model():
    payload = {}
    _suppress_ollama_thinking(payload, OLLAMA_V1, "qwen3.5:9b")
    assert payload["think"] is False
    # The one that actually takes effect on /v1.
    assert payload["reasoning_effort"] == "none"


def test_applies_to_custom_modelfile_variants():
    # Locally built variants (num_ctx baked in) must still be recognised.
    payload = {}
    _suppress_ollama_thinking(payload, OLLAMA_V1, "qwen35-9b-ctx64k")
    assert payload["reasoning_effort"] == "none"


def test_leaves_non_ollama_endpoints_untouched():
    payload = {}
    _suppress_ollama_thinking(payload, "https://api.anthropic.com/v1/messages", "qwen3.5:9b")
    assert payload == {}
