---
name: generate-system-manual
description: Generates or updates the 'docs/SYSTEM_DESIGN_MANUAL.md' file. It performs an exhaustive analysis of the entire repository (Engine, Web, Tests, Docs) to generate a "System Bible."
---

<objective>
To generate the authoritative "System Bible" for Edinburgh Finds by analyzing every major subsystem: Data Engine, Frontend, DevOps, and Testing.
</objective>

<process>
<step_1>
<instruction>Analyze Core Engine Logic.</instruction>
<command>
read_file engine/config/extraction.yaml
read_file engine/config/canonical_categories.yaml
read_file engine/config/monitoring_alerts.yaml
read_file engine/extraction/deduplication.py
read_file engine/extraction/llm_cache.py
read_file engine/extraction/quarantine.py
read_file engine/extraction/cost_report.py
read_file engine/ingestion/retry_logic.py
read_file engine/ingestion/rate_limiting.py
</command>
</step_1>

<step_2>
<instruction>Analyze CLI Tools.</instruction>
<command>
read_file engine/ingestion/cli.py
read_file engine/extraction/cli.py
read_file engine/schema/cli.py
</command>
</step_2>

<step_3>
<instruction>Analyze Frontend & Testing.</instruction>
<command>
read_file web/package.json
read_file web/README.md
read_file conftest.py
list_directory docs
</command>
</step_3>

<step_4>
<instruction>Read the manual template.</instruction>
<command>read_file .claude/skills/generate-system-manual/templates/manual_template.md</command>
</step_4>

<step_5>
<instruction>Generate the content.</instruction>
<details>
Construct the final `docs/SYSTEM_DESIGN_MANUAL.md`.

**Replacements:**

1.  `{{TAXONOMY_LOGIC_SUMMARY}}`: Summarize `canonical_categories.yaml` (promotion config, regex rules).
2.  `{{TAXONOMY_HIERARCHY}}`: Textual tree from `canonical_categories.yaml`.
3.  `{{DEDUPLICATION_LOGIC}}`: Explain `deduplication.py` logic.
4.  `{{CACHE_LOGIC_SUMMARY}}`: Explain `llm_cache.py`.
5.  `{{RETRY_LOGIC_SUMMARY}}`: Explain `retry_logic.py` (backoff strategy).
6.  `{{RATE_LIMITING_SUMMARY}}`: Explain `rate_limiting.py` (token bucket/window?).
7.  `{{QUARANTINE_LOGIC}}`: Explain `quarantine.py`.
8.  `{{COST_LOGIC}}`: Explain `cost_report.py`.
9.  `{{FRONTEND_STACK_SUMMARY}}`: Summarize dependencies from `web/package.json` and arch from `web/README.md`.
10. `{{TESTING_STRATEGY_SUMMARY}}`: Summarize `conftest.py` and general test approach (pytest).
11. `{{INGESTION_CLI_COMMANDS}}`: List commands from `engine/ingestion/cli.py`.
12. `{{EXTRACTION_CLI_COMMANDS}}`: List commands from `engine/extraction/cli.py`.
13. `{{SCHEMA_CLI_COMMANDS}}`: List commands from `engine/schema/cli.py`.
14. `{{CRITICAL_ALERTS_TABLE}}`: Table from `monitoring_alerts.yaml`.
15. `{{PERFORMANCE_TARGETS_SUMMARY}}`: Summary from `monitoring_alerts.yaml`.
16. `{{TRUST_LEVELS_TABLE}}`: Table from `extraction.yaml`.
17. `{{DOCS_INDEX_TABLE}}`: Create a table listing files in `docs/` with brief inferred descriptions.
</details>
</step_5>

<step_6>
<instruction>Write the file.</instruction>
<command>write_file docs/SYSTEM_DESIGN_MANUAL.md ...</command>
</step_6>
</process>

<success_criteria>
The file `docs/SYSTEM_DESIGN_MANUAL.md` exists and covers:
1.  Engine Logic (Taxonomy, Dedup, Cache, Resilience).
2.  Frontend Architecture.
3.  Testing & QA.
4.  CLI Reference.
5.  Documentation Index.
</success_criteria>