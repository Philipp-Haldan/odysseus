"""Regression tests: local models must not be sent loop-prone sampling.

The chat default is DEFAULT_TEMPERATURE = 1.0 and the "custom" preset ships
max_tokens 0, so a self-hosted model used to receive temperature 1.0 with no
repetition penalty and no reply cap. qwen3:30b-a3b answered such a request by
repeating the same letter ~15 times inside one <think> block, burning 20k
output tokens over 239s before replying that the *user* had repeated
themselves. Local payloads now carry the model family's documented sampling
recipe as a ceiling, plus a cap for the otherwise unbounded case.
"""
import pytest

from src import llm_core


@pytest.fixture
def local_endpoint(monkeypatch):
    import src.model_context as model_context
    monkeypatch.setattr(model_context, "is_local_endpoint", lambda _url: True)


@pytest.fixture
def cloud_endpoint(monkeypatch):
    import src.model_context as model_context
    monkeypatch.setattr(model_context, "is_local_endpoint", lambda _url: False)


LOCAL_URL = "http://host.docker.internal:11434/v1/chat/completions"


def test_local_qwen3_gets_qwen_sampling_recipe(local_endpoint):
    payload = {"model": "qwen3:30b-a3b", "temperature": 1.0}

    llm_core._apply_local_generation_stability(payload, LOCAL_URL, "qwen3:30b-a3b")

    assert payload["temperature"] == 0.6
    assert payload["top_p"] == 0.95
    assert payload["top_k"] == 20
    assert payload["presence_penalty"] == 0.5
    # No limit was sent, so the loop guard supplies one.
    assert payload["max_tokens"] == llm_core._LOCAL_STABILITY_MAX_TOKENS == 8192


def test_local_clamp_never_raises_a_calmer_preset(local_endpoint):
    payload = {"model": "qwen3:30b-a3b", "temperature": 0.2}

    llm_core._apply_local_generation_stability(payload, LOCAL_URL, "qwen3:30b-a3b")

    assert payload["temperature"] == 0.2


def test_local_explicit_max_tokens_survives(local_endpoint):
    # Deep research asks for 16384 on purpose (research_max_tokens); the cap
    # only fills in for callers that sent no limit at all.
    payload = {"model": "qwen3:30b-a3b", "temperature": 1.0, "max_tokens": 16384}

    llm_core._apply_local_generation_stability(payload, LOCAL_URL, "qwen3:30b-a3b")

    assert payload["max_tokens"] == 16384


def test_local_unknown_model_gets_generic_profile_only(local_endpoint):
    payload = {"model": "llama3.1:8b", "temperature": 1.0}

    llm_core._apply_local_generation_stability(payload, LOCAL_URL, "llama3.1:8b")

    assert payload["temperature"] == 0.8
    assert payload["top_p"] == 0.95
    # Nothing model-specific is known, so no penalties are invented.
    assert "presence_penalty" not in payload
    assert "top_k" not in payload
    assert payload["max_tokens"] == 8192


def test_cloud_payload_is_left_alone(cloud_endpoint):
    payload = {"model": "qwen3-max", "temperature": 1.0}

    llm_core._apply_local_generation_stability(
        payload, "https://api.example.com/v1/chat/completions", "qwen3-max")

    assert payload == {"model": "qwen3-max", "temperature": 1.0}


def test_reasoning_model_without_temperature_still_gets_capped(local_endpoint):
    # _omit_temperature() pops the field for some models; the cap must not
    # depend on a temperature being present.
    payload = {"model": "qwen3:30b-a3b", "max_completion_tokens": 0}

    llm_core._apply_local_generation_stability(payload, LOCAL_URL, "qwen3:30b-a3b")

    assert "temperature" not in payload
    assert payload["max_completion_tokens"] == 8192


def test_native_ollama_options_get_the_same_clamp(local_endpoint):
    payload = llm_core._build_ollama_payload(
        "qwen3:30b-a3b",
        [{"role": "user", "content": "hi"}],
        temperature=1.0,
        max_tokens=0,
    )

    llm_core._apply_ollama_local_stability(
        payload, "http://localhost:11434/api/chat", "qwen3:30b-a3b")

    options = payload["options"]
    assert options["temperature"] == 0.6
    assert options["top_p"] == 0.95
    assert options["top_k"] == 20
    assert options["presence_penalty"] == 0.5
    # Ollama's native name for the reply cap.
    assert options["num_predict"] == 8192
    assert "max_tokens" not in options


def test_native_ollama_hosted_api_is_left_alone(cloud_endpoint):
    payload = llm_core._build_ollama_payload(
        "qwen3:480b-cloud",
        [{"role": "user", "content": "hi"}],
        temperature=1.0,
        max_tokens=0,
    )

    llm_core._apply_ollama_local_stability(
        payload, "https://ollama.com/api/chat", "qwen3:480b-cloud")

    assert payload["options"] == {"temperature": 1.0}


def test_local_minimax_profile_is_unchanged(local_endpoint):
    # The MiniMax MLX ports keep their own, stricter profile.
    model = "cookietimeh/MiniMax-M2.7-BF16-ultra-uncensored-heretic-mlx-4Bit"
    payload = {"model": model, "temperature": 0.9}

    llm_core._apply_local_generation_stability(
        payload, "http://192.168.1.22:8091/v1/chat/completions", model)

    assert payload["temperature"] == 0.2
    assert payload["repetition_penalty"] == 1.12
    assert payload["max_tokens"] == 2048
