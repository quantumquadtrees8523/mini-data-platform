"""Gemini-powered agent that answers questions by exploring and querying a DuckDB warehouse."""

import json
import sys
import time

from google import genai
from google.genai import types

from astro.db import DataLayer
from astro import fmt
from astro import display

SYSTEM_PROMPT = """\
You are a data analyst agent with access to a DuckDB data warehouse.
Your job is to answer user questions by exploring the schema and running SQL queries.

## Workflow
1. List available schemas to understand the database structure.
2. List tables in the most relevant schema(s).
3. Describe table columns to understand the data model.
4. Optionally sample a few rows to see real values.
5. Write and execute SQL to answer the question.
6. If the result contains numerical data suitable for visualization, create a chart.
7. Return a clear, concise natural-language answer with key numbers.

## Rules
- Always explore the schema first. Never assume table or column names.
- Use PostgreSQL syntax.
- If a query errors, read the message, adjust, and retry.
- Format numbers for readability (commas, 2 decimal places for money).
- If the data cannot answer the question, say so clearly.
- When query results have a clear categorical dimension and a numerical measure \
(e.g. revenue by region, counts by status), call create_chart to visualize them.
"""

MAX_TURNS = 25
MAX_RETRIES = 3

TOOL_DECLARATIONS = [
    {
        "name": "list_schemas",
        "description": "List all available schemas in the database.",
    },
    {
        "name": "list_tables",
        "description": "List all tables and views in a schema, including row counts.",
        "parameters": {
            "type": "object",
            "properties": {
                "schema": {
                    "type": "string",
                    "description": "Schema name to list tables from.",
                },
            },
            "required": ["schema"],
        },
    },
    {
        "name": "describe_table",
        "description": "Get column names, data types, and nullability for a table.",
        "parameters": {
            "type": "object",
            "properties": {
                "schema": {"type": "string", "description": "Schema name."},
                "table": {"type": "string", "description": "Table name."},
            },
            "required": ["schema", "table"],
        },
    },
    {
        "name": "sample_data",
        "description": "Get sample rows from a table to understand the actual data values and format.",
        "parameters": {
            "type": "object",
            "properties": {
                "schema": {"type": "string", "description": "Schema name."},
                "table": {"type": "string", "description": "Table name."},
                "limit": {
                    "type": "integer",
                    "description": "Number of sample rows (max 10, default 5).",
                },
            },
            "required": ["schema", "table"],
        },
    },
    {
        "name": "execute_query",
        "description": "Execute a read-only SQL query against DuckDB. Results capped at 100 rows.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL query to execute (DuckDB syntax).",
                },
            },
            "required": ["sql"],
        },
    },
    {
        "name": "create_chart",
        "description": (
            "Create a terminal chart to visualize query results. "
            "Call this after executing a query that returns data suitable for plotting."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "scatter", "histogram"],
                    "description": "Type of chart.",
                },
                "x_data": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "X-axis values (labels or numbers).",
                },
                "y_data": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Y-axis numerical values.",
                },
                "x_label": {"type": "string", "description": "X-axis label."},
                "y_label": {"type": "string", "description": "Y-axis label."},
                "title": {"type": "string", "description": "Chart title."},
            },
            "required": ["chart_type", "y_data"],
        },
    },
]


