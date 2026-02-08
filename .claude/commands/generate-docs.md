---
description: Generate the complete /docs suite using parallel background agents that write directly to files, keeping orchestrator context minimal.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Task
  - TaskOutput
  - Bash
---

# Generate Complete Documentation Suite

You are the orchestrator. You MUST use background agents to keep context minimal and enable parallel generation.

## Core Principle: Parallel Background Agents

The orchestrator NEVER receives doc content. Instead:
1. Extract GLOBAL CONSTRAINTS
2. Generate diagrams (parallel agents)
3. **VALIDATE diagrams exist** (validation gate)
4. Generate docs (parallel agents, embed diagrams)
5. Validate results and report summary

**Context Budget:** Orchestrator stays under 2,000 lines total (vs. unbounded in sequential approach)

**⚠️ CRITICAL: You MUST follow all phases in order. DO NOT skip Phase 2 (diagrams) or Phase 2.5 (validation gate). Skipping phases will cause downstream failures.**

## Workflow

### Phase 0: Check Existing Docs & Get User Choice

**Before starting generation:**

1. **Scan docs/generated/ for existing docs**
   ```bash
   ls -la docs/generated/*.md
   ```

2. **Display found docs with details**
   ```
   Found existing documentation:
   ✅ ARCHITECTURE.md (2,917 lines, 89 KB)
   ✅ DATABASE.md (1,234 lines, 45 KB)
   ❌ API.md (not found)
   ...
   ```

3. **Present options to user using AskUserQuestion:**
   ```
   Question: "What should I do with existing documentation?"

   Options:
   - "Skip existing, generate only missing docs" (Recommended)
   - "Regenerate all (fresh start)"
   - "Let me choose specific docs to regenerate"
   ```

