# Development Methodology — Reality-Based Incremental Alignment

**Status:** Active Methodology  
**Last Updated:** 2026-02-12  
**Purpose:** Define the invariant execution discipline for how work is planned, implemented, validated, and proven — independent of what direction is currently chosen.

---

## Related Documents

- **CLAUDE.md:** Project overview, architecture quick reference, commands, reading paths
- **docs/system-vision.md:** Architectural constitution (10 immutable invariants) — GOLDEN DOC
- **docs/target-architecture.md:** Runtime execution pipeline specification (11 stages) — GOLDEN DOC
- **docs/process/development-roadmap.md:** Strategic intent for what we are choosing to pursue (replaceable)
- **`docs/progress/development-catalog.md`:** Execution ledger (items + completion proofs)
- **docs/progress/development-catalog-archive.md:** Completed item archive (append-only)
- **docs/progress/lessons-learned.md:** Patterns, pitfalls, doc clarifications (institutional learning)

**Golden Docs Defined:** `system-vision.md` and `target-architecture.md` are the immutable architectural constitution. All work must be **compatible with** these documents. When golden docs define a rule or constraint, that rule cannot be violated. Conflicts → golden docs always win.

**Boundary Rule**

- This document governs **HOW** work is executed.
- Direction is informed by the Development Roadmap and confirmed by user judgment.
- The Development Catalog is a ledger of scoped work items and proofs (no strategy).

---

## Table of Contents

1. Constraint System (C1–C9)
2. Workflow A: Catalog Item Creation (Steps 1-3)
3. Workflow B: Catalog Item Execution (Steps 4-11)
4. Validation Gates (Gate 1–6)
5. Recovery Protocol
6. Templates
7. Catalog Archival Policy
8. Quick Reference

---

## 1. Constraint System

**Purpose:** Hard rules that prevent agents from drifting off-piste.

These constraints are **MANDATORY** and **CANNOT BE VIOLATED**.

---

### C1: Golden Doc Compatibility

- All work must be **compatible with** `system-vision.md` and `target-architecture.md`
- Golden docs define the architectural rules and constraints of the system
- No work may violate golden doc rules
- When in doubt → read golden docs, don't assume
- Conflicts → golden docs always win

**For Principle-Driven work:**

- MUST reference the specific golden doc section being advanced
- Change explicitly upholds or restores a stated principle

**For Goal-Driven work (features, bugs, infrastructure):**

- Must not violate any golden doc rules
- Must operate within established architectural boundaries
- Compatibility verified, but explicit principle reference not required

**Enforcement:** Catalog items declare their type; validation approach depends on type

---

### C2: Reality-Based Planning

- MUST read actual code files before planning (Step 4 mandatory in Workflow B)
- NO assumptions about code structure
- If assumption needed → verify by reading code
- Mental models are forbidden

**Enforcement:** Step 4 review results must be included in micro-plan

---

### C3: Scope Limits

- **Maximum 2 files changed** (excluding tests)
- **Maximum 1 architectural seam crossed**
- **Maximum 100 lines of code changed**
- If scope grows → split into multiple catalog items

**Enforcement:** User checkpoint 1 verifies scope before approval

---

### C4: Proof-First Validation

- Test must be written BEFORE implementation
- Test must validate the stated goal
- For principle-driven work: test must explicitly validate golden doc compliance
- No test = no implementation

**Alternative proofs accepted:**

- CLI validation command
- Database query demonstrating correct entity data

**Enforcement:** Step 7 requires RED test before GREEN implementation

---

### C5: Catalog Fidelity

- Only work on items in the catalog
- No improvisation or "while we're here" changes
- Discovered work → add to catalog, don't fix immediately
- One item at a time, fully complete before next

**Enforcement:** User checkpoint 1 verifies work matches catalog item

---

### C6: Foundation Permanence

- Completed foundation changes are NEVER revisited
- No "temporary" solutions or scaffolding
- Every change is production-quality
- Technical debt is forbidden

**Enforcement:** User checkpoint 2 validates quality before marking complete

---

### C7: User Validation Required

- Agent cannot mark item complete without user approval
- User must validate outcome at checkpoint 2
- User must approve micro-plan at checkpoint 1
- No autonomous completion

**Enforcement:** Step 10 only executes after user checkpoint 2 approval

---

### C8: Collaborative Shaping Required (Workflow A Only)

- No Development Catalog item may be created, accepted, or executed without completion of Step 2 and explicit user confirmation at Step 3
- **No code reading, no reality investigation, no planning until Step 3 is complete**