class Agent:
    def __init__(
        self,
        data_layer: DataLayer,
        api_key: str,
        model: str = "gemini-2.0-flash",
        project: str | None = None,
        location: str | None = None,
    ):
        self.dl = data_layer
        if project:
            _log(fmt.step("~", f"Using Vertex AI backend (project={project}, location={location or 'us-central1'})"))
            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=location or "us-central1",
                api_key=api_key,
            )
        else:
            self.client = genai.Client(api_key=api_key)
        self.model = model
        self._query_errors: list[dict[str, str]] = []
        self._contents: list[types.Content] = []
        self._tools = [types.Tool(function_declarations=TOOL_DECLARATIONS)]
        self._current_sources: list[dict] = []
        self._preflight()

    def _preflight(self):
        """Quick auth check before starting the agent loop."""
        try:
            self.client.models.generate_content(
                model=self.model,
                contents="ping",
                config=types.GenerateContentConfig(max_output_tokens=1),
            )
        except Exception as e:
            err = str(e)
            if "401" in err or "UNAUTHENTICATED" in err or "CREDENTIALS_MISSING" in err:
                raise RuntimeError(
                    "Authentication failed.\n"
                    "  1. Get a key from https://aistudio.google.com/apikey\n"
                    "  2. export GEMINI_API_KEY=<your-key>\n"
                    "  3. Make sure you're NOT using a Google Cloud Console key."
                ) from e
            raise

    def ask(self, question: str) -> str:
        """Append a user question and run the tool-calling loop until an answer."""
        self._current_sources = []

        self._contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=question)],
            )
        )

        for turn in range(MAX_TURNS):
            response = self._call_model(self._contents, self._tools)
            candidate = response.candidates[0]

            function_calls = [
                p for p in candidate.content.parts if p.function_call is not None
            ]

            if not function_calls:
                # Persist the model's final text reply in history
                self._contents.append(candidate.content)
                text_parts = [p.text for p in candidate.content.parts if p.text]
                return "\n".join(text_parts) if text_parts else "(No response from model)"

            # Append model's response (with function calls) to conversation
            self._contents.append(candidate.content)

            # Execute each function call and collect responses
            response_parts = []
            for fc_part in function_calls:
                fc = fc_part.function_call
                args = dict(fc.args) if fc.args else {}
                result = self._execute_tool(fc.name, args)
                response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result},
                        )
                    )
                )

            self._contents.append(types.Content(parts=response_parts))

        return "(Agent reached maximum turns without a final answer. Try a more specific question.)"

    def get_sources(self) -> list[dict]:
        """Return sources collected during the last ask() call."""
        return self._current_sources

    def _record_query_error(self, sql: str, error: str):
        """Store a failed query so the model can learn from past mistakes."""
        self._query_errors.append({"sql": sql, "error": error})
        _log(fmt.warning(f"Query error recorded ({len(self._query_errors)} total)"))

    def _build_system_prompt(self) -> str:
        """Build system prompt, appending any accumulated query errors."""
        if not self._query_errors:
            return SYSTEM_PROMPT
        lines = [SYSTEM_PROMPT, "\n## Previous Query Errors (avoid repeating these mistakes)"]
        for i, entry in enumerate(self._query_errors, 1):
            lines.append(f"\n### Error {i}")
            lines.append(f"SQL: {entry['sql']}")
            lines.append(f"Error: {entry['error']}")
        return "\n".join(lines)

    def _call_model(self, contents, tools):
        """Call Gemini with exponential-backoff retry for rate limits and timeouts."""
        for attempt in range(MAX_RETRIES):
            try:
                return self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        tools=tools,
                        system_instruction=self._build_system_prompt(),
                        temperature=0.1,
                    ),
                )
            except Exception as e:
                err = str(e).lower()
                # Fail fast on auth errors — no point retrying
                if "401" in err or "403" in err or "unauthenticated" in err or "permission" in err:
                    if "api key" in err:
                        raise RuntimeError(
                            "Authentication failed. Make sure you're using a Gemini API key "
                            "from https://aistudio.google.com/apikey (not a Google Cloud key)."
                        ) from e
                    raise
                retryable = (
                    "rate limit" in err
                    or "resource_exhausted" in err
                    or "429" in err
                    or "quota" in err
                    or "timeout" in err
                    or "deadline" in err
                    or "503" in err
                    or "unavailable" in err
                )
                if retryable and attempt < MAX_RETRIES - 1:
                    wait = 2 ** (attempt + 1)
                    _log(fmt.warning(f"Retryable error ({type(e).__name__}). Waiting {wait}s..."))
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError("Max retries exceeded for Gemini API call")

    def _execute_tool(self, name: str, args: dict):
        """Dispatch a tool call to the data layer and display results."""
        _print_step(name, args)

        try:
            match name:
                case "list_schemas":
                    result = self.dl.list_schemas()
                    display.show_schemas(result)
                    return result

                case "list_tables":
                    result = self.dl.list_tables(args["schema"])
                    display.show_tables(result, args["schema"])
                    self._current_sources.append({
                        "type": "table_discovery",
                        "table": f"{args['schema']}.*",
                    })
                    return result

                case "describe_table":
                    result = self.dl.describe_table(args["schema"], args["table"])
                    display.show_columns(result, args["schema"], args["table"])
                    self._current_sources.append({
                        "type": "schema_inspection",
                        "table": f"{args['schema']}.{args['table']}",
                    })
                    return result

                case "sample_data":
                    result = self.dl.sample_data(
                        args["schema"], args["table"], args.get("limit", 5)
                    )
                    display.show_data(result.get("columns", []), result.get("rows", []))
                    self._current_sources.append({
                        "type": "data_sample",
                        "table": f"{args['schema']}.{args['table']}",
                    })
                    return result

                case "execute_query":
                    result = self.dl.execute_query(args["sql"])
                    if isinstance(result, dict) and "error" in result:
                        self._record_query_error(args["sql"], result["error"])
                    else:
                        display.show_query_result(result)
                        self._current_sources.append({
                            "type": "query",
                            "sql": args["sql"],
                            "row_count": result.get("row_count", 0),
                        })
                    return result

                case "create_chart":
                    # Chart acknowledged but not rendered during intermediate steps
                    return {"success": True, "message": "Chart acknowledged."}

                case _:
                    return {"error": f"Unknown tool: {name}"}
        except Exception as e:
            _log(fmt.error(str(e)))
            if name == "execute_query":
                self._record_query_error(args.get("sql", ""), str(e))
            return {"error": str(e)}


def _log(msg: str):
    print(msg, file=sys.stderr)


def _print_step(tool_name: str, args: dict):
    """Print agent steps to stderr so the user can follow along."""
    # Only show SQL execution; other steps use brief summaries from display.py
    if tool_name == "execute_query":
        _log(fmt.step_sql(args.get("sql", "")))
