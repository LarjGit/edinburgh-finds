---
description: Review and fix generated documentation quality issues independently after doc generation completes
allowed-tools:
  - Read
  - Glob
  - Edit
  - Task
  - TaskOutput
  - Bash
  - AskUserQuestion
---

# Review Documentation

Independent review workflow that runs after documentation generation completes. This command spawns review agents in parallel that write patches to temporary files, keeping orchestrator context minimal.

## Usage

```bash
# Review all docs
/review-docs

# Review specific doc
/review-docs ARCHITECTURE.md

# Review multiple docs
/review-docs ARCHITECTURE.md DATABASE.md FRONTEND.md
```

## Core Principle: Context-Efficient Review

**The orchestrator NEVER receives full patch content.** Instead:
1. Review agents write patches to `.claude/tmp/patches/` directory
2. Orchestrator reads ONLY patch summaries (first 30 lines)
3. User approves patches before applying
4. Patches applied using Edit tool

**Context Budget:** Orchestrator stays under 2,000 lines total (vs. ~6,300 lines if review content flooded orchestrator)

## Workflow

### Phase 1: Scan Generated Docs

**Check what docs exist:**

```bash
ls -lh docs/generated/*.md | grep -v "README\|CHANGELOG"
```

**Display found docs with details:**

```
📚 Generated Documentation

1. ARCHITECTURE.md (2,456 lines, 78 KB, modified 2026-02-08 14:32)
2. DATABASE.md (1,123 lines, 42 KB, modified 2026-02-08 14:33)
3. API.md (987 lines, 35 KB, modified 2026-02-08 14:33)
4. FEATURES.md (1,234 lines, 45 KB, modified 2026-02-08 14:34)
5. ONBOARDING.md (756 lines, 28 KB, modified 2026-02-08 14:34)
6. FRONTEND.md (1,098 lines, 39 KB, modified 2026-02-08 14:35)
7. BACKEND.md (1,567 lines, 52 KB, modified 2026-02-08 14:35)
8. DEPLOYMENT.md (654 lines, 24 KB, modified 2026-02-08 14:36)
9. DEVELOPMENT.md (892 lines, 31 KB, modified 2026-02-08 14:36)
10. CONFIGURATION.md (445 lines, 16 KB, modified 2026-02-08 14:37)
```

**If no docs found:**

```
⚠️ No documentation found in docs/generated/

Recommendation: Run /generate-docs first to create documentation.
```

### Phase 2: Let User Choose (If No Args Provided)

**If user didn't specify docs in command args, use AskUserQuestion:**

```python
AskUserQuestion(
    questions=[
        {
            "question": "Which documentation would you like to review?",
            "header": "Review Target",
            "multiSelect": True,
            "options": [
                {
                    "label": "All docs",
                    "description": "Review all 10 generated documentation files (recommended for first-time review)"
                },
                {
                    "label": "Architecture docs",
                    "description": "ARCHITECTURE.md, DATABASE.md, BACKEND.md, FRONTEND.md"
                },
                {
                    "label": "User-facing docs",
                    "description": "ONBOARDING.md, FEATURES.md, API.md"
                },
                {
                    "label": "Operational docs",
                    "description": "DEPLOYMENT.md, DEVELOPMENT.md, CONFIGURATION.md"
                }
            ]
        }
    ]
)
```

**Map user choices to doc list:**

```python
if "All docs" in choices:
    docs_to_review = ["ARCHITECTURE.md", "DATABASE.md", "API.md", "FEATURES.md",
                      "ONBOARDING.md", "FRONTEND.md", "BACKEND.md", "DEPLOYMENT.md",
                      "DEVELOPMENT.md", "CONFIGURATION.md"]
elif "Architecture docs" in choices:
    docs_to_review = ["ARCHITECTURE.md", "DATABASE.md", "BACKEND.md", "FRONTEND.md"]
# ... etc
```

### Phase 3: Spawn Review Agents (Parallel)

**Create patch output directory:**

```bash
mkdir -p .claude/tmp/patches
```

**Verify GLOBAL CONSTRAINTS exist:**

```bash
if [[ ! -f .claude/tmp/global_constraints.md ]]; then
    echo "⚠️ GLOBAL CONSTRAINTS not found. Extracting from source docs..."
    # Read and extract from docs/target/system-vision.md and architecture.md
fi
```

**Spawn review agents in parallel:**