**Enforcement:** Step 3 is a mandatory gate before Workflow B can begin

---

### C9: Catalog Persistence Required

- No execution (Workflow B) may begin without catalog items persisted to file
- Step 4 (Code Reality Review) reads from catalog file, not conversation memory
- Session clearing between Step 3 (end of Workflow A) and Step 4 (start of Workflow B) is explicitly supported
- Catalog items are the handoff point between strategic shaping and tactical execution

**Enforcement:** Step 4 begins by reading catalog item from file; if item not in file, execution cannot proceed

---

## 2. Workflow A: Catalog Item Creation

**Purpose:** Convert strategic intent into concrete, scoped catalog items ready for execution.

**Context:** This workflow is exploratory and context-heavy. Requires understanding of roadmap, golden docs, and high-level architecture. Does NOT require reading actual code.

**Output:** One or more catalog items written to `docs/progress/development-catalog.md`

**Session Independence:** After Step 3 completes, session can be cleared. Workflow B is context-independent.

---

### Step 1 — Identify the Next Focus

**User Action:**

- Consult the Development Roadmap
- Identify a strategic direction to pursue:
    - Architectural convergence (fix violations)
    - New feature development
    - Bug fixes
    - Infrastructure improvements
    - Capability additions

**Agent Action:**

- Acknowledge the chosen direction
- Prepare to ask shaping questions (do NOT start asking yet)

**No catalog item exists yet.**

---

### Step 2 — Collaborative Shaping (Interactive Q&A)

**Purpose:** Through structured dialogue, shape the strategic intent into one or more concrete catalog items.

**CRITICAL INTERACTION PROTOCOL:**

The agent must conduct an **interactive question-and-answer session** using the following mandatory pattern:

1. **One question at a time** — never present multiple questions simultaneously
2. **Each question must offer 3-5 specific options** based on architectural patterns, roadmap context, or typical work categories
3. **Every question MUST include a final option: "None of these / I'll specify: [free text]"**
4. **After each answer**, the agent asks: **"Continue with next question, or proceed to catalog item proposal?"**
5. User may choose to continue questioning or move to proposal at any point

**Question Categories (Examples):**

**Work Type Classification:**

> "What type of work is this? A) Principle-Driven (fixing architectural violation or advancing golden doc principle) B) Feature (new capability within established architecture) C) Bug Fix (correcting existing behavior) D) Infrastructure (tooling, logging, dev experience) E) None of these / I'll specify: [your answer]"

**Scope Boundaries:**

> "Which architectural layer should this touch? A) Extraction layer only B) Classification layer only C) Lens configuration only D) Multiple layers (will need careful scoping) E) None of these / I'll specify: [your answer]"

**Proof Strategy:**

> "How should this change be validated? A) Unit test checking specific behavior B) Integration test running entity through pipeline C) Database inspection for correct entity data D) CLI command validation E) None of these / I'll specify: [your answer]"

**FORBIDDEN BEHAVIORS:**

- ❌ Presenting 5-10 questions in a single message
- ❌ Asking open-ended questions without options
- ❌ Continuing to next question without user choosing to continue
- ❌ Assuming answers based on "typical" patterns
- ❌ Reading code files (happens in Workflow B, not here)

**Output of this step:**

One OR MORE **draft catalog items**, each containing:

- Type (Principle-Driven | Feature | Bug | Infrastructure)
- Goal and boundaries
- Exclusions
- Proof approach
- Golden Doc Reference (for Principle-Driven work)
- Estimated files to touch
- Estimated scope
- Ordering if more than one item

**Scope Gate:** Draft items must already satisfy C3 (≤2 code files, ≤100 LOC, ≤1 seam). Items that exceed these limits must be split during this step.

---

### Step 3 — Catalog Validation & Persistence

**Purpose:** User validates draft items and agent persists approved items to catalog file.

**Agent Action:** Present each draft catalog item in the format:

```markdown
### [DRAFT] [ID]: [Title]
- **Type:** [Principle-Driven | Feature | Bug | Infrastructure]
- **Golden Doc Reference:** [if Principle-Driven: specific section]
- **Goal:** [concise statement]
- **Boundaries:** [what's in scope]
- **Exclusions:** [what's explicitly out of scope]
- **Files (Estimated):** [best guess - verified during execution]
- **Proof Approach:** [test type, CLI command, or DB query]
- **Estimated Scope:** [N files, ~M lines] (must satisfy C3)
- **Status:** [ ] Pending
```

**User Review:**

- Is the type correct?
- Is scope within C3 limits?
- Are boundaries clear?
- Is proof approach sensible?
- For Principle-Driven: Is golden doc reference specific enough?

