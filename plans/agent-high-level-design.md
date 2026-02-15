# Astro: Natural Language Data Warehouse Agent

A CLI agent that answers analytical questions against DuckDB using Gemini function-calling.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Terminal                                                       │
│  $ uv run astro                                                 │
│  astro> "What's our top-selling product?"                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  cli.py                                                          │
│  • Loads .env (walks up 6 dirs to find it)                       │
│  • Auto-detects warehouse/data.duckdb                            │
│  • Runs interactive REPL via prompt_toolkit                      │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  agent.py (Agent class)                                          │
│  • Maintains conversation history (_contents)                    │
│  • Dispatches tool calls to DataLayer                            │
│  • Tracks sources for citation                                   │
│  • Records failed queries for learning                           │
└─────┬────────────────────┬───────────────────────────────────────┘
      │                    │
      ▼                    ▼
┌───────────┐      ┌──────────────┐
│ db.py     │      │ Gemini API   │
│ DataLayer │      │ (external)   │
└───────────┘      └──────────────┘
```

## Module Responsibilities

| File | Purpose |
|------|---------|
| `astro/cli.py` | Entry point. Environment loading, REPL loop |
| `astro/agent.py` | Gemini orchestration, tool dispatch, conversation state |
| `astro/db.py` | DuckDB access via `information_schema` introspection |
| `astro/fmt.py` | ANSI escape codes, prompt styling, answer boxes |
| `astro/display.py` | Intermediate result display (schema/table/query feedback) |

## Available Tools

The agent can call these functions during reasoning:

| Tool | Parameters | Returns |
|------|------------|---------|
| `list_schemas` | none | `["schema1", "schema2"]` |
| `list_tables` | `schema` | `[{name, type, row_count}, ...]` |
| `describe_table` | `schema`, `table` | `[{column, type, nullable}, ...]` |
| `sample_data` | `schema`, `table`, `limit?` | `{columns, rows}` |
| `execute_query` | `sql` | `{columns, rows, row_count}` or `{error}` |

## Hardcoded Values

| What | Value | Location |
|------|-------|----------|
| Model | `gemini-2.5-flash` | `cli.py:113` |
| Max tool-call turns | 25 | `agent.py:38` |
| Max API retries | 3 | `agent.py:39` |
| Query row limit | 100 | `db.py:100` |
| Sample row limit | 10 | `db.py:75` |
| .env search depth | 6 parent dirs | `cli.py:20` |
| DB auto-detect path | `warehouse/data.duckdb` | `cli.py:34` |

## Gemini API Integration

### Authentication
```
cli.py → reads GEMINI_API_KEY or GOOGLE_API_KEY from env
       → passes to Agent.__init__

agent.py → genai.Client(api_key=...)
        → _preflight() runs a minimal "ping" to verify auth
```

### Request Flow
```
Agent.ask(question)
  │
  ├─ Append user message to _contents
  │
  └─ Loop (max 25 turns):
       │
       ├─ _call_model(_contents, _tools)
       │     └─ client.models.generate_content(...)
       │        with _build_system_prompt() + query error history
       │
       ├─ If response has function_calls:
       │     └─ For each call: _execute_tool(name, args)
       │           └─ Route to DataLayer method
       │           └─ Append FunctionResponse to _contents
       │     └─ Continue loop
       │
       └─ If response has text (no function_calls):
             └─ Return answer, exit loop
```

### Error Handling
| Error Type | Behavior |
|------------|----------|
| 401/403/UNAUTHENTICATED | Fail immediately with actionable message |
| 429/rate limit/quota | Exponential backoff (2s, 4s, 8s) |
| DB/SQL error | Caught, recorded in `_query_errors`, returned to model |
| Max turns exceeded | Return timeout message |

## State Management

| State | Scope | Purpose |
|-------|-------|---------|
| `_contents` | Session | Full conversation history (persists across questions) |
| `_query_errors` | Session | Failed SQL + error messages (appended to system prompt) |
| `_current_sources` | Per-question | Tables/queries used (reset each `ask()`) |

## Output Streams

- **stdout**: Final answer box, sources section
- **stderr**: All intermediate feedback (schema info, query progress, errors)

This separation allows piping answers while keeping progress visible.

## Dependencies

```
google-genai>=1.0.0     # Gemini SDK
prompt-toolkit>=3.0.0   # REPL with history
python-dotenv>=1.0.0    # .env auto-loading
duckdb                  # Database (also used by rest of platform)
```
