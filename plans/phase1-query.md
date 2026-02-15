# Phase 1: Natural Language Query via CLI

## Goal
Expose an interactive agent via `astro` (or `astro --ask "<question>"`) that can answer ad-hoc analytical questions against any DuckDB warehouse in a persistent chat session.

## Architecture

```
$ astro                        # interactive chat (or --ask for first question)
  ┌─────────────────────────┐
  │  astro> <question>       │◄── REPL loop (stdin)
  └────────┬────────────────┘
           │
           ▼
  Gemini Agent (persistent conversation history)
    │  ╭──────────────────────╮
    ├──┤ list_schemas()       │
    ├──┤ list_tables(schema)  │
    ├──┤ describe_table(s, t) │──▶ DataLayer ──▶ DuckDB
    ├──┤ sample_data(s, t, n) │
    ├──┤ execute_query(sql)   │
    ├──┤ create_chart(type,…) │
    │  ╰──────────────────────╯
    ▼
  Answer + Sources (stdout) ──► back to astro> prompt
```

## Files Created

| File | Purpose |
|------|---------|
| `astro/__init__.py` | Package marker |
| `astro/fmt.py` | Terminal formatting — ANSI colors, banner, styled prompts, sources footer |
| `astro/display.py` | Intermediate result rendering — tables, schema lists, query results on stderr |
| `astro/charts.py` | Terminal chart rendering via plotext (bar, line, scatter, histogram) |
| `astro/cli.py` | CLI entry point — parses args, runs optional `--ask`, then enters interactive REPL |
| `astro/db.py` | `DataLayer` class — generic DuckDB introspection and query execution |
| `astro/agent.py` | `Agent` class — Gemini function-calling loop with persistent conversation history |

## Design Decisions

### Why dynamic schema discovery (not hardcoded)?
The agent uses `information_schema` to discover schemas, tables, and columns at runtime. This means it works with **any** DuckDB warehouse — not just this e-commerce dataset. No schema knowledge is baked into the code.

### Why Gemini function calling (not prompt-only SQL generation)?
- The agent can **iteratively explore** before writing SQL — it doesn't need to guess table names.
- If a query fails, the error flows back as a tool result and the model can self-correct.
- Adding new tools later (e.g., `create_chart`, `explain_query`) is a config change, not a rewrite.

### Why cap results at 100 rows?
Prevents blowing up the LLM context window with huge result sets. The agent is told about truncation so it can refine queries with aggregations or filters.

### Interactive chat with persistent history
The agent maintains `_contents` (the full Gemini conversation) as instance state rather than local to a single `ask()` call. This means:
- Schema discovery from question 1 is already in context for question 2 — no redundant `list_schemas` / `describe_table` calls.
- The model can reference prior answers ("break that down by region").
- Query error memory also persists across questions in the same session.

The CLI runs an `astro>` REPL after startup. `--ask` is optional — if provided, that question is answered first, then the REPL continues. Ctrl-C during a query cancels it without killing the session; Ctrl-C/Ctrl-D at the prompt exits.

### Terminal charts (plotext)
The agent has a `create_chart` tool it can call after running a query. The system prompt instructs the model to create charts when results have a clear categorical dimension and a numerical measure. Chart types: bar, line, scatter, histogram. Charts render to stderr via `plotext.build()` (returns a string) so they don't pollute the stdout answer stream.

### Intermediate result display
Every tool call displays its results to the user on stderr as the agent works — schema lists, table listings with row counts, column definitions, and formatted query result tables. This gives the user visibility into what the agent is doing without waiting for the final answer. All intermediate output uses `fmt.DIM` styling to stay visually recessive.

### Source citations
The agent tracks which tables and queries were used during each question (`Agent._current_sources`). After the answer, the CLI prints a "Sources" footer showing deduplicated table names and numbered SQL queries with row counts. Sources reset per `ask()` call. The tracking is automatic (built into `_execute_tool()`), not dependent on the model.

### Query error memory
When an `execute_query` call fails (SQL error, DuckDB exception, etc.), the agent records the failed SQL and error message in an in-memory list (`Agent._query_errors`). On every subsequent LLM call, `_build_system_prompt()` appends these past errors to the system prompt under a "Previous Query Errors" section. This lets the model see exactly which queries failed and why, so it avoids repeating the same mistakes (wrong column names, bad syntax, etc.) without consuming extra tool-call turns.

### Error handling
- **Rate limits / timeouts**: Exponential backoff, 3 retries.
- **Auth errors (401/403)**: Fail fast with actionable message — no retries.
- **DB errors**: Caught and returned as tool results so the model can adapt; also recorded in query error memory.
- **Missing API key / DB**: Clear error message and exit.
- **Preflight check**: A minimal API call on init to catch bad credentials before the agent loop starts.
- **Runaway loops**: Hard cap at 25 tool-calling turns.

## Configuration

| Setting | Source | Default |
|---------|--------|---------|
| API key | `GEMINI_API_KEY` or `GOOGLE_API_KEY` env var / `.env` | (required) |
| GCP project | `GOOGLE_CLOUD_PROJECT` env var / `.env` | (optional — enables Vertex AI backend) |
| GCP location | `GOOGLE_CLOUD_LOCATION` env var / `.env` | `us-central1` |
| Database | `--db` flag or auto-detect `warehouse/data.duckdb` | auto-detect |
| Model | `--model` flag | `gemini-2.0-flash` |

The CLI auto-loads a `.env` file from the project root via `python-dotenv`.

## Dependencies Added
- `google-genai>=1.0.0` (Gemini SDK)
- `plotext>=5.2.8` (terminal charts)
- `python-dotenv>=1.0.0` (auto-load `.env`)
- `hatchling` (build backend, for `project.scripts` to register the `astro` CLI)

## Status
- [x] Project structure and dependencies
- [x] DuckDB data layer with introspection
- [x] Gemini agent with tool-calling loop
- [x] CLI entry point with interactive REPL (`astro` / `astro --ask`)
- [x] Data layer smoke tested against warehouse
- [x] Terminal charts via plotext (`create_chart` tool)
- [x] Source citations after answers
- [x] Intermediate result display on stderr
- [ ] End-to-end test with live Gemini API

## What This Does NOT Do (deferred to later phases)
- Semantic layer / metadata sync (Phase 2)
- Evaluation harness (Phase 3)
- Generalization verification (Phase 4)
- Chat UI (stretch)
- Cron sync (stretch)