**User Decision:**

- ✅ **Approve** → agent writes to catalog file
- 🔄 **Revise** → return to Step 2 with clarifications
- ❌ **Reject** → discard this item

**Agent Action Upon Approval:**

1. Write approved items to `docs/progress/development-catalog.md`
2. Remove `[DRAFT]` prefix
3. Confirm to user: "Catalog items [IDs] written to catalog. Session can be cleared. To execute, reference catalog item ID."

**🎯 CHECKPOINT: Session can be cleared after this step**

---

## 3. Workflow B: Catalog Item Execution

**Purpose:** Execute a single catalog item from planning through completion.

**Context:** This workflow is code-intensive and tactical. Requires reading actual code files. Does NOT require knowledge of how item was shaped.

**Input:** Catalog item ID (e.g., "Execute EP-001")

**Output:** Code changes, tests, catalog item marked complete with proof

**Session Independence:** Starts fresh by reading catalog item from file. No dependency on Workflow A conversation.

---

### Step 4 — Code Reality Review (MANDATORY)

**Precondition:** Catalog item must exist in `docs/progress/development-catalog.md`

**Agent Action:**

1. **Read the catalog item from file**

```bash
   # Agent reads:
   `docs/progress/development-catalog.md`
   # Locates the specified item by ID
```

2. **Identify files to review based on catalog item's "Files (Estimated)"**
   - Primary file being changed
   - Files that import/depend on it
   - Test files

3. **Read ALL files using Read tool**
```
   Read: path/to/primary_file.py
   Read: path/to/dependency_file.py  # (if primary imports it)
   Read: tests/path/to/test_file.py
```

4. **Document actual structure**
   - Function signatures: `def function_name(params) -> return_type:`
   - Class definitions: `class ClassName:`
   - Dependencies: `from module import something`
   - Current implementation behavior

5. **List explicit assumptions**
   - "Function X takes parameters Y and Z"
   - "Function X returns type A, not type B"
   - "File A imports File B"

6. **Verify assumptions by reading code**
   - Never guess
   - Never assume based on naming
   - Never use mental model of "how it should be"

**Red Flag:** If you find yourself saying "I assume..." → STOP and read the code

**Output:** Clear understanding of actual code structure to inform micro-plan

---

### Step 4.5 — Existing Micro-Plan Check (Mandatory)

**Purpose:**  
Prevent plan drift and ensure execution follows the persisted micro-plan when one already exists.

Before drafting a new micro-plan (Step 5), the agent MUST:

1. Compute the expected path:
   - `tmp/microplan_<CATALOG_ITEM_ID>.md`

2. Check whether that file exists.

3. If the file exists:
   - The agent MUST immediately load and read it.
   - The agent MUST treat it as the authoritative execution plan.
   - The agent MUST NOT draft a new plan in chat.
   - The agent MUST proceed directly to execution using the loaded plan.

4. If the file does not exist:
   - The agent may proceed to Step 5 and draft a new micro-plan.

**Violation Rule:**  
If a micro-plan exists in `tmp/` and the agent drafts a new one in chat, execution must stop and restart from this step.

---

### Step 5 — Write Micro-Plan

Create a **half-page maximum** plan that:

**Header:**
- Catalog Item ID: [ID]
- Type: [from catalog]
- Golden Doc Reference: [if Principle-Driven, from catalog]
- Files Touched: [list] (max 2)

**Current State (from Step 4 review):**
```
# Lines X-Y in file.py contain:
[actual code from review]
# (explanation of current behavior)
```

**Minimal Change:**

- [specific change to specific lines]
- [replacement logic in generic terms]

**Executable Proof:**

- Test `test_name()` passes
- Existing tests still pass
- [specific validation outcome from catalog]

**Scope Check:**

- ✅ ≤2 code files ([N] file)
- ✅ ≤100 LOC (~M lines)
- ✅ ≤1 seam ([boundary name] only)

**Note on Code Examples:** Use generic placeholders (e.g., `domain_term_A`, `ValidationEntity`, `helper_function_B`) rather than concrete domain examples to prevent cognitive bleed into unrelated work.

---

#### 🛑 USER CHECKPOINT 1: Approve Micro-Plan (1-2 min)

**Position:** Between Steps 5 and 5.5.

**Agent presents:** "Catalog item [ID]. Will change [specific function in file]. Here's the micro-plan. Approve?"

**User reviews:**

- Is scope within C3 limits?
- Is golden doc reference correct (if Principle-Driven)?
- Does current state match reality?
- Is pass criteria clear?

