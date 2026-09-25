"""A research task must be able to dictate its own report shape.

FINAL_REPORT_PROMPT demands a 1500-word minimum plus an executive summary, and
CATEGORY_PROMPTS can layer a second skeleton on top (the fact-check template
turned a German distress monitor into an English "## The Claim" report). A
caller that states its own format carries a marker; then those defaults are
skipped and the short report is not auto-expanded.
"""

from src.deep_research import (
    FORMAT_OVERRIDE_MARKER,
    FINAL_REPORT_PROMPT,
    FINAL_REPORT_PROMPT_CALLER_FORMAT,
)


def test_default_template_still_asks_for_the_long_form():
    assert "MINIMUM 1500 words" in FINAL_REPORT_PROMPT
    assert "executive summary" in FINAL_REPORT_PROMPT


def test_caller_format_template_imposes_no_shape_of_its_own():
    t = FINAL_REPORT_PROMPT_CALLER_FORMAT
    assert "1500" not in t
    assert "executive summary" not in t.lower()
    assert "override every default" in t
    # It must still carry the two non-negotiables.
    assert "{question}" in t and "{report}" in t
    assert "never invent a source" in t


def test_marker_is_a_comment_so_it_never_shows_up_in_a_report():
    assert FORMAT_OVERRIDE_MARKER.startswith("<!--")
    assert FORMAT_OVERRIDE_MARKER.endswith("-->")
