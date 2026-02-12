# Development Methodology — Reality-Based Incremental Alignment

**Status:** Active Methodology  
**Last Updated:** 2026-02-11  
**Purpose:** Define the invariant execution discipline for how work is planned, implemented, validated, and proven — independent of what direction is currently chosen.

---

## Related Documents

- **CLAUDE.md:** Project overview, architecture quick reference, commands, reading paths  
- **docs/system-vision.md:** Architectural constitution (10 immutable invariants)  
- **docs/target-architecture.md:** Runtime execution pipeline specification (11 stages)  
- **docs/process/development-roadmap.md:** Strategic intent for what we are choosing to pursue (replaceable)  
- **docs/progress/development-catalog.md:** Execution ledger (items + completion proofs)  
- **docs/progress/lessons-learned.md:** Patterns, pitfalls, doc clarifications (institutional learning)

**Boundary Rule**

- This document governs **HOW** work is executed.  
- Direction is informed by the Development Roadmap and confirmed by user judgment.  
- The Development Catalog is a ledger of scoped work items and proofs (no strategy).

---

## Table of Contents

1. Purpose and Failure Modes
2. Core Principles
3. Work Discovery
4. Micro-Iteration Process (Step 1 → Step 1b → Steps 2-8, with 2 checkpoints)
5. Constraint System (C1–C9)
6. Validation Gates (G1–G6)
7. Recovery Protocol
8. Persistent State Rules
9. Compounding (Captured in Lessons Learned)
10. Templates

---

## 1. Purpose and Failure Modes

### What this methodology prevents
- Agent drift from golden docs  
- Large, unreviewable changes  
- Planning based on assumptions rather than code  
- “Tests pass” despite incorrect entity reality  
- Improvisation (“while we’re here”)

### Operating goal
Deliver progress in tiny, verifiable increments where:

- assumptions are proven by reading code  
- changes are scoped and testable  
- the user validates outcomes  
- correctness is grounded in executable proof (and DB truth where applicable)

---

## 2. Core Principles

### Reality-Based Planning
- Read the real code before planning  
- Verify all assumptions explicitly  
- No “mental models” of how the repo works

### Ultra-Small Work Units
- ≤2 code files changed (tests excluded)  
- ≤100 LOC changed (tests excluded)  
- ≤1 architectural seam crossed  
- One item, one principle, one proof

### User-Driven Validation
- User approves micro-plan before implementation  
- User validates result before completion is recorded

### Golden Doc Supremacy
- `system-vision.md` and `target-architecture.md` are authoritative  
- Conflicts → golden docs win

### Permanent Foundations
- No temporary scaffolding  
- Completed work should not require revisiting

---

## 3. Work Discovery

**Purpose:** Identify gaps between code and golden docs, then record them as candidate catalog items.

1. Extract testable principles from golden docs
2. Inspect the actual code against principles
3. Record discovered items as potential catalog items (do not implement during discovery)
4. Classify severity (Level 1/2/3) only as a descriptive label — not an execution rule

---

## 4. Micro-Iteration Process

**Purpose:** Execute one ultra-small, testable change with strict reality-checking and user control.

**Flow:** Step 1 → Step 1b → Step 2 → … → Step 8

### Step 1 — Identify the Next Focus

- The user chooses a direction informed by the Development Roadmap.
- The agent proposes candidate Development Catalog items derived from:
  - the roadmap intent
  - the golden documents
  - user direction
- No catalog item may exist until it has passed Step 1b and received user confirmation.
- Side quests are forbidden; one item at a time.

### Step 1b — Collaborative Shaping (REQUIRED)

**Purpose:** Convert roadmap intent into concrete catalog work through structured dialogue.

**Required behavior:**

1. The agent must ask intelligent questions before any catalog item is created.
2. Questions may offer options but must always allow free-text answers.
3. After each small batch of questions, the agent must ask:

   > "Do you want me to continue asking more questions, or should we proceed?"

4. The user may request more questions or proceed at any time.

**Output of this step:**

One OR MORE proposed Development Catalog items, each containing:
- Goal and boundaries
- Exclusions
- Proof approach
- Ordered if more than one is needed
- Rationale for splitting when more than one item is proposed

**Scope Gate:** Step 1b must produce catalog item(s) that already satisfy Constraint C3 (≤2 code files, ≤100 LOC, ≤1 seam). Items that exceed these limits must be split before Step 2 may begin.

**Decomposition Rule:** The structure and number of catalog items are decided during Step 1b; micro-plans must implement those items as-is and may not re-decompose or expand their scope.

**Rule:** Step 2 (Code Reality Review) may not begin until Step 1b is completed and the user confirms.

**Critical:** Roadmap entries are not executable work items; only Development Catalog items are executed via Steps 2–8.

### Step 2 — Code Reality Review (MANDATORY)

**Precondition:** Step 1b must be completed and user-approved before this step begins.

Before planning anything:

1. Identify the likely touched file(s) and direct dependents  
2. Read them fully  
3. Write down verified facts (signatures, behavior, imports, call sites)  
4. List assumptions explicitly and mark each as VERIFIED or UNKNOWN  
5. If anything is UNKNOWN → read more code until it is VERIFIED