**Quick Approval Checklist:**

- ✅ Scope within C3 limits?
- ✅ Golden doc reference clear (if Principle-Driven)?
- ✅ Current state looks accurate?
- ✅ Pass criteria unambiguous?
- ✅ Feels like "one thing"?

**User decides:**

- ✅ Approve → proceed
- 🔄 Revise → agent updates plan
- ❌ Reject → agent proposes different approach or stops

After approval, perform Step 5.5 (Persist Approved Micro-Plan).

---

### Step 5.5 — Persist Approved Micro-Plan

After Checkpoint 1 approval, the agent must write the approved micro-plan to:

`tmp/microplan_<CATALOG_ITEM_ID>.md`

Ensure `tmp/` exists (create if missing).

This file is the execution source of truth for the item.

---

### Step 6 — Review Constraints (Agent Self-Check)

Before executing, verify all constraints satisfied:

- ✅ Single architectural concern addressed
- ✅ All assumptions verified from actual code (not guessed) — C2
- ✅ Pass criteria clear and testable
- ✅ No more than one "seam" crossed — C3
- ✅ Maximum 2 files changed — C3
- ✅ Maximum 100 lines of code changed — C3
- ✅ Proof-first approach planned — C4
- ✅ Work matches catalog item — C5
- ✅ For Principle-Driven: golden doc reference explicit — C1

**If any constraint violated → return to Step 5, revise plan**

Confirm C1–C9 are satisfied. If not, stop and report blocker.

---

### Step 6.5 — Reload Micro-Plan from `tmp/`

Before any implementation begins, the agent must re-open and read:

`tmp/microplan_<CATALOG_ITEM_ID>.md`

Execution must follow the contents of that file.

If the chat context and the `tmp/` micro-plan differ, the `tmp/` file governs execution.

---

### Step 7 — Execute with Proof-First / TDD

**Red → Green → Refactor:**

1. **Write failing test FIRST** **For Principle-Driven work:**

```python
   def test_component_upholds_principle():
       """Validates [Golden Doc Reference]: [Principle Name]"""
       # Test that explicitly validates the principle
       source = inspect.getsource(target_module)
       forbidden = ["pattern_A", "pattern_B"]
       for term in forbidden:
           assert term.lower() not in source.lower()
```

**For Goal-Driven work (Feature/Bug):**

```python
   def test_feature_behavior():
       """Validates: [Goal from catalog]"""
       # Test that validates correct behavior
       result = target_function(test_input)
       assert result == expected_output
```

2. **Confirm test fails (RED)**

```bash
   pytest tests/path/to/test_file.py::test_name
   # Should fail with current code
```

3. **Implement minimum code to pass (GREEN)**
    - Make the change described in micro-plan
    - Run test until it passes
4. **Refactor while keeping tests green**
    - Improve code quality
    - Maintain test passing
5. **Run full test suite**

```bash
   pytest path/to/module/
   # Ensure no regressions
```

**Key Rule:** If at ANY point assumptions were wrong or blockers appear → STOP, return to Step 4 (Code Reality Review)

---

### Step 8 — Execution Amendment (Adaptive Re-Shaping)

**Purpose:** Acknowledge that reality discovered during execution may legitimately invalidate parts of an approved micro-plan without invalidating the overall goal. This step provides a disciplined path to adapt without restarting from zero.

**Trigger Conditions (any of the following):**

- A technical assumption in the micro-plan proves false (e.g., incorrect patch point, API shape mismatch)
- New constraints emerge from Code Reality Review performed during execution
- The original approach would violate success criteria or architectural constraints if continued
- The goal remains unchanged and scope stays within the approved catalog item

**Required Agent Output:** When triggered, the agent MUST produce an **Execution Amendment Notice** containing:

1. **Broken Assumption** – what proved incorrect
2. **New Facts** – evidence from code/reality
3. **Proposed Delta** – minimal change to plan
4. **Impact Statement** – confirmation that:
    - success criteria remain satisfied
    - scope limits (C3) remain intact
5. **Updated Proof Strategy** (if needed)

**User Decision:**

- User may approve the amendment inline without creating a new catalog item
- If scope would expand beyond C3 limits, the agent MUST stop and create a new catalog item via Workflow A

**Guardrails:**

- ❌ No silent pivots
- ❌ No continuation after invalidated assumptions without approval
- ✅ Momentum preserved when goal and scope are stable
- ✅ Full audit trail maintained via amendment notices

If Step 8 occurs and is approved, the amendment must be appended to:

`tmp/microplan_<CATALOG_ITEM_ID>.md`