```python
review_agents = []

for doc in docs_to_review:
    patch_file = f".claude/tmp/patches/{doc}.patch.md"

    result = Task(
        subagent_type="review-docs",
        description=f"Review {doc}",
        prompt=f"""
You are reviewing docs/generated/{doc} for quality and compliance.

## Instructions

1. Read GLOBAL CONSTRAINTS from .claude/tmp/global_constraints.md
2. Read the doc: docs/generated/{doc}
3. Check for:
   - Compliance with GLOBAL CONSTRAINTS (naming, terminology, architecture)
   - Cross-reference correctness (links to other docs, sections)
   - Consistency with other docs (read docs/generated/*.md to verify)
   - Diagram embedding correctness (diagrams should be embedded, not referenced)
   - Technical accuracy (facts match source code)
   - Structural issues (broken headings, formatting)

4. Write patch instructions to: {patch_file}

## Patch File Format

Use this format (write to {patch_file}):

```markdown
# Review Patch: {doc}

## Summary
[One-line summary: "Compliant" OR "Needs X fixes"]

## Patches Needed
[If compliant, write "None - documentation meets all quality standards"]

[Otherwise, list patches with this format:]

### PATCH 1: [Brief title]
**Priority:** [blocking / important / minor]
**Location:** [Section heading or line number]
**Issue:** [What's wrong]
**Fix:** [What to change]
**Old text:**
```
[exact text to find - must be unique in file]
```
**New text:**
```
[exact replacement text]
```

### PATCH 2: [Brief title]
...
```

## Important
- Write patches to {patch_file} (NOT to orchestrator output)
- Keep your final confirmation message under 100 lines
- Return ONLY a brief confirmation like:
  "✅ Review complete. Patches written to {patch_file}" (if issues found)
  "✅ Review complete. No issues found." (if compliant)
        """,
        run_in_background=True
    )

    review_agents.append({
        "doc": doc,
        "agent_id": result.agent_id,
        "patch_file": patch_file,
        "status": "running"
    })

print(f"\n🔍 Spawned {len(review_agents)} review agents in parallel")
```

### Phase 4: Wait and Collect Patch Summaries

**CRITICAL: Wait for ALL agents to complete before proceeding:**

```python
print("\n⏳ Waiting for all review agents to complete...")
print(f"Tracking {len(review_agents)} agents\n")

for i, agent in enumerate(review_agents):
    print(f"[{i+1}/{len(review_agents)}] Reviewing {agent['doc']}...")

    # BLOCKING WAIT
    result = TaskOutput(
        task_id=agent['agent_id'],
        block=True,
        timeout=300000  # 5 minutes max
    )

    agent['status'] = 'complete'
    print(f"  ✅ {agent['doc']} review complete\n")

print("✅ All reviews complete. Reading patch summaries...\n")
```

**Read ONLY patch summaries (not full content):**

```python
patch_summary = []

for agent in review_agents:
    if not os.path.exists(agent['patch_file']):
        patch_summary.append({
            "doc": agent['doc'],
            "summary": "ERROR: Patch file not created",
            "patch_count": 0,
            "patch_file": agent['patch_file'],
            "status": "error"
        })
        continue

    # Read first 30 lines of patch file (just summary + patch count)
    with open(agent['patch_file'], 'r') as f:
        lines = f.readlines()[:30]

    # Extract summary line (line 4: "## Summary")
    summary_line = "Unknown"
    for i, line in enumerate(lines):
        if line.startswith("## Summary"):
            summary_line = lines[i+1].strip() if i+1 < len(lines) else "Unknown"
            break

    # Count patches (count "### PATCH" occurrences)
    with open(agent['patch_file'], 'r') as f:
        full_content = f.read()
    patch_count = full_content.count('### PATCH')

    patch_summary.append({
        "doc": agent['doc'],
        "summary": summary_line,
        "patch_count": patch_count,
        "patch_file": agent['patch_file'],
        "status": "complete"
    })
```

### Phase 5: Present Patch Summary to User

**Display summary table:**

```
📊 Review Summary

ARCHITECTURE.md:
  Status: Needs fixes
  Patches: 3 (2 important, 1 minor)
  File: .claude/tmp/patches/ARCHITECTURE.md.patch.md

DATABASE.md:
  Status: Compliant
  Patches: 0
  File: .claude/tmp/patches/DATABASE.md.patch.md

API.md:
  Status: Needs fixes
  Patches: 1 (1 blocking)
  File: .claude/tmp/patches/API.md.patch.md

FEATURES.md:
  Status: Compliant
  Patches: 0
  File: .claude/tmp/patches/FEATURES.md.patch.md

FRONTEND.md:
  Status: Needs fixes
  Patches: 2 (2 minor)
  File: .claude/tmp/patches/FRONTEND.md.patch.md

BACKEND.md:
  Status: Compliant
  Patches: 0
  File: .claude/tmp/patches/BACKEND.md.patch.md

... (remaining docs)

Total: 6 patches across 3 docs
  - Blocking: 1
  - Important: 2
  - Minor: 3
```

**Ask user what to do:**

```python
AskUserQuestion(
    questions=[
        {
            "question": "How would you like to proceed with the review patches?",
            "header": "Action",
            "multiSelect": False,
            "options": [
                {
                    "label": "Apply all patches automatically",
                    "description": "Recommended - Apply all 6 patches to the documentation files"
                },
                {
                    "label": "Review patches first, then decide",
                    "description": "Read patch files manually before applying"
                },
                {
                    "label": "Apply only blocking/important patches",
                    "description": "Skip minor patches, apply only critical ones (3 patches)"
                },
                {
                    "label": "Skip - Keep docs as-is",
                    "description": "Do not apply any patches"
                }
            ]
        }
    ]
)
```

### Phase 6: Apply Patches

**If user chooses "Apply all" or "Apply only blocking/important":**

```python
for patch_info in patch_summary:
    if patch_info['patch_count'] == 0:
        print(f"⏭️ {patch_info['doc']}: No patches needed")
        continue

    print(f"\n📝 Applying patches to {patch_info['doc']}...")

    # Read full patch file
    with open(patch_info['patch_file'], 'r') as f:
        patch_content = f.read()

    # Parse patches
    patches = parse_patches(patch_content)  # Helper function

    # Filter by priority if needed
    if user_choice == "Apply only blocking/important":
        patches = [p for p in patches if p['priority'] in ['blocking', 'important']]

    # Apply each patch using Edit tool
    for i, patch in enumerate(patches):
        print(f"  [{i+1}/{len(patches)}] {patch['priority'].upper()}: {patch['title']}")

        try:
            Edit(
                file_path=f"docs/generated/{patch_info['doc']}",
                old_string=patch['old_text'],
                new_string=patch['new_text']
            )
            print(f"    ✅ Applied successfully")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            print(f"    (Patch file available at {patch_info['patch_file']} for manual application)")

    print(f"  ✅ Completed {patch_info['doc']} ({len(patches)} patches applied)")
```

**Helper function to parse patches:**

```python
def parse_patches(patch_content):
    """Parse patch file into structured patches."""
    patches = []

    # Split by ### PATCH markers
    patch_sections = patch_content.split('### PATCH ')[1:]  # Skip first part (header)

    for section in patch_sections:
        lines = section.split('\n')

        # Extract patch metadata
        title = lines[0].split(':', 1)[1].strip() if ':' in lines[0] else "Unknown"

        priority = "minor"
        location = ""
        issue = ""
        fix = ""
        old_text = ""
        new_text = ""

        in_old_block = False
        in_new_block = False

        for line in lines[1:]:
            if line.startswith('**Priority:**'):
                priority = line.split(':', 1)[1].strip()
            elif line.startswith('**Location:**'):
                location = line.split(':', 1)[1].strip()
            elif line.startswith('**Issue:**'):
                issue = line.split(':', 1)[1].strip()
            elif line.startswith('**Fix:**'):
                fix = line.split(':', 1)[1].strip()
            elif line.startswith('**Old text:**'):
                in_old_block = True
                in_new_block = False
            elif line.startswith('**New text:**'):
                in_old_block = False
                in_new_block = True
            elif line.startswith('```') and in_old_block:
                in_old_block = not in_old_block  # Toggle
            elif line.startswith('```') and in_new_block:
                in_new_block = not in_new_block  # Toggle
            elif in_old_block and not line.startswith('```'):
                old_text += line + '\n'
            elif in_new_block and not line.startswith('```'):
                new_text += line + '\n'

        patches.append({
            'title': title,
            'priority': priority,
            'location': location,
            'issue': issue,
            'fix': fix,
            'old_text': old_text.strip(),
            'new_text': new_text.strip()
        })

    return patches
```

### Phase 7: Cleanup

**Remove temporary patch files:**

```bash
rm -rf .claude/tmp/patches
```

### Final Output

**If patches were applied:**

```
✅ Review Complete

Docs Reviewed: 10
Patches Found: 6
Patches Applied: 6
Time: 2 minutes 15 seconds

Results:
✅ ARCHITECTURE.md - 3 patches applied
✅ DATABASE.md - No changes needed
✅ API.md - 1 patch applied
✅ FEATURES.md - No changes needed
✅ ONBOARDING.md - No changes needed
✅ FRONTEND.md - 2 patches applied
✅ BACKEND.md - No changes needed
✅ DEPLOYMENT.md - No changes needed
✅ DEVELOPMENT.md - No changes needed
✅ CONFIGURATION.md - No changes needed

Patch Breakdown:
- Blocking: 1 (fixed)
- Important: 2 (fixed)
- Minor: 3 (fixed)

Next Steps:
- Review updated docs in docs/generated/
- Run /review-docs again if you want another review pass
- Commit changes when satisfied
```

**If no patches needed:**

```
✅ Review Complete

Docs Reviewed: 10
Patches Found: 0
Time: 1 minute 45 seconds

All documentation meets quality standards:
✅ ARCHITECTURE.md - Compliant
✅ DATABASE.md - Compliant
✅ API.md - Compliant
✅ FEATURES.md - Compliant
✅ ONBOARDING.md - Compliant
✅ FRONTEND.md - Compliant
✅ BACKEND.md - Compliant
✅ DEPLOYMENT.md - Compliant
✅ DEVELOPMENT.md - Compliant
✅ CONFIGURATION.md - Compliant

Documentation is ready for use!
```

## Context Efficiency Analysis

**Without /review-docs (embedded in /generate-docs):**
- Orchestrator receives 21 review agent outputs
- Each review agent returns ~300 lines (patch instructions)
- Total context bloat: ~6,300 lines
- Peak orchestrator context: >8,000 lines

**With /review-docs (separate command):**
- Orchestrator reads ONLY patch summaries (30 lines each)
- Total context: ~300 lines (10 docs × 30 lines)
- Peak orchestrator context: ~1,800 lines
- **Reduction: 77% less context**

**Additional Benefits:**
- User can choose when to review (optional step)
- Can run multiple review passes
- Can review specific docs only
- Separates concerns (generation vs. review)

## When to Use This Command

**Run /review-docs when:**
- You've completed /generate-docs or /update-docs
- You want to check documentation quality
- You're preparing to commit documentation
- You want to ensure consistency across docs

**Skip /review-docs when:**
- Documentation is for exploratory/draft purposes
- You're confident in generated output
- Time-sensitive and quality can be verified later

**Rule of thumb:** Always review before committing to main branch.

## Error Handling

**No global constraints found:**

```
⚠️ GLOBAL CONSTRAINTS not found at .claude/tmp/global_constraints.md

This file is required for review. Extracting from source docs...

Reading docs/target/system-vision.md and docs/target/architecture.md...
✅ GLOBAL CONSTRAINTS extracted
```

**Review agent fails:**

```
⚠️ Review agent failed: task_42 (FRONTEND.md)

Reading agent output...
[diagnosis from agent output]

Options:
1. Retry review for FRONTEND.md
2. Skip FRONTEND.md (continue with other docs)
3. Abort entire review
```

**Patch application fails:**

```
⚠️ Failed to apply patch to ARCHITECTURE.md
  Patch: "Fix canonical naming"
  Error: old_string not found in file

The patch file is available at:
.claude/tmp/patches/ARCHITECTURE.md.patch.md

Options:
1. Skip this patch (continue with others)
2. Open patch file for manual application
3. Abort patch application
```

**No docs to review:**

```
⚠️ No documentation found to review

Have you run /generate-docs yet?

Run /generate-docs now? [Y/n]
```

## Performance Expectations

| Docs Reviewed | Agent Count | Time (Review + Apply) | Context Peak |
|---------------|-------------|----------------------|--------------|
| 1 doc         | 1           | ~30 seconds          | ~500 lines   |
| 3 docs        | 3           | ~45 seconds          | ~800 lines   |
| 10 docs (all) | 10          | ~2 minutes           | ~1,800 lines |

**Note:** Time varies based on patch count and complexity.
