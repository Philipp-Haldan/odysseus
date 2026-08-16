# Odysseus — Claude Code / Desktop

Self-hosted AI workspace (Chat, Agents, Research, Docs, Mail, Notes, Calendar, Cookbook, MCP).

**Projektroot:** dieses Verzeichnis (`pewdiepie_odysseus\odysseus`).

## Schnellkontext

- Stack: Python (FastAPI-artig / `app.py`, `routes/`, `services/`, `core/`), Docker (`docker-compose.yml`), optional native Windows (`start-odysseus.ps1`)
- UI: typisch `http://localhost:7000`
- Branch-Hinweis README: `dev` = neueste Änderungen; `main` = kuratierter
- Claude-Integration im Repo: `integrations/claude/` (Skill-Bundle für Odysseus↔Claude Code)
- **Kein Godot-Projekt** — Godot-Kit-Prompts (`/00`…`/05`) hier **nicht** als Standard nutzen

## Pflicht vor Änderungen

1. `README.md` + ggf. `docs/setup.md` / `ROADMAP.md` / `ODYSSEUS_DEV.md`
2. Keine Secrets: `.env` nicht committen, keine Tokens in Docs
3. Scope klein halten — große Refactors nur mit Plan
4. Tests: `tests/` beachten; bei Fixes möglichst bestehenden Teststil folgen

## Typische Einstiege

| Ziel | Hinweis |
|------|---------|
| App starten | `Odysseus starten.bat` / `start-odysseus.ps1` oder Docker Compose |
| Bug / Feature | Symptom + betroffene Area (`routes`, `services`, `static`, `cookbook`, …) |
| Claude↔Odysseus API | `integrations/claude/README.md` |
| Security | `SECURITY.md`, `THREAT_MODEL.md` |

## Design / Produkt

Nutzer entscheidet UX und Priorität live — kurz iterieren, nachfragen, nicht lange autonom wegbauen.

## Stand

Siehe `ODYSSEUS_DEV.md` und `ROADMAP.md`.