This file remains append-only during execution.

---

### Step 9 — Agent Self-Validation

**Before presenting to user at Checkpoint 2, agent must verify:**

**For Principle-Driven Work:**

1. **Re-read relevant section of golden docs**
    - [Golden Doc Reference from catalog]
    - "[Exact principle statement]"
2. **Manual verification**
    - Question: "Does this change uphold/advance the principle?"
    - Evidence: Point to specific code demonstrating compliance
    - If unsure → it fails
3. **Check test explicitly validates golden doc compliance**
    - Test references the principle (comment or test name)
    - Test would catch regression

**For Goal-Driven Work (Feature/Bug/Infrastructure):**

1. **Golden doc compatibility check**
    - Does this change violate ANY rule in system-vision.md?
    - Does this change violate ANY constraint in target-architecture.md?
    - If yes → it fails
2. **Goal achievement verification**
    - Question: "Does this change achieve the stated goal from catalog?"
    - Evidence: Point to specific behavior change
    - If unsure → it fails
3. **Check test validates the goal**
    - Test verifies the intended behavior
    - Test would catch regression

**For All Work Types:**

4. **Ensure no new violations introduced elsewhere**
    - Review all changed files
    - Check for unintended consequences

**Agent completes this step, then presents results at Checkpoint 2**

---

#### 🛑 USER CHECKPOINT 2: Validate Result (2-3 min)

**Agent presents:** "Complete. Catalog item [ID]. Changed [files]. Test passes: [test name]. Step 9 validation complete. Review?"

**User validates:**

1. **Look at diff:** Review actual changes

```bash
   git diff path/to/changed_file.py
```

2. **Run tests yourself:**

```bash
   pytest tests/path/to/test_file.py -v
```

3. **Verify scope:** Only planned files changed?
4. **Check goal/principle alignment:**
    - **Principle-Driven:** Does it uphold the golden doc principle?
    - **Goal-Driven:** Does it achieve the catalog goal without violating golden docs?

**Quick Validation Checklist:**

- ✅ Only planned files touched?
- ✅ Tests pass when I run them?
- ✅ No "extra" changes snuck in?
- ✅ Upholds principle OR achieves goal (depending on type)?

**User decides:**

- ✅ Approve → proceed to Step 10
- 🔄 Revise → agent fixes issues
- ❌ Reject → revert changes, return to planning

---

### Step 10 — Mark Complete & Commit

**Only after user approval:**

1. **Update catalog**
    - Mark item as `[x]` complete
    - Add completion date + commit hash
    - Include the executable proof command(s)
    - Update "Last Updated" timestamp in catalog file
2. **Commit with conventional commit message**

```bash
   git add path/to/changed_file.py tests/path/to/test_file.py
   
   git commit -m "[type](scope): description
   
   Detailed explanation of what was changed and why.
   
   [For Principle-Driven]: Validates: [Golden Doc Reference]
   [For All]: Achieves: [Goal from catalog]
   Catalog Item: [ID]
   
   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

3. **Foundation is now solid**
    - Never needs to be revisited
    - Permanent improvement
4. **Completion cleanup**
    - Delete `tmp/microplan_<CATALOG_ITEM_ID>.md`
    - Micro-plan files are transient execution artifacts and are not retained as governance records
5. Proceed to Step 11 (Compounding)

---

### Step 11 — Compounding (Mandatory, Lightweight)

**Purpose:** Ensure that validated work improves future work quality, not just current correctness.

This step captures institutional learning without adding ceremony or slowing execution.

**After completing Step 10, the agent MUST answer the following three questions:**

1. **Pattern Candidate?**
    - Yes / No
    - If yes:
        - Describe the pattern in 1–2 sentences
        - Reference the concrete example (file, test, or commit)
2. **Documentation Clarity Improvement?**
    - Yes / No
    - If yes:
        - Identify the relevant section of `system-vision.md` or `target-architecture.md`
        - Propose a one-line clarification or note
3. **Future Pitfall Identified?**
    - Yes / No
    - If yes:
        - State the pitfall in a single sentence (what future work must avoid or watch for)

**Recording:** Capture answers in `docs/progress/lessons-learned.md`.

**Rules:**

- Compounding observations are proposals, not automatic changes
- The user decides whether to:
    - ignore
    - defer
    - or promote the observation into documentation
- **No files are required to be updated during this step**

**Key Principle:** If a lesson was learned and not recorded, it will be relearned the hard way later.

---

## 4. Validation Gates

**Purpose:** Define unambiguous criteria for "this change is solid and permanent".

Every change must pass **ALL gates** before being marked complete.

---

### Gate 1: Golden Doc Compatibility

**For Principle-Driven Work:**

- Re-read the golden doc section referenced in catalog
- Question: "Does this change uphold/advance the stated principle?"
- Evidence: Point to specific code demonstrating compliance

**For Goal-Driven Work:**

- Question: "Does this change violate ANY golden doc rule?"
- Check system-vision.md invariants
- Check target-architecture.md constraints
- Evidence: No violations found

**Pass Criteria:**

- Principle-Driven: Change clearly upholds the principle
- Goal-Driven: Change violates no golden doc rules
- Evidence is concrete and verifiable
- If unsure → it fails

---

### Gate 2: Proof Passes

**Check:**

- The test passes (green)
- For Principle-Driven: test explicitly validates golden doc compliance
- For Goal-Driven: test validates the stated goal
- Full test suite passes (no regressions)
- Coverage >80% for changed code

**Pass Criteria:**

```bash
pytest tests/module/ -v
# All tests pass

