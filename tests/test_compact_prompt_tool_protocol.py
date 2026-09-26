"""The compact prompt must describe the protocol the turn actually uses.

Ollama endpoints force `_is_api_model = False` (see `_is_ollama_native_url` /
`_is_ollama_openai_compat_url` in src/agent_loop.py), so no function schemas
are sent and `parse_tool_blocks` only recognises fenced blocks. The compact
prompt used to hardcode the native-calling wording regardless, telling local
models to "use native tool calls" and "do not write tool syntax in chat" while
nothing listened on that channel — they answered with ```json {"tool_name":
...} and the round ended having executed nothing.
"""
from datetime import datetime, timezone

from src.agent_loop import _assemble_prompt
from src.user_time import (
    clear_user_time_context,
    current_datetime_prompt,
    set_user_tz_name,
    set_user_tz_offset,
)

TOOLS = {"manage_calendar", "manage_notes"}


def teardown_function():
    clear_user_time_context()


def test_native_compact_prompt_unchanged():
    prompt = _assemble_prompt(TOOLS, set(), compact=True, native=True)

    assert "native tool/function calling" in prompt
    assert "do not write tool syntax or tool instructions in chat" in prompt
    assert "- Prefer native tool/function calling when tools are needed." in prompt
    # Native turns get the bare tool list; the schemas carry the shape.
    assert "- `manage_calendar`\n" in prompt or prompt.endswith("- `manage_calendar`")


def test_text_protocol_compact_prompt_teaches_fenced_blocks():
    prompt = _assemble_prompt(TOOLS, set(), compact=True, native=False)

    assert "fenced code blocks" in prompt
    assert "NO function-calling channel" in prompt
    # The two shapes local models reach for instead must be named explicitly.
    assert "```json" in prompt
    assert '{"tool_name"' in prompt
    # The native bullet is its twin and must not survive on a text turn.
    assert "- Prefer native tool/function calling when tools are needed." not in prompt
    assert "writing a fenced tool block" in prompt


def test_text_protocol_prompt_carries_usage_example_per_tool():
    """Each tool keeps its fenced example, so the model can copy the shape."""
    prompt = _assemble_prompt(TOOLS, set(), compact=True, native=False)

    for tool in TOOLS:
        assert f"- `{tool}` — " in prompt, f"{tool} lost its usage hint"

    # The preamble's worked example must have the shape the loop executes:
    # tool name as the fence tag, JSON object as the body, closing fence.
    # Asserted literally rather than by running parse_tool_blocks, because
    # tests/test_skill_index_prompt_injection.py stubs src.agent_tools with a
    # MagicMock in sys.modules and never restores it — importing tool_parsing
    # after that file rebuilds _TOOL_BLOCK_RE from the mock and it matches
    # nothing, which would make this test fail on collection order alone.
    assert '```manage_calendar\n{"action": "list_calendars"}\n```' in prompt


def test_datetime_prompt_resolves_upcoming_weekdays():
    """Weekday -> date is spelled out; small models get the arithmetic wrong."""
    clear_user_time_context()
    set_user_tz_offset(120)
    set_user_tz_name("Europe/Berlin")

    prompt = current_datetime_prompt(datetime(2026, 9, 6, 10, 11, tzinfo=timezone.utc))

    assert "Sunday = 2026-09-06  <- today" in prompt
    assert "Monday = 2026-09-07" in prompt
    assert "Tuesday = 2026-09-08" in prompt
    assert "Thursday = 2026-09-10" in prompt
    # 15 days, so "next weekend" is covered as well as this one.
    assert "Saturday = 2026-09-19" in prompt
    assert prompt.count(" = 2026-") == 15
