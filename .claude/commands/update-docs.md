---
description: Incrementally update documentation using parallel background agents that write directly to files, keeping orchestrator context minimal.
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

# Update Documentation Incrementally

You are the incremental doc updater. Instead of regenerating everything, you detect changes and update only affected documentation using parallel background agents.

## Core Principle: Parallel Background Section Updates

The orchestrator NEVER receives section content. Instead:
1. Detect changes since last generation
2. Map changes to affected docs/sections
3. Spawn background agents in parallel (one per section)
4. Background agents write directly to files
5. Orchestrator monitors completion and validates

**Context Budget:** Orchestrator stays under 1,200 lines total

**Note:** Review is now handled by separate `/review-docs` command after updates complete.

## Workflow

### Phase 1: Detect Changes

**Step 1a: Find Last Doc Generation Timestamp**
```bash
# Read timestamp from CHANGELOG
grep "^## Generation:" docs/generated/CHANGELOG.md | head -1
```

Example output:
```
## Generation: 2026-02-05 10:23
```

**If CHANGELOG doesn't exist:**
```
⚠️ Cannot find last doc generation timestamp.

Recommendation: Run /generate-docs first to establish baseline.

Proceed anyway? [Choose date manually / Abort]
```

**Step 1b: Identify Changed Files**
```bash
# Get files changed since last generation
git diff --name-only HEAD@{2026-02-05}

# Or use git log
git log --since="2026-02-05 10:23" --name-only --pretty=format: | sort -u
```

**Step 1c: Count Changes**
```bash
# Count changed files
git diff --name-only HEAD@{2026-02-05} | wc -l
```

**Decision Logic:**
```
If >20 files changed across >3 areas:
  → Recommend /generate-docs (too extensive)
  → Ask user: "Switch to full regeneration? [Y/n]"

If 0 files changed:
  → "No changes detected since last generation"
  → Exit

Else:
  → Proceed with incremental update
```

### Phase 2: Categorize Changes & Map to Docs

**Read changed file list and map to affected docs:**

```json
{
  "changed_files": [
    "engine/orchestration/planner.py",
    "engine/orchestration/registry.py",
    "engine/schema/generators/prisma_generator.py",
    "web/app/search/page.tsx",
    "docs/target/architecture.md"
  ],
  "affected_docs": {
    "ARCHITECTURE.md": {
      "reason": "docs/target/architecture.md changed (GLOBAL CONSTRAINTS source)",
      "action": "regenerate_full",
      "sections": ["all"]
    },
    "BACKEND.md": {
      "reason": "engine/orchestration/* changed",
      "action": "update_sections",
      "sections": ["Orchestration System", "Query Planning"]
    },
    "DATABASE.md": {
      "reason": "engine/schema/generators/prisma_generator.py changed",
      "action": "update_sections",
      "sections": ["Schema Generation", "Prisma Integration"]
    },
    "FRONTEND.md": {
      "reason": "web/app/search/page.tsx changed",
      "action": "update_sections",
      "sections": ["Search Interface"]
    }
  }
}
```

**Change → Doc Mapping Rules:**
```
Changed files → Affected docs:

engine/ingestion/*, engine/extraction/* → BACKEND.md, ARCHITECTURE.md
engine/orchestration/* → BACKEND.md, ARCHITECTURE.md
engine/schema/* → DATABASE.md, ARCHITECTURE.md
engine/lenses/* → ARCHITECTURE.md, BACKEND.md

web/app/*, web/components/* → FRONTEND.md, FEATURES.md
web/lib/* → FRONTEND.md
web/prisma/schema.prisma → DATABASE.md

docs/target/system-vision.md → ARCHITECTURE.md (+ re-extract GLOBAL CONSTRAINTS)
docs/target/architecture.md → ARCHITECTURE.md (+ re-extract GLOBAL CONSTRAINTS)

engine/config/schemas/* → DATABASE.md, BACKEND.md, API.md

tests/* → DEVELOPMENT.md
.github/workflows/* → DEPLOYMENT.md
README.md, CLAUDE.md → ONBOARDING.md
```

