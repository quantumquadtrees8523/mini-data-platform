# Future Work

This document outlines directions for continued development of the Mini Data Platform and the Astro CLI agent. It was authored by the user with Claude assistance and is not part of the original repository.

---

## Agent

- **Reasoning with a pro model.** The agent can support deeper reasoning over data by routing complex analytical questions to a more capable model (e.g., Gemini Pro or equivalent) rather than relying solely on Gemini 3.0 Flash by default.
- **Bun/JS-based interface.** The terminal REPL could be replaced or supplemented with a Bun/JavaScript-based interface for a more expressive, interactive user experience.
- **Parallel deep dives.** We should be able to parallelize deep-dive analyses on the data, which will become increasingly important as the sheer volume of data grows.
- **Agent-generated charts.** The agent should be able to generate and showcase charts to drive home data-based ideas and make insights more tangible.
- **Task-specific agents with model selection.** Rather than routing everything through a single model, we should break apart agents to handle more specific tasks using purpose-matched models instead of defaulting to 3.0 Flash for everything.
- **Semantic index for self-reference.** At sufficient scale, the agent should have access to a semantic index that it can use to reference its own prior work — past queries, insights, and analytical artifacts.
- **Publish to PyPI.** We want to push this specific agent library to PyPI so it can be dropped into any DuckDB-based mini data platform as a reusable package.
- **Backend-agnostic interfaces.** The agent should expose interfaces that allow it to interact with more than just DuckDB — supporting other data stores and query engines.

## Data Platform

- **Semantic index over metadata.** With enough data, we want to introduce a semantic index that maps the metadata both explicitly declared and implicitly inferred from the data CSVs. This would enable richer discovery and more intelligent query planning.
- **Broader input sources.** We want to support a broader range of input sources that the DAG (or DAGs) can massage into a series of data stores, including but not limited to DuckDB.
- **More expressive UI layer.** There is value in adding a more expressive UI layer in addition to the Evidence BI user interface — specifically, a chatbot interface that provides more interactive ways to see what is happening under the hood.
- **Scale-aware technology choices.** We acknowledge that the scale of this project is constrained. At massive scale — the kind Astronomer actually deals with — there are additional optimizations and technology choices that become relevant. For example:
  - Intelligent DFS (depth-first search) for an agent to make sense of data using a semantic layer.
  - OLAP engines like BigQuery or Redshift for handling analytical workloads at scale.

## Evals
- A more comprehensive set of evals testing a broader range of edge cases.
- Some agent evaluations are flapping a bit and need to be more thoroughly ironed out.

## References

- [Inside Our In-House Data Agent](https://openai.com/index/inside-our-in-house-data-agent/) — This document was used as a meaningful source of inspiration and reference.