pytest --cov=module --cov-report=term
# Coverage >80%
```

**Alternative proof criteria:**

- CLI validation command produces expected output
- Database query returns correct entity shape

---

### Gate 3: Diff Matches Plan

**Check:**

- Changed code matches what was planned (no drift)
- No "extra" changes or improvements sneaked in
- All files touched were listed in micro-plan
- Scope stayed within C3 limits

**Pass Criteria:**

```bash
git diff --stat
# Only planned files changed
# Line count within limits
```

---

### Gate 4: Zero Assumptions

**Check:**

- All code integrated actually exists (no hallucinated APIs)
- All imports resolve correctly
- All function signatures match actual definitions
- Run the code/tests to prove it works

**Pass Criteria:**

```bash
python -m pytest tests/path/to/test_file.py -v
# Tests pass (proves code actually works)
```

---

### Gate 5: Catalog Updated

**Check:**

- Item marked complete `[x]` with date + commit hash
- Executable proof command(s) documented
- Any discovered work added to catalog as new items
- Next item is clear

**Pass Criteria:**

- Catalog file shows item completed
- No orphaned work discovered during implementation

---

### Gate 6: Reality Validation (DB Truth)

**Check:**

- For code-level changes: unit tests pass (proves logic correct)
- For pipeline-level changes: integration tests pass (proves flow correct)
- For end-to-end validation: **database inspection shows correct entity data**

**Pass Criteria:**

Code-level:

```bash
pytest tests/path/to/test_file.py -v
# All tests green
```

End-to-end:

```bash
# Run validation entity through pipeline
python -m engine.orchestration.cli run "validation entity name" --lens target_lens

# Inspect database - entity data must match expected values
psql $DATABASE_URL -c "
SELECT entity_name, entity_class, canonical_activities, canonical_place_types, modules
FROM entities
WHERE entity_name ILIKE '%validation_entity%';"