**Display Analysis:**
```
📊 Change Analysis

Files changed: 5
Areas affected: backend, database, frontend, architecture

Affected Documentation:
✅ ARCHITECTURE.md - Full regeneration (GLOBAL CONSTRAINTS changed)
✅ BACKEND.md - Update 2 sections
✅ DATABASE.md - Update 2 sections
✅ FRONTEND.md - Update 1 section
⏭️ API.md - No changes
⏭️ FEATURES.md - No changes
⏭️ ONBOARDING.md - No changes
⏭️ DEPLOYMENT.md - No changes
⏭️ DEVELOPMENT.md - No changes
⏭️ CONFIGURATION.md - No changes

Estimated time: ~2 minutes (parallel updates)
```

### Phase 3: Re-extract Global Constraints (If Needed)

**If docs/target/system-vision.md or docs/target/architecture.md changed:**

1. **Read both files**
2. **Re-extract GLOBAL CONSTRAINTS** (max 100 lines)
3. **Write to .claude/tmp/global_constraints.md**
4. **Flag all docs for regeneration** (not just updates)

**Otherwise:**
```bash
# Reuse existing GLOBAL CONSTRAINTS from last generation
cp docs/generated/.global_constraints_cache.md .claude/tmp/global_constraints.md
```

### Phase 4: Spawn Background Update Agents (Parallel)

**For each affected doc, determine update strategy:**

**Strategy 1: Full Doc Regeneration**
- Used when: GLOBAL CONSTRAINTS changed, or structural changes detected
- Process: Same as generate-docs (spawn one agent for entire doc)

**Strategy 2: Section-Level Updates** (most common)
- Used when: Localized changes to specific areas
- Process: Spawn one agent per section that needs updating

#### Strategy 2 Example: Update Specific Sections

**For BACKEND.md → Update 2 sections:**

```python
# Spawn 2 background agents in parallel (one per section)

Task(
  subagent_type="general-purpose",
  description="Update BACKEND.md: Orchestration System",
  prompt=f"""
You are a background agent updating a specific section in BACKEND.md.

## Task
Update section: "## Orchestration System"

## Instructions
1. Read GLOBAL CONSTRAINTS from .claude/tmp/global_constraints.md
2. Read changed source files:
   - engine/orchestration/planner.py
   - engine/orchestration/registry.py
3. Read current section content from docs/generated/BACKEND.md
4. Generate updated section content (≤400 lines) incorporating recent changes
5. Use Edit tool to replace old section with new section
6. Return concise confirmation (see _shared-direct-write-pattern.md)

## Important
- Edit docs/generated/BACKEND.md directly
- Only modify the "Orchestration System" section
- Preserve surrounding sections unchanged
- Keep your final message under 50 lines
  """,
  run_in_background=True
)

Task(
  subagent_type="general-purpose",
  description="Update BACKEND.md: Query Planning",
  prompt=f"""
[Similar prompt for "Query Planning" section]
  """,
  run_in_background=True
)

# Repeat for all sections across all affected docs
```

**Track agents:**
```json
{
  "updates": [
    {
      "doc": "BACKEND.md",
      "section": "Orchestration System",
      "agent_id": "task_20",
      "output_file": "<from_task_result>"
    },
    {
      "doc": "BACKEND.md",
      "section": "Query Planning",
      "agent_id": "task_21",
      "output_file": "<from_task_result_agent_21.log"
    },
    {
      "doc": "DATABASE.md",
      "section": "Schema Generation",
      "agent_id": "task_22",
      "output_file": "<from_task_result_agent_22.log"
    },
    ...
  ]
}
```

### Phase 5: Monitor Progress

**Poll output files periodically (using paths from task results):**

```bash
# Every 15 seconds, check agent progress using captured output_file paths
tail -n 10 <output_file_for_agent_1>  # Look for "✅ Section complete"
tail -n 10 <output_file_for_agent_2>
...
```

**Display progress:**
```
📊 Update Progress (7 agents running in parallel)

ARCHITECTURE.md (full regeneration):
  ⏳ Section 5/12 in progress

BACKEND.md (2 section updates):
  ✅ Orchestration System - Complete
  ⏳ Query Planning - In progress

DATABASE.md (2 section updates):
  ✅ Schema Generation - Complete
  ✅ Prisma Integration - Complete

FRONTEND.md (1 section update):
  ⏳ Search Interface - In progress
```