4. **Process user choice:**
   - Option 1: Filter doc list to only missing docs
   - Option 2: Delete docs/generated/*.md, proceed with full list
   - Option 3: Present follow-up with checkboxes

### Phase 1: Extract Global Constraints

1. **Read architectural authorities:**
   - docs/target/system-vision.md
   - docs/target/architecture.md

2. **Extract GLOBAL CONSTRAINTS** (max 100 lines):
   - System name, tech stack
   - Key architectural patterns
   - Naming conventions
   - Immutable invariants
   - Engine vs Lens boundaries

3. **Write to shared file** for background agents:
   ```
   Write to: .claude/tmp/global_constraints.md
   ```

### Phase 2: Generate Diagrams (Parallel)

**⚠️ MANDATORY PHASE - DO NOT SKIP**

**Required Diagrams (minimum):**
1. `pipeline.mmd` — 11-stage data flow (Input → Entity Store)
2. `architecture.mmd` — Engine vs Lens layers, component interaction
3. `entity_model.mmd` — Entity schema (classes, dimensions, modules)

**Generate diagrams by writing Mermaid directly** (NO agents needed for simple diagrams):

```bash
# Write each diagram directly to docs/generated/diagrams/
cat > docs/generated/diagrams/pipeline.mmd << 'EOF'
graph TB
    Input[Query] --> Lens[Lens Resolution]
    Lens --> Planning[Planning]
    ...
EOF
```

**OR spawn diagram agents if complex** using `run_in_background=True`:

```python
# Single message with multiple Task calls if diagrams need exploration
Task(subagent="diagram-architecture", run_in_background=True, ...)
Task(subagent="diagram-er", run_in_background=True, ...)
...
```

Each diagram agent:
1. Reads .claude/tmp/global_constraints.md
2. Generates Mermaid diagram
3. Writes to docs/generated/diagrams/diagram_[type].mmd
4. Returns brief confirmation

**Track completion:**
```json
{
  "diagram-architecture": {"agent_id": "task_1", "output_file": "<from_task_result_agent_1.log"},
  "diagram-er": {"agent_id": "task_2", "output_file": "<from_task_result_agent_2.log"},
  ...
}
```

**Monitor completion:**
```bash
# Poll each output file
tail <output_file_from_task_result>  # Check if "✅ Complete" appears
```

**Once all diagrams complete:** Collect diagram file paths for doc agents

### Phase 2.5: VALIDATION GATE - Verify Diagrams Exist

**CRITICAL: This gate MUST pass before proceeding to Phase 3**

```bash
# Verify all required diagrams exist
required_diagrams=(
  "docs/generated/diagrams/pipeline.mmd"
  "docs/generated/diagrams/architecture.mmd"
  "docs/generated/diagrams/entity_model.mmd"
)

for diagram in "${required_diagrams[@]}"; do
  if [[ ! -f "$diagram" ]]; then
    echo "❌ VALIDATION FAILED: Missing diagram: $diagram"
    echo "Cannot proceed to Phase 3 without diagrams"
    exit 1
  fi
done

echo "✅ All required diagrams verified"
```

**If validation fails:**
1. STOP execution immediately
2. Report which diagrams are missing
3. DO NOT proceed to Phase 3
4. Fix Phase 2 diagram generation

**Only proceed to Phase 3 if this validation passes.**

### Phase 3: Generate Docs (Parallel)

**Document List:**
1. ARCHITECTURE.md
2. DATABASE.md
3. API.md
4. FEATURES.md
5. ONBOARDING.md
6. FRONTEND.md
7. BACKEND.md
8. DEPLOYMENT.md
9. DEVELOPMENT.md
10. CONFIGURATION.md

**For each doc in FILTERED list (from Phase 0):**

#### Step 3a: Spawn Background Agent

**Single message with multiple Task calls** (one per doc):

```python
# Parallel doc generation
Task(
  subagent_type="general-purpose",
  description=f"Generate ARCHITECTURE.md",
  prompt=f"""
You are a background agent generating ARCHITECTURE.md.

## Instructions

1. Read GLOBAL CONSTRAINTS from .claude/tmp/global_constraints.md
2. Read required diagrams:
   - docs/generated/diagrams/diagram_architecture.mmd
   - docs/generated/diagrams/diagram_c4.mmd
   - docs/generated/diagrams/diagram_dependency.mmd
   - docs/generated/diagrams/diagram_sequence.mmd

3. Read source files to understand architecture:
   - docs/target/system-vision.md
   - docs/target/architecture.md
   - engine/orchestration/
   - engine/ingestion/
   - engine/extraction/
   - engine/lenses/

4. Generate complete ARCHITECTURE.md following the outline→section-chunks pattern:
   a. Create outline (sections)
   b. Write skeleton to docs/generated/ARCHITECTURE.md
   c. For each section:
      - Generate content (≤400 lines)
      - Edit file to insert content
      - Continue to next section

5. Embed diagrams using: ```mermaid\n[diagram content]\n```

6. Follow GLOBAL CONSTRAINTS for all naming and terminology

7. When complete, return concise confirmation (see _shared-direct-write-pattern.md)

## Important
- Write directly to docs/generated/ARCHITECTURE.md
- DO NOT return content to orchestrator
- Keep your final message under 50 lines
  """,
  run_in_background=True
)

# Repeat for all 10 docs in parallel
Task(subagent="general-purpose", description="Generate DATABASE.md", prompt="...", run_in_background=True)
Task(subagent="general-purpose", description="Generate API.md", prompt="...", run_in_background=True)
...
```

**Track agents (capture output_file from task results):**
```json
{
  "ARCHITECTURE.md": {"agent_id": "task_10", "output_file": "<path_from_task_result>"},
  "DATABASE.md": {"agent_id": "task_11", "output_file": "<path_from_task_result>"},
  ...
}
```

**Note:** The `output_file` paths are returned by the Task tool and may vary by system.

#### Step 3b: Monitor Progress

**Poll output files periodically using paths from task results:**

```bash
# Every 30 seconds, check all agent output files using captured paths
tail -n 20 <output_file_for_architecture>  # Look for "✅ Section complete" or "✅ Complete"
tail -n 20 <output_file_for_database>
...
```

**Display progress to user:**
```
📊 Doc Generation Progress (10 agents running in parallel)

✅ ARCHITECTURE.md - Complete (2,456 lines)
✅ DATABASE.md - Complete (1,123 lines)
⏳ API.md - Section 4/7 in progress
⏳ FEATURES.md - Section 2/5 in progress
⏳ ONBOARDING.md - Generating outline
⏳ FRONTEND.md - Section 1/6 in progress
⏳ BACKEND.md - Section 3/8 in progress
⏳ DEPLOYMENT.md - Section 2/4 in progress
⏳ DEVELOPMENT.md - Generating outline
⏳ CONFIGURATION.md - Section 1/3 in progress
```

#### Step 3c: Wait for All Agents to Complete

Use `TaskOutput` with `block=true` to wait for completion:

```python
for agent_id in agent_ids:
    TaskOutput(task_id=agent_id, block=true, timeout=600000)  # 10min max
```

### Phase 4: Validate Generated Files

**For each doc:**

1. **Check file exists:**
   ```bash
   ls -lh docs/generated/ARCHITECTURE.md
   ```

2. **Verify content (lightweight check):**
   ```bash
   wc -l docs/generated/ARCHITECTURE.md  # Line count
   grep "^#" docs/generated/ARCHITECTURE.md | head -20  # Section headings
   ```

3. **Track validation results:**
   ```json
   {
     "ARCHITECTURE.md": {"exists": true, "lines": 2456, "sections": 12},
     "DATABASE.md": {"exists": true, "lines": 1123, "sections": 8},
     ...
   }
   ```

**If file missing or suspiciously small:**
```
⚠️ DATABASE.md validation failed (only 23 lines)
Reading agent output to diagnose...
[tail <output_file_agent_11.log]

Issue: [describe problem]
Options:
1. Retry this doc
2. Continue with other docs
3. Abort
```

### Phase 5: Review & Fix (Parallel)

**Spawn review agents in parallel:**

```python
# One review agent per doc
Task(
  subagent_type="review-docs",
  description="Review ARCHITECTURE.md",
  prompt=f"""
Review docs/generated/ARCHITECTURE.md

Check for:
- Compliance with GLOBAL CONSTRAINTS (.claude/tmp/global_constraints.md)
- Cross-reference correctness
- Consistency with other docs (read all docs/generated/*.md)
- Diagram embedding correctness

Return patch instructions if issues found, or confirm "✅ No issues" if clean.

Keep response under 100 lines.
  """,
  run_in_background=True
)

# Repeat for all docs
...
```

**Wait for reviews to complete:**
```python
for review_agent_id in review_agent_ids:
    result = TaskOutput(task_id=review_agent_id, block=true)
    # Check if patches needed
```

**Apply patches sequentially** (if needed):
- Read review agent output
- Parse patch instructions
- Use Edit tool to apply patches

### Phase 6: Generate Navigation Docs

**Generate README.md and CHANGELOG.md** (orchestrator does this directly):

1. **README.md:**
   ```markdown
   # Generated Documentation Suite

   Generated on: [timestamp]

   ## Documents
   - [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture (2,456 lines)
   - [DATABASE.md](DATABASE.md) - Database schema (1,123 lines)
   ...

   ## Generation Stats
   - Total lines: 12,345
   - Docs generated: 10
   - Diagrams embedded: 15
   - Generation time: 3.5 minutes (parallel)
   - Agents used: 25 (10 doc + 11 diagram + 4 review)
   ```

2. **CHANGELOG.md:**
   ```markdown
   # Documentation Generation Changelog

   ## Generation: 2026-02-08 14:32

   ### Strategy
   - Mode: Parallel background agents
   - Docs generated: 10
   - Time: 3.5 minutes

   ### Agent Details
   - Diagram agents: 11 (parallel)
   - Doc agents: 10 (parallel)
   - Review agents: 10 (parallel)

   ### Files Created
   - docs/generated/ARCHITECTURE.md (2,456 lines)
   - docs/generated/DATABASE.md (1,123 lines)
   ...

   ### Review Summary
   - Blocking issues: 0
   - Important issues: 3 (applied automatically)
   - Minor issues: 7 (applied automatically)

   ### Context Efficiency
   - Orchestrator peak context: ~1,800 lines
   - vs. Sequential approach: ~15,000 lines
   - Reduction: 88%
   ```

### Phase 7: Cleanup

**Remove temporary files:**
```bash
rm .claude/tmp/global_constraints.md
rm docs/generated/diagrams/diagram_*.mmd
# Note: agent log files are system-managed and cleaned automatically
```

### Final Output

```
✅ Documentation Generation Complete

Strategy: Parallel background agents
Time: 3 minutes 42 seconds
Agents: 31 total (11 diagram + 10 doc + 10 review)

Files Generated:
✅ docs/generated/ARCHITECTURE.md (2,456 lines, 78 KB)
✅ docs/generated/DATABASE.md (1,123 lines, 42 KB)
✅ docs/generated/API.md (987 lines, 35 KB)
✅ docs/generated/FEATURES.md (1,234 lines, 45 KB)
✅ docs/generated/ONBOARDING.md (756 lines, 28 KB)
✅ docs/generated/FRONTEND.md (1,098 lines, 39 KB)
✅ docs/generated/BACKEND.md (1,567 lines, 52 KB)
✅ docs/generated/DEPLOYMENT.md (654 lines, 24 KB)
✅ docs/generated/DEVELOPMENT.md (892 lines, 31 KB)
✅ docs/generated/CONFIGURATION.md (445 lines, 16 KB)
✅ docs/generated/README.md (navigation)
✅ docs/generated/CHANGELOG.md (generation log)

Total: 11,212 lines across 12 files

Quality:
- Cross-references validated: ✅
- Diagrams embedded: 15 total
- GLOBAL CONSTRAINTS compliance: ✅
- Review issues: 0 blocking, 3 important (fixed), 7 minor (fixed)

Context Efficiency:
- Orchestrator peak: 1,823 lines
- vs. Sequential: ~15,000 lines
- Improvement: 88% reduction

Next Steps:
- Review generated docs in docs/generated/
- Move to docs/ root when approved
- Run /update-docs for incremental changes
```

## Agent Mapping

**Doc Agents (background):**
- Each doc gets its own general-purpose agent
- Agent reads sources, generates content, writes directly to file
- Returns brief (<50 line) confirmation

**Diagram Agents (background):**
- diagram-architecture
- diagram-c4
- diagram-component
- diagram-contribution-flow
- diagram-dependency
- diagram-deployment
- diagram-er
- diagram-network
- diagram-sequence
- diagram-state
- diagram-user-journey

**Review Agents (background):**
- review-docs (one instance per doc)

## Error Handling

**If agent fails:**
1. Read agent output file: `Read(<output_file_agent_X.log)`
2. Diagnose issue from agent's messages
3. Options:
   - Retry with clearer prompt
   - Skip this doc (continue with others)
   - Abort entire generation

**If agent timeout (>10 min):**
```
⚠️ Agent task_15 (BACKEND.md) timed out after 10 minutes

Options:
1. Extend timeout and continue waiting
2. Terminate and retry with simpler sections
3. Skip this doc
```

**If validation fails:**
```
⚠️ FEATURES.md validation failed
- Expected >500 lines, got 87 lines
- Missing sections: User Journeys, Integration Examples

Reading agent output...
[diagnosis]

Options:
1. Retry generation
2. Manual inspection needed
3. Continue with other docs
```

## Performance Comparison

| Metric | Sequential (v3) | Parallel (v4) | Improvement |
|--------|----------------|---------------|-------------|
| Time | ~25 minutes | ~4 minutes | 84% faster |
| Orchestrator context | ~15,000 lines peak | ~2,000 lines peak | 87% reduction |
| Scalability | Limited by sequential processing | Limited by agent count | Scales horizontally |
| Failure isolation | One failure blocks all | Independent failures | Better resilience |

## When to Use Sequential vs. Parallel

**Use Parallel (v4 - this version):**
- Default for all doc generation
- When you have >3 docs to generate
- When speed matters
- When context window is limited

**Use Sequential (v3):**
- Debugging a specific doc (easier to trace)
- Very small projects (1-2 docs)
- When you need step-by-step control

**Rule of thumb:** Always prefer parallel unless you have a specific reason not to.