# Expected output must match architecture requirements
```

**Critical Rule (system-vision.md 6.3):**

> "The entity database is the ultimate correctness signal. Tests that pass but produce incorrect entity data constitute a failure."

**If tests pass but entity data is wrong or incomplete → FAILURE**

---

### Fail Fast Rule

**If ANY gate fails → do NOT proceed**

Actions:

- Fix the issue, OR
- Revert the change
- Never mark incomplete work as done

---

## 5. Recovery Protocol

**Purpose:** Define what to do when things go wrong.

### Detection Signals (When to STOP)

---

#### Signal 1: Assumption Violation

**Symptoms:**

- Code structure doesn't match what was planned
- Function signatures are different
- Files don't exist where expected
- Dependencies are missing

**Action:**

1. **STOP immediately.** Do not improvise.
2. Return to Step 4 (Code Reality Review)
3. Update understanding of actual code
4. Revise micro-plan based on reality, OR
5. If scope grows beyond C3, stop and create new catalog item via Workflow A

---

#### Signal 2: Scope Creep

**Symptoms:**

- Change touches more than 2 files (excluding tests)
- Discovers additional work or gaps
- Requires crossing more than one architectural seam
- Requires more than 100 lines of code changed

**Action:**

1. **STOP.**
2. Mark current item as "blocked" or "needs split"
3. Return to Workflow A to create new catalog items for discovered work
4. Choose smaller scope OR address blocker first

---

#### Signal 3: Proof Failures Beyond Scope

**Symptoms:**

- Tests failing in unrelated parts of codebase
- Regression failures not anticipated in plan
- Cannot make tests pass without additional changes

**Action:**

1. **STOP.** Assess blast radius.
2. Either:
    - **(A)** Add regression fix to current item if small (<10 lines)
    - **(B)** Revert changes, create new catalog item for regression via Workflow A, fix that first
3. Return to Step 4 or Workflow A as appropriate

---

#### Signal 4: Golden Doc Conflict

**Symptoms:**

- Implementation conflicts with system-vision.md or target-architecture.md
- Cannot satisfy both the plan and golden docs
- Architectural rule being violated

**Action:**

1. **STOP immediately.** Golden docs win.
2. Revert changes
3. Re-read golden docs carefully
4. Return to Workflow A to reshape catalog item, OR
5. Return to Step 5 to revise micro-plan within current catalog item

---

#### Signal 5: Agent Going Off-Piste

**Symptoms:**

- Agent making changes not in the micro-plan
- "While we're here" improvements
- Refactoring beyond scope
- Adding features not in catalog

**Action:**

1. **STOP.**
2. Revert unauthorized changes
3. Re-read micro-plan
4. Only implement what's explicitly in the plan
5. **No exceptions.**

---

### Recovery Steps (Universal Process)

1. **Stop Work** - No more code changes
2. **Assess State** - What went wrong? Which signal triggered?
3. **Revert if Needed** - `git revert` or `git reset` to last solid foundation
4. **Update Catalog** - Add newly discovered work as separate items (Workflow A)
5. **Revise Understanding** - Re-review code reality if assumptions were wrong
6. **Choose Path** - Return to appropriate workflow step

---

## 6. Templates

### Catalog Item Template (Principle-Driven)

```markdown
### [ID]: [Title]
- **Type:** Principle-Driven
- **Golden Doc Reference:** [document] [section] ([Principle Name])
- **Goal:** [concise statement of what will change to uphold/advance principle]
- **Boundaries:** [what is in scope]
- **Exclusions:** [what is explicitly out of scope]
- **Files (Estimated):** [best guess at files - verified during execution]
- **Proof Approach:** [test type that validates golden doc compliance]
- **Estimated Scope:** [N files, ~M lines] (must satisfy C3: ≤2 files, ≤100 LOC, ≤1 seam)
- **Status:** [ ] Pending
```

### Catalog Item Template (Goal-Driven: Feature/Bug/Infrastructure)

```markdown
### [ID]: [Title]
- **Type:** [Feature | Bug Fix | Infrastructure]
- **Goal:** [concise statement of capability/fix/improvement]
- **Boundaries:** [what is in scope]
- **Exclusions:** [what is explicitly out of scope]
- **Files (Estimated):** [best guess at files - verified during execution]
- **Proof Approach:** [test type that validates goal achievement]
- **Estimated Scope:** [N files, ~M lines] (must satisfy C3: ≤2 files, ≤100 LOC, ≤1 seam)
- **Status:** [ ] Pending
```

---

### Micro-Plan Template (Principle-Driven)

````markdown
**Catalog Item ID:** [ID]

**Type:** Principle-Driven

**Golden Doc Reference:** [document] [section] ([Principle Name])

**Files Touched:** 
- `path/to/file.py` ([N] file)

**Current State (from Step 4 review):**
~~~
# Lines X-Y in file.py contain:
[actual code from review]
# (explanation of how this violates/doesn't uphold principle)
~~~
**Minimal Change:**
- [specific change to specific lines]
- [replacement logic that upholds principle]:
~~~
[pseudocode or generic code structure]
~~~

**Executable Proof:**
- Test `test_name()` passes (validates principle)
- Existing tests still pass
- [specific validation outcome]

**Scope Check:**
- ✅ ≤2 code files ([N] file)
- ✅ ≤100 LOC (~M lines)
- ✅ ≤1 seam ([boundary name] only)
````

---

### Micro-Plan Template (Goal-Driven)

````markdown
**Catalog Item ID:** [ID]

**Type:** [Feature | Bug Fix | Infrastructure]

**Goal:** [from catalog]

**Files Touched:** 
- `path/to/file.py` ([N] file)

**Current State (from Step 4 review):**
~~~
# Lines X-Y in file.py contain:
[actual code from review]
# (explanation of current behavior)
~~~
**Minimal Change:**
- [specific change to specific lines]
- [new behavior logic]:
~~~
[pseudocode or generic code structure]
~~~

**Executable Proof:**
- Test `test_name()` passes (validates goal achievement)
- Existing tests still pass
- [specific validation outcome]

**Golden Doc Compatibility:**
- Does not violate system-vision.md invariants
- Does not violate target-architecture.md constraints

**Scope Check:**
- ✅ ≤2 code files ([N] file)
- ✅ ≤100 LOC (~M lines)
- ✅ ≤1 seam ([boundary name] only)
````

---

### Completion Proof Template

````markdown
**Completed:** [YYYY-MM-DD]

**Commit:** [hash]

**Proof Commands:**
```bash
# Unit test validation
pytest tests/path/to/test_file.py::test_name -v
# PASSED