### Phase 5.5: WAIT for ALL Agents to Complete (CRITICAL SYNCHRONIZATION GATE)

**⚠️ THIS IS CRITICAL - DO NOT SKIP**

**Step 1: Display Waiting Message**

```
⏳ Waiting for all update agents to complete...
Tracking {len(update_agents)} agents

This may take 1-2 minutes. Progress will be shown below.
```

**Step 2: Sequential Completion Waiting**

**CRITICAL:** Use `TaskOutput(block=True)` to wait for EACH agent sequentially:

```python
print("\n⏳ Waiting for all update agents to complete...")
print(f"Tracking {len(update_agents)} agents\n")

for i, agent in enumerate(update_agents):
    print(f"[{i+1}/{len(update_agents)}] Waiting for {agent['doc']} → {agent['section']}...")

    # BLOCKING WAIT - do not proceed until this agent completes
    result = TaskOutput(
        task_id=agent['agent_id'],
        block=True,
        timeout=300000  # 5 minutes max per section
    )

    agent['status'] = 'complete'
    print(f"  ✅ {agent['doc']} → {agent['section']} complete\n")

print("\n✅ All agents complete. Proceeding to validation...\n")
```

**Step 3: Display Live Progress to User**

Example output:

```
⏳ Waiting for all update agents to complete...
Tracking 7 agents

[1/7] Waiting for ARCHITECTURE.md → Full doc...
  ✅ ARCHITECTURE.md → Full doc complete

[2/7] Waiting for BACKEND.md → Orchestration System...
  ✅ BACKEND.md → Orchestration System complete

[3/7] Waiting for BACKEND.md → Query Planning...
  ✅ BACKEND.md → Query Planning complete

[4/7] Waiting for DATABASE.md → Schema Generation...
  ✅ DATABASE.md → Schema Generation complete

[5/7] Waiting for DATABASE.md → Prisma Integration...
  ✅ DATABASE.md → Prisma Integration complete

[6/7] Waiting for FRONTEND.md → Search Interface...
  ✅ FRONTEND.md → Search Interface complete

[7/7] Waiting for FRONTEND.md → Component Library...
  ✅ FRONTEND.md → Component Library complete

✅ All agents complete. Proceeding to validation...
```

**ONLY AFTER THIS PHASE MAY YOU PROCEED TO PHASE 6 (VALIDATION).**

### Phase 6: Validate Updates

**For each updated doc:**

1. **Check file still exists and is valid:**
   ```bash
   ls -lh docs/generated/BACKEND.md
   wc -l docs/generated/BACKEND.md
   ```

2. **Verify sections were actually updated:**
   ```bash
   # Check if section heading exists
   grep "^## Orchestration System" docs/generated/BACKEND.md
   ```

3. **Quick content sanity check:**
   ```bash
   # Check that the section has reasonable content (not just heading)
   awk '/^## Orchestration System/,/^## / {count++} END {print count}' docs/generated/BACKEND.md
   ```

**If validation fails:**
```
⚠️ Section update validation failed: BACKEND.md → Orchestration System
- Section heading found, but content is only 5 lines (expected >50)

Reading agent output...
[tail <output_file_agent_20.log]

Issue: [diagnosis]
Options:
1. Retry this section
2. Skip (keep old content)
3. Abort
```

### Phase 7: Update CHANGELOG

**Append to docs/generated/CHANGELOG.md:**

