---
description: Generate the complete /docs suite by orchestrating doc agents and diagram agents using the outline→section-chunks pattern to keep orchestrator context lean.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
---

# Generate Complete Documentation Suite (Orchestrator v3 - Section-Chunked)

You are the orchestrator. You MUST follow the section-chunked pattern to keep context lean.

## 🚨 CRITICAL RULES 🚨

1. **NO INTERMEDIATE FILES** - Never create temp files like "doc_sections_X.md"
2. **NO BATCH GENERATION** - Generate ONE section at a time, not "sections 2-16"
3. **IMMEDIATE INSERTION** - Edit the target file immediately after generating each section
4. **NO USER PROMPTS** - Don't ask "should I append?" - just do it
5. **ONE FILE ONLY** - Only docs/generated/[DOCNAME].md should exist when done

## Core Principle: Outline→Section-Chunks Pattern

Doc subagents NEVER return full documents. Instead:
1. First call: Return outline (≤50 lines)
2. Subsequent calls: Return ONE section at a time (≤400 lines each)
3. Orchestrator immediately inserts each section into target file

This keeps orchestrator context bounded regardless of doc size.

**Workflow Summary:**
```
Outline → Skeleton → [For each section: Generate → Edit → Next] → Review → Done
                      ↑                                         ↑
                      NO intermediate files!                   Direct Edit only!
```

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
   ❌ FEATURES.md (not found)
   ...
   ```

3. **Present options to user using AskUserQuestion:**
   ```
   Question: "What should I do with existing documentation?"

   Options:
   - "Skip existing, continue from first missing" (Recommended)
     → Keeps ARCHITECTURE.md, DATABASE.md
     → Starts with API.md

   - "Regenerate all (fresh start)"
     → Deletes all existing docs
     → Generates complete suite from scratch

   - "Let me choose specific docs to regenerate"
     → Shows checklist of all 10 docs
     → User selects which to regenerate
   ```

4. **Process user choice:**
   - **Option 1 (Skip existing):** Filter doc list to only missing docs
   - **Option 2 (Regenerate all):** Delete docs/generated/*.md, proceed with full list
   - **Option 3 (Choose specific):** Present follow-up question with checkboxes for all 10 docs

5. **Proceed with filtered document list**

### Phase 1: Extract Global Constraints

1. Read docs/target/system-vision.md and docs/target/architecture.md
2. Extract into GLOBAL CONSTRAINTS (max 100 lines):
   - System name, tech stack, key patterns
   - Naming conventions, terminology
   - Cross-cutting concerns (auth, logging, etc.)
   - Immutable invariants
   - Engine vs Lens boundaries

### Phase 2: Generate Diagrams

For each diagram type needed:
1. Call diagram subagent with GLOBAL CONSTRAINTS
2. Receive Mermaid code (max 150 lines)
3. Store diagram text for later inclusion in docs

Diagram types:
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

### Phase 3: Generate Docs (Section-by-Section)

**For each doc in the FILTERED list (from Phase 0):**

NOTE: Only process docs that need generation based on user choice in Phase 0.

**Document Order:**
1. ARCHITECTURE.md (needs: diagram-architecture, diagram-c4, diagram-dependency, diagram-sequence)
2. DATABASE.md (needs: diagram-er)
3. API.md (needs: diagram-sequence)
4. FEATURES.md (needs: diagram-user-journey, diagram-sequence)
5. ONBOARDING.md (needs: none)
6. FRONTEND.md (needs: diagram-component, diagram-state)
7. BACKEND.md (needs: diagram-component, diagram-sequence)
8. DEPLOYMENT.md (needs: diagram-deployment, diagram-network)
9. DEVELOPMENT.md (needs: diagram-contribution-flow)
10. CONFIGURATION.md (needs: none)

**For each document:**

**Step 3a: Get Outline**
1. Call doc subagent with:
   - GLOBAL CONSTRAINTS
   - Required diagrams for this doc
   - Instruction: `task: "outline"`
2. Receive outline (max 50 lines) with format:
   ```markdown
   # [Document Title]

   ## Section: [Heading 1]
   Description: [One-line description]
   Estimated lines: [number]

   ## Section: [Heading 2]
   Description: [One-line description]
   Estimated lines: [number]
   ```

**Step 3b: Create Skeleton**
1. Parse outline to extract section headings
2. Write skeleton file to docs/generated/[FILENAME] with:
   - Document title
   - Section headings from outline
   - Placeholder comment: `<!-- SECTION PENDING: [heading] -->`

**Step 3c: Fill Sections (ONE AT A TIME - NO BATCH GENERATION)**

⚠️ **CRITICAL: Process sections individually, not in batches!**

For each section in outline (process sequentially, one by one):

1. **Call subagent for THIS SECTION ONLY**
   - GLOBAL CONSTRAINTS
   - Required diagrams
   - Current skeleton file content
   - Instruction: `task: "section: [heading name]"`
   - ❌ DO NOT ask for multiple sections at once
   - ❌ DO NOT ask for "sections 2-16" or similar batches

2. **Receive section content (≤400 lines)**
   - Subagent returns markdown content for ONE section only

3. **Immediately Edit the skeleton file**
   - Use Edit tool to replace `<!-- SECTION PENDING: [heading] -->` with section content
   - ❌ DO NOT write to intermediate/temp files
   - ❌ DO NOT store content in variables for later
   - ✅ Direct replacement in docs/generated/[FILENAME]

4. **Move to next section**
   - Repeat steps 1-3 for next section
   - Continue until all sections complete

**Section content should:**
- Reference diagrams: ` ```mermaid\n[diagram content]\n``` `
- Reference other docs: `[Doc Name](FILENAME.md#section)`
- Follow GLOBAL CONSTRAINTS for all naming

**What NOT to do:**
- ❌ Generate all sections in one subagent call (too large, hard to insert)
- ❌ Create intermediate files like "doc_sections_2_16.md"
- ❌ Ask user for confirmation before appending (just do it)
- ❌ Store content anywhere except the final docs/generated/ file

### Phase 4: Review & Fix

For each completed doc:
1. Call review-docs subagent with:
   - The specific doc file path
   - GLOBAL CONSTRAINTS
   - All other completed docs (for cross-references)
2. Receive patch instructions in format:
   ```markdown
   ## PATCH 1
   SECTION: ## [Heading Name]
   ACTION: REPLACE
   REASON: [Why this change is needed]
   CONTENT:
   [replacement content, max 300 lines]

   ## PATCH 2
   SECTION: ## [Heading Name]
   ACTION: INSERT_AFTER
   REASON: [Why this change is needed]
   CONTENT:
   [new content to insert, max 300 lines]

   ## PATCH 3
   SECTION: ## [Heading Name]
   ACTION: DELETE
   REASON: [Why this section should be removed]
   ```
3. Apply patches using Edit tool

### Phase 5: Final Validation

1. Check all cross-references resolve
2. Verify diagram content is embedded correctly
3. Generate docs/generated/README.md with navigation structure:
   ```markdown
   # Generated Documentation Suite

   Generated on: [timestamp]

   ## Documents
   - [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
   - [DATABASE.md](DATABASE.md) - Database schema and data model
   - [API.md](API.md) - API endpoints and contracts
   - [FEATURES.md](FEATURES.md) - Feature documentation
   - [ONBOARDING.md](ONBOARDING.md) - Developer onboarding guide
   - [FRONTEND.md](FRONTEND.md) - Frontend architecture
   - [BACKEND.md](BACKEND.md) - Backend architecture
   - [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment procedures
   - [DEVELOPMENT.md](DEVELOPMENT.md) - Development workflow
   - [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference

   ## Quality Checks
   - All cross-references validated
   - All diagrams embedded
   - Compliance with GLOBAL CONSTRAINTS verified
   ```
4. Generate CHANGELOG.md with:
   - Generation timestamp
   - List of docs created/updated
   - Summary of review issues and resolutions
   - Any warnings or notes

## Example: Correct Section-by-Section Workflow

**✅ CORRECT (What you SHOULD do):**

```
1. Get outline from subagent → "Section 1: Intro, Section 2: Architecture, ..."
2. Write skeleton:
   # Doc Title
   <!-- SECTION PENDING: 1. Intro -->
   <!-- SECTION PENDING: 2. Architecture -->
   ...

3. Generate Section 1:
   - Call subagent: "Generate section: 1. Intro"
   - Receive: "# 1. Intro\nThis document..."
   - Edit file: Replace "<!-- SECTION PENDING: 1. Intro -->" with content

4. Generate Section 2:
   - Call subagent: "Generate section: 2. Architecture"
   - Receive: "# 2. Architecture\nThe system..."
   - Edit file: Replace "<!-- SECTION PENDING: 2. Architecture -->" with content

5. Continue until all sections complete
6. ONE FILE: docs/generated/DOCNAME.md
```

**❌ WRONG (What you did before - DON'T do this):**

```
1. Get outline
2. Write skeleton
3. Call subagent: "Generate sections 2-16" ❌ BATCH REQUEST
4. Receive massive 2000-line response ❌ TOO LARGE
5. Try to write to temp file ❌ INTERMEDIATE FILE
6. Ask user "should I append?" ❌ UNNECESSARY PROMPT
7. Finally edit main file
8. Leftover temp file ❌ CLEANUP NEEDED
```

## Context Budget Enforcement

At any moment, orchestrator context contains:
- GLOBAL CONSTRAINTS: ~100 lines
- Diagram outputs: ~150 lines each (reused across docs)
- Current outline: ~50 lines
- Current section being written: ~400 lines
- **Maximum per doc iteration: ~700 lines**

This scales to unlimited doc size because we process incrementally.

## Error Handling

If a subagent exceeds limits:
1. Truncate the response at the limit
2. Log warning to CHANGELOG.md
3. Request rewrite with explicit line count reminder

If a subagent returns malformed output:
1. Log the issue to CHANGELOG.md
2. Skip that section with a placeholder: `<!-- ERROR: Failed to generate [section] -->`
3. Continue with remaining sections

## Status Reporting

Throughout execution, report progress:
```
Phase 0: ✅ Found 2 existing docs, user chose "Skip existing"
Phase 1: ✅ Global constraints extracted
Phase 2: ✅ Generated 6 diagrams
Phase 3: Processing 8 remaining docs...
  ✅ DATABASE.md complete (1,456 lines)
  ✅ API.md complete (987 lines)
  ⏳ FEATURES.md in progress (section 3/8)
```

## Final Output

Print summary:
```
✅ Documentation generation complete

Files generated:
- docs/generated/ARCHITECTURE.md (X lines)
- docs/generated/DATABASE.md (X lines)
[... etc ...]
- docs/generated/CHANGELOG.md

Review issues: X blocking, Y important, Z minor
Context budget: Peak XXX lines (within 700 line target)

Next steps:
- Review generated docs in docs/generated/
- Address any blocking review issues
- Move approved docs to docs/ root when ready
```

## Agent Mapping

- architecture-docs → docs/generated/ARCHITECTURE.md
- database-docs → docs/generated/DATABASE.md
- api-docs → docs/generated/API.md
- features-docs → docs/generated/FEATURES.md
- onboarding-docs → docs/generated/ONBOARDING.md
- frontend-docs → docs/generated/FRONTEND.md
- backend-docs → docs/generated/BACKEND.md
- deployment-docs → docs/generated/DEPLOYMENT.md
- development-docs → docs/generated/DEVELOPMENT.md
- configuration-docs → docs/generated/CONFIGURATION.md