# Regression check
pytest tests/module/ -v
# All tests PASSED

# (Optional) End-to-end validation
python -m engine.orchestration.cli run "validation entity" --lens target_lens
psql $DATABASE_URL -c "SELECT entity_name, canonical_activities FROM entities WHERE entity_name ILIKE '%validation_entity%';"
# Returns: [expected values]
```

**Output Summary:**
- All tests green
- [For Principle-Driven]: Principle [name] upheld
- [For Goal-Driven]: Goal [description] achieved
- No golden doc violations introduced
````

---

## 7. Catalog Archival Policy

The Active Catalog (`docs/progress/development-catalog.md`) contains:

- Pending items
- In-progress items
- Completed items that have dependent active items
- Completed items that are referenced by active roadmap items

Archive Catalog file:

- `docs/progress/development-catalog-archive.md`

When a catalog item:

- Is marked complete
- Has no dependent active items
- Is not referenced by any active roadmap item

It must be moved from the Active Catalog to the Archive Catalog within 24 hours.

- The Archive Catalog is append-only.
- Archived items are not modified.

---

## 8. Quick Reference

### Two Independent Workflows

**Workflow A: Catalog Item Creation (Strategic)**

- Step 1: Identify Next Focus
- Step 2: Collaborative Shaping (Interactive Q&A)
- Step 3: Catalog Validation & Persistence
- **OUTPUT:** Catalog file updated
- **SESSION:** Can be cleared after Step 3

**Workflow B: Catalog Item Execution (Tactical)**

- Step 4: Code Reality Review
- Step 5: Write Micro-Plan
- Step 5.5: Persist Approved Micro-Plan
- Step 6: Review Constraints
- Step 6.5: Reload Micro-Plan from `tmp/`
- Step 7: Execute with Proof-First
- Step 8: Execution Amendment
- Step 9: Agent Self-Validation
- Step 10: Mark Complete & Commit
- Step 11: Compounding
- **INPUT:** Catalog item ID
- **SESSION:** Starts fresh by reading catalog

---

### The 2 User Checkpoints (Workflow B Only)

- **Checkpoint 1 (Start):** Approve micro-plan (1-2 min) — between Steps 5 and 5.5
- **Checkpoint 2 (End):** Validate result (2-3 min) — between Steps 9 and 10

---

### The 9 Constraints

1. **Golden Doc Compatibility** (all work compatible; Principle-Driven must reference)
2. **Reality-Based Planning** (read actual code before planning)
3. **Scope Limits** (≤2 files, ≤100 LOC, ≤1 seam)
4. **Proof-First Validation** (test before implementation)
5. **Catalog Fidelity** (only work on catalog items)
6. **Foundation Permanence** (no temporary solutions)
7. **User Validation Required** (no autonomous completion)
8. **Collaborative Shaping Required** (Step 2 mandatory, interactive Q&A)
9. **Catalog Persistence Required** (execution reads from file, not memory)

---

### The 6 Validation Gates

1. **Golden Doc Compatibility** (upholds principle OR violates no rules)
2. **Proof Passes** (test validates principle/goal, no regressions)
3. **Diff Matches Plan** (only planned changes)
4. **Zero Assumptions** (all code exists and works)
5. **Catalog Updated** (marked complete with proof)
6. **Reality Validation** (DB truth for end-to-end work)

---

### The 5 Recovery Signals

1. **Assumption Violation** → Re-review code (return to Step 4)
2. **Scope Creep** → Create new catalog items (return to Workflow A)
3. **Proof Failures Beyond Scope** → Revert or fix regression
4. **Golden Doc Conflict** → Golden docs win, revise approach
5. **Agent Off-Piste** → Revert unauthorized changes

---

### Work Types

**Principle-Driven:**

- Fixing architectural violations
- Advancing golden doc principles
- Restoring architectural purity
- MUST reference specific golden doc section

**Goal-Driven:**

- **Feature:** New capabilities within architecture
- **Bug Fix:** Correcting existing behavior
- **Infrastructure:** Tooling, logging, dev experience
- Must be COMPATIBLE with golden docs but no explicit principle reference required

---

**End of Methodology Document**