**Red flag:** “I assume…” means you must stop and read.

### Step 3 — Write a Micro-Plan (½ page maximum)

Micro-plan must include:

- Catalog Item ID  
- Golden Doc Reference (exact invariant/section)  
- Files touched (expected)  
- Current state (quoted from real code)  
- Minimal change  
- Executable proof (test/CLI/DB query)  
- Scope check (≤2 code files, ≤100 LOC, ≤1 seam)

#### 🛑 USER CHECKPOINT 1 — Approve the Micro-Plan

User validates:

- scope is genuinely small  
- references are correct  
- current state is real  
- proof is unambiguous

### Step 4 — Constraint Self-Check

Confirm C1–C9 are satisfied. If not, split the work into smaller catalog items.

### Step 5 — Execute with TDD / Proof-First

- Write the proof first (test/CLI check/DB query expectation)  
- Confirm it fails with the current code (RED)  
- Implement the minimum change to pass (GREEN)  
- Refactor only within scope and plan

### Step 5a — Execution Amendment (Adaptive Re-Shaping)

**Purpose:**  
Acknowledge that reality discovered during execution may legitimately invalidate parts of an approved micro-plan without invalidating the overall goal. This step provides a disciplined path to adapt without restarting Step 1b from zero.

**Trigger Conditions (any of the following):**
- A technical assumption in the micro-plan proves false (e.g., incorrect patch point, API shape mismatch).
- New constraints emerge from Code Reality Review performed during execution.
- The original approach would violate success criteria or architectural invariants if continued.
- The goal remains unchanged and scope stays within the approved catalog item.

**Required Agent Output:**
When triggered, the agent MUST produce an **Execution Amendment Notice** containing:

1. **Broken Assumption** – what proved incorrect  
2. **New Facts** – evidence from code/reality  
3. **Proposed Delta** – minimal change to plan  
4. **Impact Statement** – confirmation that:  
   - success criteria remain satisfied  
   - scope limits (≤2 files, ≤100 LOC, ≤1 seam) remain intact  
5. **Updated Proof Strategy** (if needed)

**User Decision:**
- User may approve the amendment inline without creating a new catalog item.  
- If scope would expand beyond limits, the agent MUST return to Step 1b and create a new item.

**Guardrails:**
- ❌ No silent pivots  
- ❌ No continuation after invalidated assumptions without approval  
- ✅ Momentum preserved when goal and scope are stable  
- ✅ Full audit trail maintained via amendment notices

### Step 6 — Validate Against Golden Docs

Re-read the referenced golden section and confirm:

- the change upholds it  
- the proof would catch a regression

#### 🛑 USER CHECKPOINT 2 — Validate the Result

User validates:

- diff matches the micro-plan  
- proof runs and passes  
- no extra files/changes  
- alignment is real, not asserted

### Step 7 — Record Completion (Only after user approval)

Update `docs/progress/development-catalog.md`:

- mark item complete  
- include date + commit hash  
- include the executable proof command(s)

Commit with a message referencing:

- invariant/principle  
- catalog ID

### Step 8 — Compounding (Recorded in Lessons Learned)

After completion, capture in `docs/progress/lessons-learned.md`:

1. Pattern candidate?  
2. Doc clarity improvement?  
3. Future pitfall?

---

## 5. Constraint System (C1–C9)

C1 Golden Doc Supremacy
C2 Reality-Based Planning
C3 Scope Limits (≤2 code files, ≤100 LOC, ≤1 seam)
C4 Proof-First (no proof = no implementation)
C5 Catalog Fidelity (no side work)
C6 Foundation Permanence (production-quality only)
C7 User Validation Required (both checkpoints)
C8 Extraction Helper Purity (validate/normalize/provenance only; no semantics; no canonical dims/modules from extractors)
C9 Collaborative Shaping Required (no Development Catalog item may be created, accepted, or executed without completion of Step 1b and explicit user confirmation)

---

## 6. Validation Gates (G1–G6)

G1 Golden Doc Alignment  
G2 Proof Passes (and full suite as appropriate)  
G3 Diff Matches Plan (scope honored)  
G4 Zero Assumptions (imports, signatures, execution verified)  
G5 Catalog Updated (date/commit/proof)  
G6 Reality Validation (DB truth for end-to-end work)

**Critical Rule:** Tests passing but entity data wrong → FAILURE.

---

## 7. Recovery Protocol

**Stop signals**

- assumption violated  
- scope creep  
- proof failures outside scope  
- golden doc conflict  
- off-piste changes

**Recovery loop**

Stop → assess → revert if needed → add new catalog items → split → restart from Step 1

---

## 8. Persistent State Rules

- The Roadmap expresses strategic intent only.  
- The Methodology governs execution discipline only.  
- The Development Catalog is created from Step 1b shaping and user approval.  
- Lessons Learned stores compounding outputs.

---

## 9. Templates

### Micro-Plan Template
- Catalog ID:  
- Golden reference:  
- Files touched:  
- Current state (quoted):  
- Minimal change:  
- Proof:  
- Scope check:

### Completion Proof Template
- Completed:  
- Commit:  
- Proof command(s):  
- Output summary:  
- DB query + expected shape (if relevant)
