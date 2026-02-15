# Phase 1: Natural Language Query via CLI

## Goal
Expose an agent via `astro --ask "<question>"` that can answer ad-hoc analytical questions against any DuckDB warehouse.

## Architecture

```
User question
  │
  ▼
astro CLI (argparse)
  │
  ▼
Gemini Agent (tool-calling loop)
  │  ╭──────────────────────╮
  ├──┤ list_schemas()       │
  ├──┤ list_tables(schema)  │
  ├──┤ describe_table(s, t) │──▶ DataLayer ──▶ DuckDB
  ├──┤ sample_data(s, t, n) │
  ├──┤ execute_query(sql)   │
  │  ╰──────────────────────╯
  ▼
Natural language answer (stdout)
```

## Files Created

| File | Purpose |
|------|---------|
| `astro/__init__.py` | Package marker |
| `astro/cli.py` | CLI entry point — parses `--ask`, `--db`, `--model`; resolves warehouse path and API key |
| `astro/db.py` | `DataLayer` class — generic DuckDB introspection and query execution |
| `astro/agent.py` | `Agent` class — Gemini function-calling loop with retry/backoff |

## Design Decisions

### Why dynamic schema discovery (not hardcoded)?
The agent uses `information_schema` to discover schemas, tables, and columns at runtime. This means it works with **any** DuckDB warehouse — not just this e-commerce dataset. No schema knowledge is baked into the code.

### Why Gemini function calling (not prompt-only SQL generation)?
- The agent can **iteratively explore** before writing SQL — it doesn't need to guess table names.
- If a query fails, the error flows back as a tool result and the model can self-correct.
- Adding new tools later (e.g., `create_chart`, `explain_query`) is a config change, not a rewrite.

### Why cap results at 100 rows?
Prevents blowing up the LLM context window with huge result sets. The agent is told about truncation so it can refine queries with aggregations or filters.

### Error handling
- **Rate limits / timeouts**: Exponential backoff, 3 retries.
- **DB errors**: Caught and returned as tool results so the model can adapt.
- **Missing API key / DB**: Clear error message and exit.
- **Runaway loops**: Hard cap at 25 tool-calling turns.

## Configuration

| Setting | Source | Default |
|---------|--------|---------|
| API key | `GEMINI_API_KEY` or `GOOGLE_API_KEY` env var | (required) |
| Database | `--db` flag or auto-detect `warehouse/data.duckdb` | auto-detect |
| Model | `--model` flag | `gemini-2.0-flash` |

## Dependencies Added
- `google-genai>=1.0.0` (Gemini SDK)
- `hatchling` (build backend, for `project.scripts` to register the `astro` CLI)

## Status
- [x] Project structure and dependencies
- [x] DuckDB data layer with introspection
- [x] Gemini agent with tool-calling loop
- [x] CLI entry point registered (`astro --ask`)
- [x] Data layer smoke tested against warehouse
- [ ] End-to-end test with live Gemini API

## What This Does NOT Do (deferred to later phases)
- Semantic layer / metadata sync (Phase 2)
- Evaluation harness (Phase 3)
- Generalization verification (Phase 4)
- Chat UI (stretch)
- Cron sync (stretch)
