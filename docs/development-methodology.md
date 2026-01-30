# Development Methodology: Reality-Based Incremental Alignment

**Status:** Active Methodology
**Last Updated:** 2026-01-30
**Purpose:** Guide steady, aligned, vision-true progress in bite-sized, testable chunks

---

## Table of Contents

1. [The Problem](#1-the-problem)
2. [The Solution](#2-the-solution)
3. [Macro Structure: The Three Phases](#3-macro-structure-the-three-phases)
4. [The Audit Process](#4-the-audit-process)
5. [The Micro-Iteration Process](#5-the-micro-iteration-process)
6. [The Constraint System](#6-the-constraint-system)
7. [The Validation Gates](#7-the-validation-gates)
8. [The Decision Logic](#8-the-decision-logic)
9. [The Recovery Protocol](#9-the-recovery-protocol)
10. [Persistent State: The Catalog](#10-persistent-state-the-catalog)
11. [User Checkpoint Guidelines](#11-user-checkpoint-guidelines)
12. [Getting Started](#12-getting-started)

---

## 1. The Problem

### Symptoms
- AI agents drift from plans and violate golden docs
- Plans are good but agents "go off-piste" and ignore rules
- End-to-end plans are too complex to understand and verify
- Agents plan from mental models instead of actual codebase
- Assumptions wrong → blockers everywhere → agents improvise → mess
- Code changes accumulate until unclear what's happening
- Work completed but doesn't match vision/architecture

### Root Causes
1. **Insufficient Agent Discipline:** Rules exist but agents ignore them
2. **Scope Too Large:** Changes touch too many files, cross too many boundaries
3. **Reality Disconnect:** Planning based on assumptions, not actual code
4. **Insufficient Validation:** No checkpoints to catch drift before it becomes a mess
5. **Autonomy Without Constraints:** Agents have freedom but no enforcement

### The Reset Goal
- Bite-sized changes (1-2 files max)
- Understandable at moment of decision
- Easily testable with clear pass criteria
- Creates solid foundation that never needs undoing
- Clear "next best change" at any point in time
- **User validates outcomes, not AI self-certification**

---

## 2. The Solution

### Core Principles

**Reality-Based Planning**
- Read actual code before planning
- Verify all assumptions explicitly
- Plan from what exists, not what "should" exist
- No mental models, no guessing

**Ultra-Small Work Units**
- Single file changed (max 2 files for code)
- Single architectural principle addressed
- Single function/class modified
- Single test validates the change
- Scope bounded (not time bounded)

**User-Driven Validation**
- User approves micro-plan before execution
- User validates outcome after execution
- User sign-off required to mark complete
- Agent proposes, user decides

**Foundation-First Progression**
- Fix architectural violations before adding features
- Work from catalog of violations sorted by importance
- Each completed change is permanent foundation
- Never revisit completed work

**Golden Doc Supremacy**
- `docs/system-vision.md` = immutable constitution
- `docs/architecture.md` = runtime specification
- All decisions reference golden docs explicitly
- Conflicts → golden docs always win

---

## 3. Macro Structure: The Three Phases

### Phase 1: Foundation (Architectural Integrity)

**Goal:** Fix all architectural violations from golden docs

**Source of Work:** Audit `docs/system-vision.md` Invariants 1-10
- Engine Purity (Invariant 1): No domain terms in engine code
- Lens Ownership (Invariant 2): All semantics in lens configs
- Zero Engine Changes (Invariant 3): New verticals require no engine changes
- Determinism (Invariant 4): Same inputs → same outputs
- Canonical Registry Authority (Invariant 5): All values declared
- Fail-Fast Validation (Invariant 6): Invalid contracts fail at bootstrap
- Schema-Bound LLMs (Invariant 7): Only validated output
- No Translation Layers (Invariant 8): Universal schema end-to-end
- Engine Independence (Invariant 9): Useful without specific vertical
- No Reference-Lens Exceptions (Invariant 10): No special treatment

**Completion Criteria:**
- All **Level-1 violations on the runtime path for the validation entity** resolved
- Bootstrap validation gates implemented and enforced (lens validation fails fast)
- No domain terms in engine code on validation entity's path
- All boundaries correct for validation entity flow

**Transition to Phase 2:** Blocking Level-1 violations resolved + bootstrap gates enforced

**Note:** Remaining Level-2/Level-3 violations remain cataloged and can be addressed during or after Phase 2. This prevents perfectionism paralysis and allows reaching "One Perfect Entity" validation (per system-vision.md Section 6) without fixing every violation first.

---

### Phase 2: Core Pipeline Implementation

**Goal:** Implement complete orchestration pipeline per architecture

**Source of Work:** `docs/architecture.md` Section 4.1 - Pipeline Stages

The 11 stages in canonical order:
1. Input
2. Lens Resolution and Validation
3. Planning
4. Connector Execution
5. Raw Ingestion Persistence
6. Source Extraction
7. Lens Application
8. Classification
9. Cross-Source Deduplication Grouping
10. Deterministic Merge
11. Finalization and Persistence

**Work Identification:**
- Audit each stage for implementation completeness
- Catalog missing capabilities as work items
- "One Perfect Entity" validates architecture correctness (checkpoint, not goal)
- Continue implementing until all 11 stages complete

**Critical Constraint: Explicit Lens Resolution Required**
- Validation entity work MUST use explicit lens resolution (CLI flag `--lens`, environment variable `LENS_ID`, or config)
- Dev/Test lens fallback (architecture.md 3.1) is FORBIDDEN for "One Perfect Entity" proof
- Fallback only permitted for local unit tests, never integration/validation work
- This preserves fail-fast validation (system-vision.md Invariant 6) while allowing development convenience

**Completion Criteria:**
- All 11 pipeline stages implemented and working
- One perfect entity flows end-to-end correctly
- Use case test passes (entity data correct in database)
- All pipeline tests pass

**Transition to Phase 3:** Complete pipeline operational + validation entity correct

---

### Phase 3: System Expansion

**Goal:** Add more connectors, lenses, coverage

**Source of Work:** Business/product priorities (not in golden docs)
- More connectors for existing verticals
- New vertical lenses
- More edge cases and entities
- Performance optimization
- Operational improvements

**Note:** Foundation and pipeline never change in Phase 3

---

## 4. The Audit Process

**Purpose:** Systematically catalog all gaps between current codebase and golden docs

### Step 1: Identify Architectural Principles

Read `docs/system-vision.md` and `docs/architecture.md` and extract testable principles:
- Engine Purity (Invariant 1): No domain terms in engine code
- Extraction Boundary (architecture.md 4.2): Extractors emit only primitives
- Lens Ownership (Invariant 2): All semantics in lens configs
- Determinism (Invariant 4): Same inputs → same outputs
- Context Propagation (architecture.md 3.7): ExecutionContext threaded through pipeline
- etc.

### Step 2: Audit Each Principle Against Codebase

For each principle, search codebase for violations:

**Example - Engine Purity:**
```bash
# Search for domain terms
grep -r "padel\|tennis\|wine\|restaurant" engine/

# Review each match:
# - Is it a violation? (hardcoded domain logic)
# - Or acceptable? (test fixture, comment example)
```

**Example - Extraction Boundary:**
```bash
# Read each extractor file
# Check: Does it emit canonical_* fields? (violation)
# Check: Does it emit only primitives + raw_observations? (correct)
```

### Step 3: Catalog Violations

Create structured catalog entries:

```markdown
### EP-001: Engine Purity Violation
- **Principle:** Engine Purity (Invariant 1)
- **Location:** `engine/extraction/entity_classifier.py:102-120`
- **Description:** Hardcoded domain terms "padel", "league", "club" in classification logic
- **Evidence:** Lines 102-120 contain domain-specific category checks
- **Foundational Level:** 1 (Critical - architectural boundary)
- **Estimated Scope:** Single file, ~20 lines
```

### Step 4: Sort by Foundational Level

**Level 1 (Critical):** Architectural boundaries violated
- Engine purity violations
- Extraction boundary violations
- Missing ExecutionContext propagation
- Hardcoded domain logic

**Level 2 (Important):** Missing contracts/interfaces
- Missing function parameters
- Missing validation gates
- Incomplete error handling

**Level 3 (Feature):** Missing functionality
- Unimplemented pipeline stages
- Missing module extractors
- Incomplete lens configs

### Step 5: Write to Catalog File

Save to `docs/progress/audit-catalog.md` (see Section 10 for format)

---

## 5. The Micro-Iteration Process

**Purpose:** Execute one ultra-small, testable change with strict reality-checking

### The Process: 7 Steps with User Checkpoints

---

#### Step 1: Select Next Item (Phase-Aware)

**In Phase 1 (Foundation):**
- Pick highest-priority item from violation catalog
- Sort by: Foundational Level (1 = critical) → Order added
- Goal: Fix architectural violations

**In Phase 2 (Use Case Enablement):**
- Pick based on what use case entity needs next
- Logic: "What's blocking the entity from flowing to the next pipeline stage?"
- Still consult catalog if new violations discovered

**In Phase 3 (Expansion):**
- Pick based on coverage gaps
- More entities, more edge cases, more verticals
- Foundation never changes

**Phase Transition Criteria:**
- Phase 1 → Phase 2: Catalog empty + architectural tests pass
- Phase 2 → Phase 3: Complete pipeline + use case test passes

---

#### Step 2: Code Reality Audit (MANDATORY)

**Before planning anything, read the actual code:**

1. **Identify files that will be touched**
   - Primary file being changed
   - Files that import/depend on it
   - Test files

2. **Read ALL files using Read tool**
   ```
   Read: engine/extraction/entity_classifier.py
   Read: engine/extraction/base.py  # (if it imports classifier)
   Read: tests/engine/extraction/test_entity_classifier.py
   ```

3. **Document actual structure**
   - Function signatures: `def classify_entity(data: dict) -> str:`
   - Class definitions: `class EntityClassifier:`
   - Dependencies: `from engine.lenses import query_lens`
   - Current implementation behavior

4. **List explicit assumptions**
   - "Function X takes parameters Y and Z"
   - "Function X returns a string, not a dict"
   - "File A imports File B"

5. **Verify assumptions by reading code**
   - Never guess
   - Never assume based on naming
   - Never use mental model of "how it should be"

**Red Flag:** If you find yourself saying "I assume..." → STOP and read the code

---

#### Step 3: Write Micro-Plan

Create a **half-page maximum** plan that:

**Header:**
- Catalog Item ID: EP-001
- Golden Doc Reference: system-vision.md Invariant 1 (Engine Purity)
- Files Touched: `engine/extraction/entity_classifier.py` (1 file)

**Current State (from Step 2 audit):**
```python
# Lines 102-120 in entity_classifier.py contain:
if "padel" in raw_categories or "tennis" in raw_categories:
    return "place"
# (hardcoded domain terms)
```

**Change:**
- Remove domain-specific terms from lines 102-120
- Replace with structural classification:
  ```python
  if has_street_address and has_latitude:
      return "place"
  ```

**Pass Criteria:**
- Test `test_classifier_contains_no_domain_literals()` passes
- Existing entity classification tests still pass
- Powerleague entity still classifies as "place"

**Estimated Scope:** 20 lines changed, 1 file

---

#### 🛑 USER CHECKPOINT 1: Approve Micro-Plan (1-2 min)

**Agent presents:**
"Next item: [ID]. Will change [specific function in file]. Here's the micro-plan. Approve?"

**User reviews:**
- Is scope small enough? (1-2 files)
- Is golden doc reference correct?
- Does current state match reality?
- Is pass criteria clear?

**User decides:**
- ✅ Approve → proceed
- 🔄 Revise → agent updates plan
- ❌ Reject → agent selects different item

---

#### Step 4: Review Constraints (Agent Self-Check)

Before executing, verify all constraints satisfied:

- ✅ Single architectural principle addressed
- ✅ All assumptions verified from actual code (not guessed)
- ✅ Pass criteria references golden docs explicitly
- ✅ No more than one "seam" crossed (one architectural boundary)
- ✅ Maximum 2 files changed (excluding tests)
- ✅ Maximum 100 lines of code changed
- ✅ Test-first approach planned

**If any constraint violated → return to Step 3, revise plan**

---

#### Step 5: Execute with TDD

**Red → Green → Refactor:**

1. **Write failing test FIRST**
   ```python
   def test_classifier_contains_no_domain_literals():
       """Validates Invariant 1: Engine Purity"""
       source = inspect.getsource(entity_classifier)
       forbidden = ["padel", "tennis", "wine", "restaurant"]
       for term in forbidden:
           assert term.lower() not in source.lower()
   ```

2. **Confirm test fails (RED)**
   ```bash
   pytest tests/engine/extraction/test_entity_classifier.py::test_classifier_contains_no_domain_literals
   # Should fail with current code
   ```

3. **Implement minimum code to pass (GREEN)**
   - Remove hardcoded domain terms
   - Replace with structural logic
   - Run test until it passes

4. **Refactor while keeping tests green**
   - Improve code quality
   - Maintain test passing

5. **Run full test suite**
   ```bash
   pytest engine/extraction/
   # Ensure no regressions
   ```

**Key Rule:** If at ANY point assumptions were wrong or blockers appear → STOP, return to Step 2 (Code Reality Audit)

---

#### Step 6: Validate Against Golden Docs

Before marking complete:

1. **Re-read relevant section of golden docs**
   - system-vision.md Invariant 1
   - "The engine contains zero domain knowledge"

2. **Manual verification**
   - Question: "Does this change uphold the principle?"
   - Evidence: Point to specific code demonstrating compliance
   - If unsure → it fails

3. **Check test explicitly validates golden doc compliance**
   - Test references the principle (comment or test name)
   - Test would catch regression

4. **Ensure no new violations introduced elsewhere**
   - Review all changed files
   - Check for unintended consequences

---

#### 🛑 USER CHECKPOINT 2: Validate Result (2-3 min)

**Agent presents:**
"Complete. Changed [files]. Test passes: [test name]. All gates passed. Review?"

**User validates:**
1. **Look at diff:** Review actual changes
   ```bash
   git diff engine/extraction/entity_classifier.py
   ```

2. **Run tests yourself:**
   ```bash
   pytest tests/engine/extraction/test_entity_classifier.py -v
   ```

3. **Verify scope:** Only planned files changed?

4. **Check golden doc alignment:** Does it uphold the principle?

**User decides:**
- ✅ Approve → proceed to Step 7
- 🔄 Revise → agent fixes issues
- ❌ Reject → revert changes, return to planning

---

#### Step 7: Mark Complete & Commit

**Only after user approval:**

1. **Update catalog**
   - Mark item as `[x]` complete
   - Add completion date + commit hash
   - Update "Last Updated" timestamp

2. **Commit with conventional commit message**
   ```bash
   git add engine/extraction/entity_classifier.py tests/engine/extraction/test_entity_classifier.py

   git commit -m "fix(extraction): remove domain terms from classifier (Invariant 1)

   Replaced hardcoded domain-specific category checks with structural
   classification rules. Classifier now uses only universal type indicators
   and structural field checks, preserving engine purity.

   Validates: system-vision.md Invariant 1 (Engine Purity)
   Catalog Item: EP-001

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

3. **Foundation is now solid**
   - Never needs to be revisited
   - Permanent architectural improvement

4. **Return to Step 1**
   - Select next item from catalog
   - Repeat process

---

## 6. The Constraint System

**Purpose:** Hard rules that prevent agents from drifting off-piste

These constraints are **MANDATORY** and **CANNOT BE VIOLATED**.

---

### C1: Golden Doc Supremacy

- Every change MUST reference a specific section of `system-vision.md` or `architecture.md`
- If golden docs don't support it → change is invalid
- When in doubt → read golden docs, don't assume
- Conflicts → golden docs always win

**Enforcement:** Every micro-plan must have "Golden Doc Reference" field

---

### C2: Reality-Based Planning

- MUST read actual code files before planning (Step 2 mandatory)
- NO assumptions about code structure
- If assumption needed → verify by reading code
- Mental models are forbidden

**Enforcement:** Step 2 audit results must be included in micro-plan

---

### C3: Scope Limits

- **Maximum 2 files changed** (excluding tests)
- **Maximum 1 architectural seam crossed**
- **Maximum 100 lines of code changed**
- If scope grows → split into multiple catalog items

**Enforcement:** User checkpoint 1 verifies scope before approval

---

### C4: Test-First Validation

- Test must be written BEFORE implementation
- Test must explicitly validate golden doc compliance
- Test must reference specific invariant/principle
- No test = no implementation

**Enforcement:** Step 5 requires RED test before GREEN implementation

---

### C5: Catalog Fidelity

- Only work on items in the catalog
- No improvisation or "while we're here" changes
- Discovered violations → add to catalog, don't fix immediately
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

**Enforcement:** Step 7 only executes after user checkpoint 2 approval

---

### C8: Extraction Helper Purity

- Extraction helpers may ONLY perform: validation, normalization, provenance tracking
- NEVER: interpretation, classification, semantic detection, or domain logic
- Contract test: extractor output contains ONLY schema primitives + raw_observations
- Any helper that produces `canonical_*` fields or `modules` = violation
- Structural signals = counts, presence of schema fields, data completeness (never interpret meaning)

**Enforcement:** Architecture.md 4.2 extraction boundary contract tests. Helpers that touch canonical dimensions or modules fail purity validation.

**Note:** Per architecture.md 8.2, acceptable extractor outputs are:
- Schema primitives: `entity_name`, `latitude`, `longitude`, `street_address`, `city`, `postcode`, `phone`, `email`, `website_url`
- Raw observations (opaque): `raw_categories`, `description`, connector-native fields
- Structural counts: `location_count`, `employee_count` (counts only, not interpretation)

---

## 7. The Validation Gates

**Purpose:** Define unambiguous criteria for "this change is solid and permanent"

Every change must pass **ALL gates** before being marked complete.

---

### Gate 1: Golden Doc Alignment

**Check:**
- Re-read the golden doc section being addressed
- Question: "Does this change uphold the stated principle?"
- Evidence: Point to specific code demonstrating compliance

**Pass Criteria:**
- Change clearly upholds the principle
- Evidence is concrete and verifiable
- If unsure → it fails

---

### Gate 2: Test Validation

**Check:**
- The golden-doc-compliance test passes (green)
- Full test suite passes (no regressions)
- Coverage >80% for changed code
- Test explicitly references the principle

**Pass Criteria:**
```bash
pytest tests/engine/extraction/ -v
# All tests pass

pytest --cov=engine/extraction --cov-report=term
# Coverage >80%
```

---

### Gate 3: Code Reality Check

**Check:**
- Changed code matches what was planned (no drift)
- No "extra" changes or improvements sneaked in
- All files touched were listed in micro-plan
- Scope stayed within limits (2 files, 100 lines)

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
python -m pytest tests/engine/extraction/test_entity_classifier.py -v
# Tests pass (proves code actually works)
```

---

### Gate 5: Catalog Updated

**Check:**
- Item marked complete `[x]` with date + commit hash
- Any discovered violations added to catalog
- Current phase updated if transition criteria met
- Next item is clear

**Pass Criteria:**
- Catalog file shows item completed
- No orphaned work discovered during implementation

---

### Gate 6: Reality Validation

**Check:**
- For code-level changes: unit tests pass (proves logic correct)
- For pipeline-level changes: integration tests pass (proves flow correct)
- For end-to-end validation: **database inspection shows correct entity data**

**Pass Criteria:**

Code-level:
```bash
pytest tests/engine/extraction/test_entity_classifier.py -v
# All tests green
```

End-to-end:
```bash
# Run validation entity through pipeline
python -m engine.orchestration.cli run "powerleague portobello edinburgh" --lens edinburgh_finds

# Inspect database - entity data must match expected values
psql $DATABASE_URL -c "
SELECT entity_name, entity_class, canonical_activities, canonical_place_types, modules
FROM entities
WHERE entity_name ILIKE '%powerleague%portobello%';"

# Expected output must match architecture requirements
# canonical_activities: ['padel'] or similar
# canonical_place_types: ['sports_facility'] or similar
# modules: {"sports_facility": {"padel_courts": {...}}} or similar
```

**Critical Rule (system-vision.md 6.3):**
> "The entity database is the ultimate correctness signal. Tests that pass but produce incorrect entity data constitute a failure."

If tests pass but entity data is wrong or incomplete → FAILURE

---

### Fail Fast Rule

**If ANY gate fails → do NOT proceed**

Actions:
- Fix the issue, OR
- Revert the change
- Never mark incomplete work as done

---

## 8. The Decision Logic

**Purpose:** Explicit algorithm for "what's the next thing to work on?" - no ambiguity

### The Algorithm

```
1. Read docs/progress/audit-catalog.md

2. Check "Current Phase" field

3. IF Phase = "Foundation":
   a. Find first unchecked [ ] item in "Critical (Level 1)" section
   b. IF none exist:
      - Find first unchecked [ ] item in "Important (Level 2)" section
      - IF none exist:
        - Run architectural compliance test suite
        - IF all pass:
          * Update Phase to "Use Case Enablement"
          * GO TO step 2
        - ELSE:
          * Catalog the failing tests as new violations
          * GO TO step 3
   c. RETURN: Selected item

4. IF Phase = "Use Case Enablement":
   a. Check architecture.md Section 4.1 (11 pipeline stages)
   b. Identify which stage is incomplete or blocking
   c. Check catalog for existing item addressing that stage
   d. IF exists: RETURN that item
   e. IF not exists:
      - Create new catalog item for that stage
      - RETURN: Selected item

5. IF Phase = "Expansion":
   a. Identify coverage gaps (entities, edge cases, verticals)
   b. Create catalog item for next gap
   c. RETURN: Selected item
```

**Key Property:** No human judgment required. Any agent can run this algorithm and get the same answer.

---

## 9. The Recovery Protocol

**Purpose:** Define what to do when things go wrong

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
2. Return to Step 2 (Code Reality Audit)
3. Update understanding of actual code
4. Revise micro-plan based on reality, OR
5. Split into smaller item if scope too large

---

#### Signal 2: Scope Creep

**Symptoms:**
- Change touches more than 2 files (excluding tests)
- Discovers additional violations or gaps
- Requires crossing more than one architectural seam
- Requires more than 100 lines of code changed

**Action:**
1. **STOP.**
2. Mark current item as "blocked" or "needs split"
3. Create new catalog items for discovered work
4. Choose smaller scope OR address blocker first
5. Return to Step 1

---

#### Signal 3: Test Failures Beyond Scope

**Symptoms:**
- Tests failing in unrelated parts of codebase
- Regression failures not anticipated in plan
- Cannot make tests pass without additional changes

**Action:**
1. **STOP.** Assess blast radius.
2. Either:
   - **(A)** Add regression fix to current item if small (<10 lines)
   - **(B)** Revert changes, create new catalog item for regression, fix that first
3. Return to Step 1

---

#### Signal 4: Golden Doc Conflict

**Symptoms:**
- Implementation conflicts with system-vision.md or architecture.md
- Cannot satisfy both the plan and golden docs
- Architectural principle being violated

**Action:**
1. **STOP immediately.** Golden docs win.
2. Revert changes
3. Re-read golden docs carefully
4. Revise approach to align with architecture
5. Update plan
6. Return to Step 1

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
4. **Update Catalog** - Add newly discovered work as separate items
5. **Revise Understanding** - Re-audit code reality if assumptions were wrong
6. **Choose Smaller Scope** - Split catalog item if too large
7. **Restart** - Return to Step 1 (Select Next Item) with updated catalog

---

### Prevention

- Every detection signal teaches us to write better micro-plans
- Update catalog immediately when new work discovered
- Never skip Code Reality Audit (Step 2)
- User checkpoints catch drift early before it becomes mess

---

## 10. Persistent State: The Catalog

**Purpose:** Living document that tracks progress across sessions

**Location:** `docs/progress/audit-catalog.md`

---

### Catalog Structure

```markdown
# Architectural Audit Catalog

**Current Phase:** Foundation (Phase 1)
**Use Case:** Powerleague Portobello (when in Phase 2+)
**Last Updated:** 2026-01-30

---

## Phase 1: Foundation Violations

### Critical (Level 1) - Architectural Boundaries

- [ ] EP-001: Engine Purity - entity_classifier.py:102-120
  - **Principle:** Engine Purity (Invariant 1)
  - **Location:** `engine/extraction/entity_classifier.py:102-120`
  - **Description:** Hardcoded domain terms "padel", "league", "club"
  - **Estimated Scope:** 1 file, ~20 lines

- [ ] EB-001: Extraction Boundary - serper_extractor.py emits canonical_activities
  - **Principle:** Extraction Boundary (architecture.md 4.2)
  - **Location:** `engine/ingestion/connectors/serper_extractor.py:45-60`
  - **Description:** Extractor directly emits canonical dimensions (should only emit primitives)
  - **Estimated Scope:** 1 file, ~15 lines

- [x] ~~EP-002: Engine Purity - orchestrator had hardcoded "padel"~~
  - **Completed:** 2026-01-29
  - **Commit:** abc123def
  - **Proof:** `pytest tests/engine/orchestration/test_purity.py::test_no_domain_literals -v` passed
  - **Note:** Replaced hardcoded term with lens-driven vocabulary lookup

### Important (Level 2) - Missing Contracts

- [ ] MC-001: ExecutionContext not threaded through extractors
  - **Principle:** Context Propagation (architecture.md 3.7)
  - **Location:** `engine/extraction/extractors/*.py` (6 files)
  - **Description:** Extractors don't accept ctx parameter
  - **Estimated Scope:** 6 files, signature changes only

---

## Phase 2: Pipeline Implementation

(Populated when Phase 1 complete)

- [ ] Stage 3 incomplete: Planning stage missing query feature extraction
- [ ] Stage 7 incomplete: Lens Application not fully wired
- [ ] Stage 10 incomplete: Deterministic Merge not implemented

---

## Notes

- Items are worked in order (top to bottom within each level)
- Discovered violations added to appropriate section
- Completed items marked with [x] and moved to bottom of section
- **Catalog is the ONLY source of truth for progress**
- Every completed item MUST include executable proof (test, CLI run, or DB inspection)
- Catalog updated after every micro-iteration

```

---

### Usage Across Sessions

**Starting new session:**
1. Read `docs/progress/audit-catalog.md`
2. Check "Current Phase" field
3. Run Decision Logic (Section 8) to find next item
4. Begin micro-iteration

**After completing item:**
1. Mark `[x]` complete
2. Add completion date + commit hash + **executable proof**
3. Update "Last Updated" timestamp
4. Push changes to catalog file

**Executable Proof Required (per system-vision.md 6.3):**
- Code-level: Test name that passed (`test_classifier_purity`)
- Pipeline-level: Integration test that passed
- End-to-end: Database query showing correct entity data
- No item marked complete without concrete proof documented

**Discovering new violation:**
1. Add new catalog item immediately
2. Sort into appropriate foundational level
3. Continue with current item (don't fix new violation immediately)

---

## 11. User Checkpoint Guidelines

**Purpose:** Minimize interruption while maintaining control

### Checkpoint 1: Approve Micro-Plan (Start)

**Frequency:** Once per micro-iteration (start)

**Time Investment:** 1-2 minutes

**What User Reviews:**
- Catalog item ID and golden doc reference
- Current state (actual code from audit)
- Planned change (specific function/file)
- Pass criteria (test name)
- Scope (files touched, lines changed)

**Quick Approval Checklist:**
- ✅ Scope small? (1-2 files)
- ✅ Golden doc reference clear?
- ✅ Current state looks accurate?
- ✅ Pass criteria unambiguous?
- ✅ Feels like "one thing"?

**Decision:**
- ✅ Approve → agent proceeds
- 🔄 Revise → "make scope smaller" or "re-audit this file"
- ❌ Reject → "select different item"

---

### Checkpoint 2: Validate Result (End)

**Frequency:** Once per micro-iteration (end)

**Time Investment:** 2-3 minutes

**What User Reviews:**
1. **Diff review:**
   ```bash
   git diff engine/extraction/entity_classifier.py
   ```
   - Only planned files changed?
   - Changes match what was described?

2. **Run tests yourself:**
   ```bash
   pytest tests/engine/extraction/test_entity_classifier.py -v
   ```
   - Do tests actually pass?

3. **Spot check:** Does change uphold golden doc principle?

**Quick Validation Checklist:**
- ✅ Only planned files touched?
- ✅ Tests pass when I run them?
- ✅ No "extra" changes snuck in?
- ✅ Upholds golden doc principle?

**Decision:**
- ✅ Approve → agent commits and marks complete
- 🔄 Revise → "remove this extra change" or "add this test case"
- ❌ Reject → "revert, this doesn't match plan"

---

### Total User Time Per Iteration

**Per micro-iteration:** ~5 minutes (1-2 min start + 2-3 min end)

**If agent drifts:** Only 1-2 files affected, easy to spot and revert

**Benefit:** User has control without constant interruption

---

## 12. Getting Started

**Purpose:** Practical first steps to begin using this methodology

---

### Step 1: Read the Golden Docs

**Essential reading (must read before starting):**
- `docs/system-vision.md` - The immutable constitution (30 min)
- `docs/architecture.md` - Runtime specification (45 min)

**Purpose:** Understand what you're building toward

---

### Step 2: Run Initial Audit (Foundation)

**Audit system-vision.md Invariants 1-10:**

```bash
# Example: Audit Engine Purity (Invariant 1)
grep -r "padel\|tennis\|wine\|restaurant" engine/

# Review each match, catalog violations
```

**Create catalog file:**
```bash
# Create catalog
touch docs/progress/audit-catalog.md

# Use template from Section 10
# Fill in violations discovered
```

**Estimated Time:** 2-3 hours for initial audit

---

### Step 3: Select First Item

**Run Decision Logic (Section 8):**
1. Read catalog
2. Current Phase = "Foundation"
3. Find first Level 1 (Critical) item
4. That's your next work item

---

### Step 4: Execute First Micro-Iteration

**Follow Section 5 (Micro-Iteration Process):**
1. Select next item (Step 1) ✅
2. Code Reality Audit (Step 2) - read actual files
3. Write Micro-Plan (Step 3) - half page max
4. 🛑 **USER CHECKPOINT 1:** Approve plan
5. Review Constraints (Step 4)
6. Execute with TDD (Step 5)
7. Validate Against Golden Docs (Step 6)
8. 🛑 **USER CHECKPOINT 2:** Validate result
9. Mark Complete & Commit (Step 7)

---

### Step 5: Repeat

**After first item complete:**
1. Catalog updated
2. Commit pushed
3. Foundation is now solid
4. Return to Step 3 (Select First Item)
5. Repeat

**You're now in the rhythm.**

---

### Common First Items

**Typical Level 1 violations found in initial audit:**
- Engine Purity: Remove hardcoded domain terms from classifier
- Extraction Boundary: Fix extractors emitting canonical dimensions
- Context Propagation: Thread ExecutionContext through pipeline
- Fail-Fast Validation: Add lens validation at bootstrap

**Start with the first one in catalog, not the "easiest" one.**

---

## Appendix: Quick Reference

### The 7-Step Process

1. **Select Next Item** (Use Decision Logic)
2. **Code Reality Audit** (Read actual files, verify assumptions)
3. **Write Micro-Plan** (Half page, golden doc reference, pass criteria)
4. **Review Constraints** (Check all 8 constraints satisfied)
5. **Execute with TDD** (RED → GREEN → Refactor)
6. **Validate Against Golden Docs** (Manual verification)
7. **Mark Complete & Commit** (After user approval only)

### The 2 User Checkpoints

- **Checkpoint 1 (Start):** Approve micro-plan (1-2 min)
- **Checkpoint 2 (End):** Validate result (2-3 min)

### The 8 Constraints

1. Golden Doc Supremacy
2. Reality-Based Planning
3. Scope Limits (2 files, 100 lines)
4. Test-First Validation
5. Catalog Fidelity
6. Foundation Permanence
7. User Validation Required
8. Extraction Helper Purity (validation/normalization only, never interpretation)

### The 6 Validation Gates

1. Golden Doc Alignment
2. Test Validation
3. Code Reality Check
4. Zero Assumptions
5. Catalog Updated
6. Reality Validation (DB inspection for end-to-end work)

### The 5 Recovery Signals

1. Assumption Violation → Re-audit code
2. Scope Creep → Split into smaller items
3. Test Failures → Revert or fix regression
4. Golden Doc Conflict → Golden docs win, revise approach
5. Agent Off-Piste → Revert unauthorized changes

---

## Document Maintenance

This methodology document is itself a living artifact.

**When to update:**
- Constraints prove insufficient → add new constraint
- Recovery signals missed → add new detection signal
- Process breaks down → revise process
- Successful patterns emerge → codify them

**How to update:**
1. Identify problem with methodology
2. Propose change in catalog as special item
3. Discuss with user
4. Update document
5. Commit with clear reasoning

**This document exists to enable steady progress. If it's not working, fix it.**

---

**End of Methodology Document**
