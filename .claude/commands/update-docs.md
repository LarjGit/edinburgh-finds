---
description: Incrementally update documentation based on codebase changes since last doc generation. Only regenerates affected sections/docs.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash
---

# Update Documentation Incrementally

You are the incremental doc updater. Instead of regenerating everything, you detect changes and update only affected documentation.

## Core Principle

Analyze what changed in the codebase since the last doc generation, map those changes to affected docs, and regenerate only the necessary sections using the same outline→section-chunks pattern.

## Workflow

### Phase 1: Detect Changes

**Step 1a: Find Last Doc Generation Timestamp**
1. Read `docs/generated/CHANGELOG.md` to find last generation timestamp
2. If CHANGELOG doesn't exist, fall back to full generation (recommend using `/generate-docs` instead)

**Step 1b: Identify Changed Files**
Use one of these methods:
- If timestamp available: `git diff --name-only HEAD@{YYYY-MM-DD}`
- Alternative: `git log --since="YYYY-MM-DD" --name-only --pretty=format: | sort -u`
- Fallback: Check file modification times in key directories

**Step 1c: Categorize Changes**
Map changed files to doc categories:

```
Changed files → Affected docs mapping:

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

New features (infer from commit messages) → FEATURES.md
```

### Phase 2: Re-extract Global Constraints (If Needed)

If `docs/target/system-vision.md` or `docs/target/architecture.md` changed:
1. Re-read both files
2. Re-extract GLOBAL CONSTRAINTS (max 100 lines)
3. Use these updated constraints for all doc updates

Otherwise, read existing GLOBAL CONSTRAINTS from last generation.

### Phase 3: Identify Affected Sections

For each affected doc, determine which sections need updating:

**Heuristics:**
- If schema files changed → Update relevant table/model sections in DATABASE.md
- If new endpoints added → Update endpoint sections in API.md
- If new components added → Update component sections in FRONTEND.md
- If architectural changes → May need full doc regeneration

**Decision Logic:**
- **Minor changes** (few files, localized): Update specific sections
- **Major changes** (cross-cutting, architectural): Regenerate entire doc
- **Uncertainty**: Default to regenerating entire doc (safer)

### Phase 4: Update Affected Docs

For each affected doc:

**If regenerating entire doc:**
1. Call doc subagent with `task: "outline"`
2. Receive new outline
3. Compare with existing doc sections
4. Regenerate changed sections only (or all if structure changed significantly)

**If updating specific sections:**
1. Read existing doc
2. Identify section to update (e.g., "## Core Tables")
3. Call doc subagent with `task: "section: [section heading]"`
4. Replace old section content with new content using Edit tool

**Section Update Process:**
```
For section "Core Tables" in DATABASE.md:
1. Read docs/generated/DATABASE.md
2. Extract current "## Core Tables" section
3. Call database-docs with:
   - GLOBAL CONSTRAINTS
   - Required diagrams (may reuse existing if not changed)
   - Current doc skeleton
   - task: "section: Core Tables"
4. Receive new section content (≤400 lines)
5. Edit doc to replace old section with new section
```

### Phase 5: Update Diagrams (If Needed)

**Diagram Update Logic:**
- If architectural changes detected → Regenerate architecture diagrams
- If schema changes detected → Regenerate ERD
- If new user journeys mentioned in commits → Regenerate user journey diagram
- Otherwise → Reuse existing diagrams (faster)

To regenerate a diagram:
1. Call appropriate diagram subagent (e.g., diagram-er for ERD)
2. Receive updated Mermaid code (≤150 lines)
3. Update diagram references in affected docs

### Phase 6: Review Updated Docs

For each updated doc:
1. Call review-docs subagent with:
   - The updated doc file path
   - GLOBAL CONSTRAINTS
   - All other docs (for cross-reference checking)
2. Receive patch instructions (if any issues found)
3. Apply patches using Edit tool

### Phase 7: Update CHANGELOG

Append to `docs/generated/CHANGELOG.md`:

```markdown
## Update: YYYY-MM-DD HH:MM

### Changes Detected
- X files changed since last generation (YYYY-MM-DD)
- Changed areas: [list categories]

### Docs Updated
- BACKEND.md: Updated sections [list sections]
- DATABASE.md: Regenerated due to schema changes
- FRONTEND.md: Added new component documentation

### Files Changed
[List of changed files from git diff]

### Review Issues
- X blocking, Y important, Z minor
- [Summary of issues and resolutions]

### Context Budget
- Peak context usage: XXX lines
- Sections updated: X
- Time saved vs. full regeneration: ~XX%
```

## Smart Update Strategies

### Strategy 1: Section-Level Updates (Fastest)
**Use when:** Small, localized changes (1-3 files in same area)
**Process:** Update only affected sections
**Context usage:** ~400 lines per section

### Strategy 2: Doc-Level Updates (Moderate)
**Use when:** Multiple changes across a doc, but other docs unaffected
**Process:** Regenerate entire affected doc(s)
**Context usage:** ~550 lines peak per doc

### Strategy 3: Full Regeneration (Thorough)
**Use when:**
- Major architectural changes
- Changes to GLOBAL CONSTRAINTS sources
- >10 files changed across multiple areas
- Uncertain about change impact
**Process:** Recommend using `/generate-docs` instead
**Note:** This command will inform user and offer to switch to full regeneration

## Error Handling

**If unable to determine last generation date:**
```
⚠️ Cannot find last doc generation timestamp.
Options:
1. Run full generation: /generate-docs
2. Specify date manually: [prompt user for date]
3. Update all docs regardless of changes
```

**If changes are too extensive:**
```
⚠️ Detected extensive changes (X files across Y areas)
Recommendation: Run full doc regeneration for consistency
Run /generate-docs? [Y/n]
```

**If section not found in existing doc:**
```
⚠️ Section "[heading]" not found in existing doc
This may indicate structural changes. Options:
1. Regenerate entire doc
2. Add as new section
3. Skip this update
```

## Output Format

```
🔄 Documentation Update

Changes Detected:
- 8 files changed since 2026-02-01
- Affected areas: backend, database, frontend

Analysis:
✅ BACKEND.md: Update 2 sections (Module Structure, Business Logic)
✅ DATABASE.md: Regenerate entire doc (schema changes)
✅ FRONTEND.md: Update 1 section (Component Architecture)
⏭️ ARCHITECTURE.md: No changes needed
⏭️ API.md: No changes needed
⏭️ [other docs]: No changes needed

Updating...
[Progress indicators as each section/doc updates]

✅ Update Complete

Updated:
- docs/generated/BACKEND.md (2 sections, 800 lines total)
- docs/generated/DATABASE.md (regenerated, 450 lines)
- docs/generated/FRONTEND.md (1 section, 600 lines total)
- docs/generated/CHANGELOG.md (update log appended)

Context used: Peak 550 lines (vs. 5,500 for full regeneration)
Time saved: ~85% vs. full regeneration

Review: 0 blocking, 2 minor issues (applied automatically)

Next steps:
- Review updated docs in docs/generated/
- Run full regeneration if updates seem incomplete
```

## Command Usage

```bash
# From Claude Code CLI
claude update-docs

# Or as skill
/update-docs

# With date override
/update-docs --since=2026-01-15

# Force full regeneration of specific doc
/update-docs --doc=DATABASE.md --full
```

## Comparison: update-docs vs. generate-docs

| Aspect | update-docs | generate-docs |
|--------|-------------|---------------|
| Speed | Fast (seconds-minutes) | Thorough (minutes-hours) |
| Context | ~550 lines peak | ~550 lines peak (per doc) |
| Use case | Incremental changes | First time or major changes |
| Safety | May miss cross-cutting issues | Comprehensive |
| When to use | Daily updates, small changes | Weekly/major milestones |

**Rule of thumb:** Use `update-docs` for routine changes, `generate-docs` for major milestones or when uncertain about change impact.