```markdown
## Update: 2026-02-08 14:55

### Changes Detected
- 5 files changed since last generation (2026-02-05 10:23)
- Changed areas: backend, database, frontend, architecture

### Strategy
- Mode: Parallel background agents (section-level updates)
- Time: 1 minute 15 seconds
- Agents: 7 update agents

### Docs Updated

**ARCHITECTURE.md**
- Action: Full regeneration (GLOBAL CONSTRAINTS changed)
- Lines: 2,567 (was 2,456)

**BACKEND.md**
- Action: Section updates
- Sections: Orchestration System, Query Planning
- Lines: 1,589 (was 1,567)

**DATABASE.md**
- Action: Section updates
- Sections: Schema Generation, Prisma Integration
- Lines: 1,145 (was 1,123)

**FRONTEND.md**
- Action: Section updates
- Sections: Search Interface
- Lines: 1,112 (was 1,098)

### Files Changed
- engine/orchestration/planner.py
- engine/orchestration/registry.py
- engine/schema/generators/prisma_generator.py
- web/app/search/page.tsx
- docs/target/architecture.md

### Context Efficiency
- Orchestrator peak context: ~1,200 lines
- vs. Full regeneration: ~15,000 lines
- Time saved: ~93% vs. full regeneration (1.7min vs. 25min)
```

### Phase 8: Cleanup

**Remove temporary files:**
```bash
rm .claude/tmp/global_constraints.md
# Note: agent log files are system-managed and cleaned automatically
```

### Final Output

```
✅ Documentation Update Complete

Strategy: Parallel background agents (section-level updates)
Time: 1 minute 15 seconds
Agents: 7 update agents

Changes Detected:
- 5 files changed since 2026-02-05 10:23
- Areas: backend, database, frontend, architecture

Docs Updated:
✅ ARCHITECTURE.md - Full regeneration (2,567 lines)
✅ BACKEND.md - 2 sections updated (1,589 lines)
✅ DATABASE.md - 2 sections updated (1,145 lines)
✅ FRONTEND.md - 1 section updated (1,112 lines)

Docs Unchanged:
⏭️ API.md (987 lines)
⏭️ FEATURES.md (1,234 lines)
⏭️ ONBOARDING.md (756 lines)
⏭️ DEPLOYMENT.md (654 lines)
⏭️ DEVELOPMENT.md (892 lines)
⏭️ CONFIGURATION.md (445 lines)

Context Efficiency:
- Orchestrator peak: 1,234 lines
- vs. Full regeneration: ~15,000 lines
- Improvement: 92% reduction
- Time saved: 93% (1.7min vs. 25min)

Next Steps:
- Review updated docs in docs/generated/
- Run /review-docs to review quality (optional)
- Run /generate-docs if changes seem incomplete
- Continue with incremental updates for future changes
```

## Performance Comparison

| Metric | Sequential Update | Parallel Update | Improvement |
|--------|-------------------|-----------------|-------------|
| Time (5 sections) | ~8 minutes | ~2 minutes | 75% faster |
| Orchestrator context | ~3,000 lines | ~1,200 lines | 60% reduction |
| Scalability | Linear with section count | Constant (parallel) | Scales better |

## When to Use Update vs. Generate

**Use /update-docs (this command):**
- 1-20 files changed
- Changes are localized (not architectural)
- Need fast refresh
- Daily/routine updates

**Use /generate-docs:**
- First time generating docs
- >20 files changed
- GLOBAL CONSTRAINTS sources changed significantly
- Major architectural refactoring
- Weekly/milestone comprehensive updates
- When uncertain about change impact

**Decision threshold:**
```
If changed_files > 20 OR architectural_changes:
    recommend /generate-docs
Else:
    proceed with /update-docs
```

## Error Handling

**No changes detected:**
```
ℹ️ No changes detected since last generation (2026-02-05 10:23)

Documentation is up to date.
```

**Changes too extensive:**
```
⚠️ Extensive changes detected (32 files across 6 areas)

Recommendation: Run full doc regeneration for consistency.
Run /generate-docs? [Y/n]
```

**Section not found in existing doc:**
```
⚠️ Section "Query Planning" not found in BACKEND.md

This may indicate structural changes.

Options:
1. Regenerate entire BACKEND.md
2. Add as new section (specify location)
3. Skip this update

Choose [1/2/3]:
```

**Agent failure:**
```
⚠️ Update agent failed: task_22 (DATABASE.md → Schema Generation)

Reading agent output...
[diagnosis from <output_file_agent_22.log]

Options:
1. Retry with adjusted prompt
2. Skip this section (keep old content)
3. Switch to full doc regeneration
```
