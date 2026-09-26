# -*- coding: utf-8 -*-
"""German chat messages must promote chat -> agent, just like English ones.

Regression for the 07.09.2026 session "Calendar Entry at Age Twenty-Six": the
user wrote "am 26. Usingen eintragen im Kalender" twice. Every routing pattern
in src/action_intents.py was English-only, so the message never escalated, the
model never got manage_calendar, and it answered with follow-up questions
instead of writing the event.
"""

from src.action_intents import classify_tool_intent, message_needs_tools


def test_the_message_that_failed_in_production():
    intent = classify_tool_intent("am 26. Usingen eintragen im Kalender")
    assert intent.needs_tools
    assert intent.category == "calendar"


def test_german_calendar_creation():
    assert message_needs_tools("trag mir nächsten Mittwoch abends mit Marc chillen ein")
    assert message_needs_tools("bitte einen Termin für Freitag 18 Uhr anlegen")
    assert message_needs_tools("mach mir einen Termin am Dienstag")
    assert message_needs_tools("leg das bitte in den Kalender")
    assert message_needs_tools("Zahnarzt am 12.11. im Kalender vormerken")


def test_german_separable_verbs_in_either_order():
    """"trag ... ein" and "sag ... ab" split the verb across the sentence."""
    assert message_needs_tools("trag das bitte für morgen um 19 Uhr ein")
    assert message_needs_tools("sag den Zahnarzttermin ab")
    assert message_needs_tools("verschieb den Termin auf Donnerstag")


def test_german_compound_nouns():
    """Zahnarzttermin / Kalendereintrag have no word boundary before the stem."""
    assert message_needs_tools("lösch den Zahnarzttermin")
    assert message_needs_tools("erstell einen Kalendereintrag für Montag")


def test_german_calendar_lookup():
    assert message_needs_tools("was steht diese Woche in meinem Kalender?")
    assert message_needs_tools("welche Termine habe ich morgen?")
    assert message_needs_tools("wann ist mein nächster Termin?")


def test_german_notes_and_reminders():
    assert message_needs_tools("erinnere mich um 16 Uhr an den Anruf")
    assert message_needs_tools("schreib Milch auf die Einkaufsliste")
    assert message_needs_tools("füg das zu meinen Aufgaben hinzu")


def test_german_email_and_ui_and_web():
    assert classify_tool_intent("antworte auf die Mail von Marc").category == "email"
    assert classify_tool_intent("hab ich ungelesene Mails?").category == "email"
    assert classify_tool_intent("öffne meinen Kalender").category == "ui"
    assert classify_tool_intent("such mal im Netz nach günstigen GPUs").category == "web"
    assert classify_tool_intent("wie ist das Wetter morgen?").category == "web"


def test_german_explanatory_questions_stay_in_chat():
    """Asking HOW a feature works must not spend a tool round."""
    assert not message_needs_tools("wie trage ich einen Termin ein?")
    assert not message_needs_tools("wie funktioniert der Kalender in Odysseus?")
    assert not message_needs_tools("kannst du mir erklären wie Kalender-Erinnerungen funktionieren?")
    assert not message_needs_tools("erklär mir mal den Unterschied zwischen Docker und nativ")


def test_ordinary_german_chat_is_not_escalated():
    assert not message_needs_tools("Hallo, wie geht es dir?")
    assert not message_needs_tools("Schreib mir einen Text über die Weimarer Republik")
    assert not message_needs_tools("Was hältst du von dem Ansatz?")
    assert not message_needs_tools("Fass mir das mal zusammen")
    assert not message_needs_tools("(subventioniert) was heißt das")
