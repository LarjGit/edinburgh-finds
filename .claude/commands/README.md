# Documentation Generation Commands

Two commands for managing the `/docs` suite:

## Commands Overview

### `/generate-docs` - Full Documentation Generation
**Purpose:** Generate complete documentation suite from scratch

**When to use:**
- First-time documentation setup
- Major architectural changes
- After significant refactoring
- Weekly/milestone comprehensive updates
- When you want guaranteed consistency

**What it does:**
- Reads architectural authorities (system-vision.md, architecture.md)
- Extracts GLOBAL CONSTRAINTS
- Generates all diagrams from scratch
- Creates 10 comprehensive docs using outline→section-chunks pattern
- Reviews and patches all docs
- Generates README and CHANGELOG

**Output:** Complete doc suite in `docs/generated/`

**Time:** Minutes to hours (depending on codebase size)

**Context usage:** ~550 lines peak per doc (incremental processing)

---

### `/update-docs` - Incremental Documentation Updates
**Purpose:** Update only docs affected by recent changes

**When to use:**
- Daily/routine updates after commits
- Small, localized changes (1-10 files)
- Quick refresh after feature additions
- When you know changes are isolated
- Time-sensitive updates

**What it does:**
- Detects changes since last doc generation (via git diff)
- Maps changed files to affected docs
- Updates only affected sections/docs
- Reuses existing diagrams when possible
- Appends update log to CHANGELOG

**Output:** Updated docs in `docs/generated/` (only affected files modified)

**Time:** Seconds to minutes

**Context usage:** ~400 lines per updated section

---

## Decision Matrix

| Scenario | Recommended Command | Reason |
|----------|-------------------|---------|
| First time generating docs | `/generate-docs` | Need complete baseline |
| Changed 1-3 files in engine/ | `/update-docs` | Localized, fast update |
| Changed system-vision.md | `/generate-docs` | Affects all docs |
| Added new API endpoint | `/update-docs` | Isolated to API.md |
| Refactored entire backend | `/generate-docs` | Cross-cutting changes |
| Fixed typo in README | `/update-docs` | Minimal impact |
| Changed Prisma schema | `/update-docs` | Affects DATABASE.md mainly |
| Restructured project folders | `/generate-docs` | Structural changes |
| Added new React component | `/update-docs` | Isolated to FRONTEND.md |
| Weekly documentation refresh | `/generate-docs` | Ensures consistency |
| Daily after commits | `/update-docs` | Keep docs current |
| Uncertain about change impact | `/generate-docs` | Safer, comprehensive |

---

## Quick Start Examples

### Full Generation (First Time)
```bash
# Generate everything from scratch
claude generate-docs

# What you get:
# - docs/generated/ARCHITECTURE.md
# - docs/generated/DATABASE.md
# - docs/generated/API.md
# - docs/generated/FEATURES.md
# - docs/generated/ONBOARDING.md
# - docs/generated/FRONTEND.md
# - docs/generated/BACKEND.md
# - docs/generated/DEPLOYMENT.md
# - docs/generated/DEVELOPMENT.md
# - docs/generated/CONFIGURATION.md
# - docs/generated/README.md
# - docs/generated/CHANGELOG.md
```

### Incremental Update (After Changes)
```bash
# Update docs based on recent changes
claude update-docs

# Example output:
# 🔄 Detected 5 files changed
# ✅ Updating BACKEND.md (2 sections)
# ✅ Updating DATABASE.md (full regeneration)
# ⏭️ FRONTEND.md: No changes needed
# [... other docs ...]
#
# ✅ Complete in 45 seconds (vs. 10 minutes for full generation)
```

### Update Specific Doc (Force Regeneration)
```bash
# Force regenerate a specific doc
claude update-docs --doc=DATABASE.md --full
```

### Update Since Specific Date
```bash
# Update based on changes since a date
claude update-docs --since=2026-02-01
```

---

## How They Work Together

**Recommended Workflow:**

1. **Initial Setup:**
   ```bash
   claude generate-docs
   ```
   Creates complete baseline documentation

2. **Daily Development:**
   ```bash
   # After committing changes
   claude update-docs
   ```
   Fast incremental updates as you work

3. **Weekly/Milestone:**
   ```bash
   claude generate-docs
   ```
   Full regeneration to ensure consistency and catch any drift

4. **Before Major Release:**
   ```bash
   claude generate-docs
   ```
   Comprehensive refresh with full cross-reference validation

---

## Technical Details

Both commands use the **outline→section-chunks pattern**:
- Docs never returned as full 3,000+ line blocks
- Each doc processed as outline (50 lines) + sections (400 lines each)
- Keeps orchestrator context at ~550 lines peak
- Scales to unlimited doc size without context bloat

### Context Budget (per doc)
- GLOBAL CONSTRAINTS: ~100 lines
- Diagrams: ~150 lines each
- Outline: ~50 lines
- Section content: ~400 lines
- **Peak: ~550 lines** (regardless of final doc size)

### Output Location
Both commands write to `docs/generated/`:
- Keeps generated docs separate from hand-written docs
- Safe to delete and regenerate anytime
- Move to `docs/` root when ready to publish

---

## Troubleshooting

### "Cannot find last doc generation timestamp"
**Solution:** Run `/generate-docs` first to establish baseline

### "Changes too extensive for incremental update"
**Solution:** Switch to `/generate-docs` (command will recommend this)

### "Updated docs seem incomplete"
**Solution:** Run `/generate-docs` for comprehensive regeneration

### "Docs out of sync with codebase"
**Solution:** Run `/generate-docs` weekly to prevent drift

---

## How It Works

Both commands use **parallel background agents** for speed and minimal context usage:

- Spawns multiple background agents simultaneously
- Agents write directly to files (orchestrator never sees content)
- 84% faster than sequential approach (4 min vs 25 min for full suite)
- 87% less context bloat (~2,000 lines vs ~15,000 lines)

**Performance:**
- Full generation: ~4 minutes (10 docs)
- Incremental update: ~2 minutes (5 sections)
- Context stays under 2,000 lines

---

## Future Enhancements

Potential additions to the doc generation system:
- **Smart change detection:** Better heuristics for mapping file changes to docs
- **Diff-based updates:** Show what changed in each doc section
- **Preview mode:** See what would be updated before running
- **Version tracking:** Track doc versions alongside code versions
- **CI/CD integration:** Auto-update docs on push/merge

---

## Files Reference

- **Orchestrator:** `.claude/commands/generate-docs.md` (full generation)
- **Incremental:** `.claude/commands/update-docs.md` (incremental updates)
- **Doc Agents:** `.claude/agents/*-docs.md` (11 doc generators)
- **Review Agent:** `.claude/agents/review-docs.md` (QA and patching)
- **Diagram Agents:** `.claude/agents/diagram-*.md` (11 diagram generators)
- **Context Budget:** `.claude/agents/_shared-context-budget.md` (rules and limits)
