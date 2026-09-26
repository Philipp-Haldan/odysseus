# Odysseus — Arbeitsstand (Claude)

**Root:** `C:\Users\phili\Documents\pewdiepie_odysseus\odysseus`  
**Was es ist:** Self-hosted AI workspace (nicht Godot).

## Lokal starten (Windows)

- `Odysseus starten.bat` / `start-odysseus.ps1`
- Docker: `docker compose up -d --build` → `http://localhost:7000`
- Stop: `Odysseus stoppen.bat` / `stop-odysseus.ps1`

## Wichtige Ordner

| Ordner | Rolle |
|--------|--------|
| `app.py`, `launcher.py` | Einstieg |
| `routes/`, `services/`, `core/` | Backend |
| `static/`, `src/` | Frontend / Assets |
| `config/`, `data/` | Config / Runtime-Daten |
| `integrations/claude/` | Claude Code Skill-Integration |
| `mcp_servers/` | MCP |
| `docs/`, `ROADMAP.md` | Doku / Prioritäten |
| `tests/` | Tests |

## High Priority (aus ROADMAP, gekürzt)

- Bugs squashen, Fresh-Install Smoke (Win/Docker/WSL)
- Integration audit, Self-host troubleshooting cookbook
- Cookbook reliability / SGLang / Model-Ranking / Error-Logs
- Agent prompt/context bloat für kleine lokale Modelle
- Skill/tool prompt-injection Absicherung

## Claude Desktop

Shortcut: **Claude Code - Odysseus**  
Kein Kit-Strang A–D — normales Code-Arbeiten an diesem Repo.
