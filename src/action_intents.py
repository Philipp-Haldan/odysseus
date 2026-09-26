"""Lightweight routing hints for chat requests that need tools.

These patterns are intentionally conservative. They only promote plain chat
to agent mode when the user asks the assistant to take an action, not when the
user asks how a feature works.

German is matched as well. The rules used to be English-only, so a German
request like "am 26. Usingen eintragen im Kalender" stayed in plain chat, the
model never saw manage_calendar, and it answered by asking follow-up questions
instead of writing the event. German also puts the separable verb particle at
the end of the clause ("... eintragen im Kalender"), so the German rules match
verb and object in EITHER order via :func:`_either_order` rather than assuming
English word order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Pattern


@dataclass(frozen=True)
class ToolIntent:
    """A cheap, deterministic chat-to-agent routing decision."""

    needs_tools: bool
    category: str = ""
    reason: str = ""


_ACTION_QUESTION = r"\b(?:can|could|would|will)\s+you\s+"
_ACTION_FOLLOWUP = (
    r"\b(?:you\s+should\s+be\s+able\s+to|"
    r"(?:can|could|would|will|should)\s+you|"
    r"you\s+(?:can|could|would|will|should|need\s+to|have\s+to))\s+"
)
_PLEASE = (
    r"^\s*(?:(?:please|ok(?:ay)?|alright|right|sure|cool|great|thanks|"
    r"bitte|gut|super|danke|jo|joa|alles\s+klar|na\s+gut)[\s,.!-]+)*"
)

_CALENDAR_ACTION = (
    r"(?:add|adding|create|creating|recreate|recreating|schedule|scheduling|"
    r"reschedule|rescheduling|book|booking|put|set\s+up|make|making|"
    r"delete|deleting|remove|removing|cancel|cancelling|canceling)"
)
_CALENDAR_THING = r"(?:calendar|calendar\s+(?:entry|item)|event|meeting|appointment|entry|call)"
_CALENDAR_READ_THING = r"(?:calendar|schedule|events?|meetings?|appointments?|classes?)"


def _either_order(first: str, second: str, gap: int = 160) -> str:
    """Match two fragments in either order, within ``gap`` characters.

    German separates verb particles ("trag das bitte ein"), and puts the
    infinitive last ("am 26. Usingen eintragen im Kalender"), so the object can
    precede or follow the verb. Ordered English-style regexes miss half of it.
    """
    return rf"(?:{first}[\s\S]{{0,{gap}}}{second}|{second}[\s\S]{{0,{gap}}}{first})"


# --- German ------------------------------------------------------------------
# Nouns that name a calendar entry.
_DE_CAL_THING = (
    # \w* on both sides: German compounds ("Zahnarzttermin", "Kalendereintrag")
    # give no word boundary in front of the stem.
    r"\b\w*(?:kalender|termin|verabredung|besprechung|"
    r"veranstaltung|meeting|geburtstag)\w*\b"
)
# Verbs that create, move or drop one. Stems are matched with \w* so every
# conjugation ("trage", "trägst", "eingetragen", "einzutragen") is covered.
_DE_CAL_ACTION = (
    r"\b(?:(?:ein|vor|an|um)?(?:trag|träg|plan|leg|merk)\w*|"
    r"erstell\w*|buch\w*|notier\w*|reservier\w*|mach\w*|setz\w*|"
    r"absag\w*|abzusagen|lösch\w*|entfern\w*|streich\w*|verschieb\w*|"
    r"cancel\w*)\b"
    # Separable verbs: "sag den Termin ab", "trag das ein", "schieb das um".
    # Zero-width lookahead for the particle, so the match does not consume the
    # words the other half of the rule still has to find.
    r"|\b(?:sag|schieb|leg|trag|träg|plan|streich|setz|merk|mach|buch|nehm)\w*"
    r"(?=[\s\S]{0,60}?\b(?:ab|ein|um|vor|an|aus|rein)\b)"
)
# "trag ... ein" / "eintragen" / "einplanen" on its own — used when the user
# names no calendar noun at all ("am 26. Usingen eintragen").
_DE_ENTER = (
    r"\b(?:ein(?:ge|zu)?trag\w*|ein(?:ge|zu)?plan\w*|"
    # Separable "trag ... ein" / "plan ... ein" / "leg ... rein" — again a
    # lookahead, so the date half of the rule can still match the words between.
    r"(?:trag|träg|plan|leg|pack)\w*(?=[\s\S]{0,60}?\b(?:ein|rein)\b))"
)
# Date-ish expressions. Enough to tell "trag das ein" (calendar) apart from
# "trag dich in die Mailingliste ein" (not ours).
_DE_WHEN = (
    r"\b(?:heute|morgen\b|übermorgen|heute\s+abend|abends|vormittags|nachmittags|"
    r"montag\w*|dienstag\w*|mittwoch\w*|donnerstag\w*|freitag\w*|samstag\w*|"
    r"sonnabend\w*|sonntag\w*|wochenende|"
    r"(?:nächste|kommende|diese)[nrms]?\s+(?:woche|monat|wochenende)|"
    r"am\s+\d{1,2}\.|\d{1,2}\.\d{1,2}\.|um\s+\d{1,2}(?::\d{2})?\s*uhr|\d{1,2}\s*uhr)"
)
# Calendar lookups.
_DE_CAL_READ = (
    r"\b(?:was\s+(?:steht|habe?\s+ich|ist)\b[\s\S]{0,60}?\b(?:kalender|termin\w*|vor)\b|"
    r"welche[nrs]?\s+termin\w*|"
    r"wann\s+(?:ist|habe?\s+ich)\b[\s\S]{0,40}?\btermin\w*|"
    r"(?:hab|habe)\s+ich\b[\s\S]{0,60}?\b(?:termin\w*|vor)\b|"
    r"(?:zeig|zeige)\w*\b[\s\S]{0,40}?\b(?:kalender|termin\w*)\b)"
)

_DE_NOTE_THING = (
    r"\b(?:notiz\w*|aufgabe\w*|to-?do\w*|merkzettel|einkaufsliste|"
    r"aufgabenliste|erinnerung\w*|checkliste)\b"
)
_DE_NOTE_ACTION = (
    r"\b(?:(?:auf|hinzu|an|ein)?(?:schreib|setz|füg|leg|trag|nehm|pack)\w*|"
    r"erstell\w*|notier\w*|mach\w*|hak\w*|erledig\w*|streich\w*|lösch\w*)\b"
)

_DE_MAIL_THING = r"\b(?:e-?mails?|mails?|postfach|posteingang|ungelesene[nrs]?)\b"
_DE_MAIL_ACTION = (
    r"\b(?:schreib\w*|schick\w*|(?:be)?antwort\w*|weiterleit\w*|archivier\w*|"
    r"lösch\w*|check\w*|prüf\w*|(?:nach)?schau\w*|guck\w*|les\w*|lies|markier\w*)\b"
)

_DE_PANEL = (
    r"(?:kalender|notizen|todos?|posteingang|postfach|dokumente|galerie|"
    r"einstellungen|cookbook|chats?|sitzungen|skills|gedächtnis|erinnerungen)"
)


_EXPLANATORY_PREFIX = re.compile(
    r"^\s*(?:how\s+(?:do|can)\s+i|can\s+you\s+explain|what\s+about|tell\s+me\s+how|show\s+me\s+how"
    # German mirrors: "wie trage ich ... ein?", "erklär mir ...", "was ist mit ...".
    r"|wie\s+(?:kann|könnte|mache|mach|trage|trag|erstelle|lege|füge|schreibe)\s+ich"
    r"|wie\s+funktioniert"
    r"|(?:kannst|könntest)\s+du\s+(?:mir\s+)?(?:mal\s+)?erklären"
    r"|erklär(?:e|st)?\s+mir"
    r"|(?:zeig|sag)\w*\s+mir\s+(?:mal\s+)?wie"
    r"|was\s+ist\s+(?:mit|eigentlich)"
    r"|was\s+bedeutet"
    r")\b",
    re.I,
)

_PANEL = (
    r"(?:calendar|notes?|inbox|email|mail|documents?|docs|library|gallery|"
    r"settings|cookbook|sessions?|chats?|skills|memories|memory|brain)"
)

_ROUTING_PATTERNS: tuple[tuple[str, str, Pattern[str]], ...] = tuple(
    (category, reason, re.compile(pattern, re.I))
    for category, reason, pattern in (
        # Calendar/event creation. Covers "Can you add an entry to my
        # calendar?", imperatives like "add lunch to my calendar", and
        # follow-ups such as "you should be able to create that event now".
        ("calendar", "assistant calendar action request", rf"{_ACTION_QUESTION}{_CALENDAR_ACTION}\b.{{0,120}}\b{_CALENDAR_THING}\b"),
        ("calendar", "calendar follow-up action request", rf"{_ACTION_FOLLOWUP}{_CALENDAR_ACTION}\b.{{0,120}}\b{_CALENDAR_THING}\b"),
        ("calendar", "calendar imperative action request", rf"{_PLEASE}{_CALENDAR_ACTION}\b.{{0,120}}\b{_CALENDAR_THING}\b"),
        ("calendar", "calendar target action request", rf"{_PLEASE}{_CALENDAR_ACTION}\b.{{0,120}}\b(?:to|on|in|into|for)\s+(?:my\s+|the\s+|this\s+)?calendar\b"),
        ("calendar", "calendar item action request", rf"{_PLEASE}{_CALENDAR_ACTION}\s+(?:it\s+)?(?:a\s+|an\s+)?(?:calendar\s+)?(?:event|meeting|appointment|entry|item|call)\b"),
        ("calendar", "calendar target action request", rf"\b{_CALENDAR_ACTION}\b.{{0,120}}\b(?:to|on|in|into|for)\s+(?:my\s+|the\s+|this\s+)?calendar\b"),
        ("calendar", "put item on calendar request", r"\bput\s+.+\bon\s+(?:my\s+)?calendar\b"),

        # Calendar/event lookup. A question such as "Do I have Taekwondo
        # classes this week?" needs the calendar tool; plain chat cannot know.
        ("calendar", "calendar lookup request", rf"\b(?:list|show|check|find)\b.{{0,120}}\b(?:my\s+|the\s+)?(?:upcoming|next|today'?s?|tomorrow'?s?|this\s+week'?s?)\b.{{0,120}}\b{_CALENDAR_READ_THING}\b"),
        ("calendar", "calendar lookup question", rf"\b(?:what|which)\b.{{0,120}}\b(?:upcoming|next|today'?s?|tomorrow'?s?|this\s+week'?s?)\b.{{0,120}}\b{_CALENDAR_READ_THING}\b"),
        ("calendar", "calendar availability question", rf"\bdo\s+i\s+have\b.{{0,120}}\b(?:upcoming|next|today|tomorrow|this\s+week)\b.{{0,120}}\b{_CALENDAR_READ_THING}\b"),
        ("calendar", "calendar agenda question", r"\bwhat(?:'s| is)\s+on\s+(?:my\s+)?calendar\b"),
        ("calendar", "next calendar item question", r"\bwhen\s+(?:is|are)\s+(?:my\s+)?next\s+(?:event|meeting|appointment|class)\b"),

        # Notes, todos, checklists, and reminders.
        ("notes", "reminder request", r"\bremind\s+me\b"),
        ("notes", "assistant note/todo action request", rf"{_ACTION_QUESTION}(?:add|create|make|take|jot|write\s+down|set)\b.{{0,120}}\b(?:note|todo|task|checklist|reminder)\b"),
        ("notes", "note/todo imperative request", rf"{_PLEASE}(?:add|create|make)\s+(?:a\s+|an\s+)?(?:todo|task|reminder|note|checklist)\b"),
        ("notes", "take note request", rf"{_PLEASE}(?:take|jot|write\s+down)\s+(?:a\s+|an\s+)?note\b"),
        ("notes", "add item to notes/todo request", rf"{_PLEASE}(?:add|jot|write\s+down)\b.{{0,120}}\b(?:to|in|into)\s+(?:my\s+|the\s+)?(?:todo(?:\s+list)?|task\s+list|notes?|checklist)\b"),
        ("notes", "set reminder request", rf"{_PLEASE}set\s+(?:a\s+)?reminder\b"),
        ("notes", "assistant reminder request", rf"{_ACTION_QUESTION}set\s+(?:a\s+)?reminder\b"),

        # Email actions.
        ("email", "assistant email action request", rf"{_ACTION_QUESTION}(?:send|write|reply|email|message|archive|delete|mark)\b.{{0,120}}\b(?:emails?|mail|messages?|inbox|unread|read)\b"),
        ("email", "send/write/reply email request", rf"{_PLEASE}(?:send|write|reply)\b.{{0,120}}\b(?:emails?|mail|messages?)\b"),
        ("email", "archive/delete/mark email request", rf"{_PLEASE}(?:archive|delete|mark)\b.{{0,120}}\b(?:emails?|mail|messages?|inbox)\b"),
        ("email", "email composition request", r"\b(?:send|write|reply)\s+(?:an?\s+)?(?:email|message|mail)\b"),
        ("email", "email contact request", r"\bemail\s+\w+\b"),
        ("email", "check inbox request", r"\bcheck\s+(?:my\s+)?(?:email|inbox|mail)\b"),
        ("email", "unread email request", r"\bunread\s+(?:email|mail)s?\b"),

        # UI/control-plane actions that should open panels or flip toggles.
        ("ui", "open/show panel request", rf"{_PLEASE}(?:open|show|bring\s+up)\s+(?:me\s+)?(?:my\s+|the\s+)?{_PANEL}\b"),
        ("ui", "tool or feature toggle request", r"\b(?:disable|enable|turn\s+(?:on|off))\s+(?:the\s+)?(?:shell|search|web|browser|documents?|memory|skills|images?|calendar|email|mail|research|incognito)\b"),

        # Deep research jobs, not quick conceptual mentions of research.
        ("web", "explicit web search request", rf"{_PLEASE}(?:do|run|use|perform|make)\s+(?:a\s+)?(?:web\s+search|search\s+the\s+web)\b.+"),
        ("web", "generic search request", rf"{_PLEASE}search\s+(?!(?:my\s+)?(?:chats?|history|sessions?|notes?|todos?|emails?|mail|inbox|documents?|docs|gallery|images?|files?)\b).+"),
        ("web", "web lookup imperative request", rf"{_PLEASE}(?:web\s+search|search\s+the\s+web|search\s+online|look\s+up|google(?:\s+it)?)\b.*"),
        ("web", "short web lookup follow-up", rf"{_PLEASE}(?:just\s+)?(?:look\s+it\s+up|look\s+up|search\s+(?:online|web|now)|search\s+it)\b\s*$"),
        ("web", "assistant short web lookup request", rf"{_ACTION_QUESTION}(?:search|look\s+up|google)(?:\s+(?:online|web|now|it))?\b.*"),
        ("web", "assistant web lookup request", rf"{_ACTION_QUESTION}(?:web\s+search|search\s+the\s+web|search\s+online|look\s+up|google(?:\s+it)?)\b.*"),
        ("web", "assistant weather check request", rf"{_ACTION_QUESTION}(?:check|find|get|look\s+up)\b.{{0,100}}\b(?:weather|forecast)\b.*"),
        ("web", "news lookup request", r"\b(?:news|headlines)\s+(?:in|from|about|for)\s+[\w\s.-]{2,80}\??\s*$"),
        ("web", "forecast lookup request", r"\b(?:hourly|daily|weekly|local)\s+(?:weather\s+)?forecast\b|\b(?:weather\s+)?forecast\s+(?:for|today|tomorrow|now|hourly)\b"),
        ("web", "weather lookup request", r"\bweather\b.{0,80}\b(?:hourly|rain|raining|rin|today|tomorrow|update|current|now)\b|\b(?:hourly|rain|raining|rin)\b.{0,80}\bweather\b"),
        ("web", "rain lookup request", r"\b(?:hourly|daily|weekly|local|today|tomorrow|current|now|update)\b.{0,100}\b(?:rain|raining|rainy|precipitation|showers?)\b|\b(?:rain|raining|rainy|precipitation|showers?)\b.{0,100}\b(?:hourly|daily|weekly|local|today|tomorrow|current|now|update|in|for|at)\b"),
        ("web", "bare weather lookup request", r"\b(?:weather|forecast)\s+(?:in|for|at)?\s*[\w\s.-]{2,80}\??\s*$|\b[\w\s.-]{2,80}\s+(?:weather|forecast)\??\s*$"),
        ("web", "latest info lookup request", r"\b(?:latest|current|newest|recent|up(?: |-)?to(?: |-)?date)\s+(?:info|information|updates?|details?|developments?)\s+(?:on|about|for|in)\s+[\w\s.,:'\"/-]{2,120}\??\s*$"),
        ("web", "current/latest lookup request", r"\b(?:current|latest|today'?s?|right\s+now|live|online)\b.{0,120}\b(?:rate|price|news|weather|forecast|score|exchange|market|status)\b"),
        ("web", "rate/price/news lookup request", r"\b(?:rate|rates|price|prices|news|weather|forecast|score|exchange|currency|market)\b.{0,120}\b(?:now|today|current|latest|online|live|search|look\s+up|find)\b"),
        ("web", "conversion-rate lookup request", r"\b(?:convert|conversion|exchange)\b.{0,120}\b(?:rate|rates|currency|currencies|price|prices)\b"),
        ("research", "deep research imperative request", rf"{_PLEASE}(?:research|deep\s+dive|look\s+into|investigate)\s+.+"),
        ("research", "assistant deep research request", rf"{_ACTION_QUESTION}(?:research|do\s+research|deep\s+dive|look\s+into|investigate)\s+.+"),

        # Shell / remote-host intent.
        ("shell", "ssh request", r"\bssh\s+(?:in)?to\b"),
        ("shell", "ssh target request", r"\bssh\s+\w+"),
        ("shell", "remote command request", r"\b(run|execute)\s+.{1,40}\bon\s+\w+"),
        ("shell", "assistant command execution request", r"\b(can|could|please|would)\s+you\s+(run|execute|exec)\b"),
        # Shell verbs only count in imperative position (start of message,
        # optionally after "please") or as a "can you ..." request. A bare
        # word match promoted informational questions ("What does the grep
        # command do?") and incidental uses ("My cat ate my homework").
        ("shell", "imperative shell command request", rf"{_PLEASE}(deploy|build|install|restart|reboot|kill|tail|grep|cat|ls|cd|cp|mv|rm)\b\s+\S+"),
        ("shell", "assistant shell command request", rf"{_ACTION_QUESTION}(deploy|build|install|restart|reboot|kill|tail|grep|cat|ls|cd|cp|mv|rm)\b\s+\S+"),
        ("shell", "system/file check request", r"\b(check|see)\s+(if|whether|what)\s+.{1,40}\b(running|process|service|port|file|exists?)\b"),
        # --- German -------------------------------------------------------
        # The user writes German (see the "respond in German" preference), so
        # none of the English rules above ever fired: calendar and notes
        # requests stayed in plain chat and were answered by a tool-less model.
        ("calendar", "German calendar action request", _either_order(_DE_CAL_ACTION, _DE_CAL_THING)),
        ("calendar", "German 'eintragen' with a date", _either_order(_DE_ENTER, _DE_WHEN, 120)),
        ("calendar", "German calendar lookup request", _DE_CAL_READ),

        ("notes", "German reminder request", r"\berinner(?:e|st|t)?\s+mich\b"),
        ("notes", "German note/todo action request", _either_order(_DE_NOTE_ACTION, _DE_NOTE_THING)),

        ("email", "German email action request", _either_order(_DE_MAIL_ACTION, _DE_MAIL_THING)),
        ("email", "German unread mail lookup", r"\b(?:neue|ungelesene)[nrs]?\b[\s\S]{0,20}\b(?:e-?)?mails?\b"),

        ("ui", "German open panel request", rf"{_PLEASE}(?:öffne|öffnen|zeig|zeige|mach)\s+(?:mir\s+)?(?:mal\s+)?(?:mein(?:en|e|em)?\s+|den\s+|die\s+|das\s+)?{_DE_PANEL}\b"),
        ("ui", "German tool toggle request", r"\b(?:schalte|mach|stell|stelle)\s+(?:mal\s+)?(?:die\s+|den\s+|das\s+)?(?:shell|websuche|web-?suche|suche|browser|dokumente|gedächtnis|skills|bilder|kalender|mails?|recherche|incognito)\s+(?:mal\s+)?(?:ein|aus|an|ab)\b"),

        ("web", "German web search request", rf"{_PLEASE}(?:such|suche|schau|guck|google|recherchier)\w*\s+(?:mal\s+)?(?:im\s+(?:netz|internet|web)|online|nach)\b.+"),
        ("web", "German weather request", r"\bwie\s+(?:ist|wird)\s+das\s+wetter\b|\bwetter\w*\s+(?:heute|morgen|in|für)\b|\bregnet\s+es\b"),
        ("research", "German deep research request", rf"{_PLEASE}(?:recherchier\w*|erforsch\w*|untersuch\w*)\s+.+"),
    )
)

_TOOL_INTENT_PATTERNS: tuple[Pattern[str], ...] = tuple(
    pattern for _, _, pattern in _ROUTING_PATTERNS
)


def classify_tool_intent(text: str) -> ToolIntent:
    """Classify whether a chat message should be promoted to agent mode."""
    if not text:
        return ToolIntent(False, reason="empty message")
    if _EXPLANATORY_PREFIX.search(text):
        return ToolIntent(False, reason="explanatory feature question")
    for category, reason, pattern in _ROUTING_PATTERNS:
        if pattern.search(text):
            return ToolIntent(True, category=category, reason=reason)
    return ToolIntent(False, reason="no tool-action pattern matched")


def message_needs_tools(text: str, patterns: Iterable[Pattern[str]] = _TOOL_INTENT_PATTERNS) -> bool:
    """Return True when a plain chat message should be promoted to agent mode."""
    if not text:
        return False
    if _EXPLANATORY_PREFIX.search(text):
        return False
    if patterns is _TOOL_INTENT_PATTERNS:
        return classify_tool_intent(text).needs_tools
    return any(pattern.search(text) for pattern in patterns)
