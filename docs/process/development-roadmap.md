# Development Roadmap

**Status:** Current Direction (replaceable at any time)  
**Last Updated:** 2026-02-11  
**Purpose:** Describe WHAT we are choosing to work toward and WHY.  
**Nature:** This document is strategic and narrative. It does not prescribe how work is executed.

---

# CURRENT ROADMAP

---

## R-01 — Converge Repository to New Governance Model (Kill Legacy Paths & Naming)

### Bootstrap Context

This transition is already in motion:

- The **Methodology** now lives at: `docs/process/development-methodology.md`
- The **Roadmap** now lives at: `docs/process/development-roadmap.md`
- The **Catalog** now lives at: `docs/progress/development-catalog.md`
- **Lessons Learned** now lives at: `docs/progress/lessons-learned.md`

R-01 completes the repo-wide convergence so **nothing operational still points at the legacy model**.

### Golden Docs (Do Not Change)

These are authoritative and out of scope for modification during R-01:

- `docs/system-vision.md` — Architectural Constitution (immutable)
- `docs/target-architecture.md` — Runtime Pipeline Specification

R-01 may update **references to these** if broken, but must not alter their contents.

### Legacy Terms / Locations to Eliminate

The repository previously referenced the older structure and naming.  
R-01’s job is to eradicate those operational references:

- **Old methodology path/name:**  
  `docs/development-methodology.md` → now `docs/process/development-methodology.md`

- **Old catalog name/path:**  
  `docs/progress/audit-catalog.md` → now `docs/progress/development-catalog.md`

- Any remaining use of **“audit”** that implies the previous governance model  
  (e.g., “audit process”, “audit catalog”) in:
  - documentation  
  - CLAUDE.md navigation  
  - code comments  
  - prompts or agent instructions  
  - tests or scripts

> Note: The word *audit* may remain only as historical narration in  
> `lessons-learned.md`; it must not appear as an active instruction system.

### Intent

Bring the entire repository into alignment with the new governance triad so that:

- **Methodology = execution discipline only** (HOW)  
- **Roadmap = strategic intent only** (WHAT/WHY)  
- **Catalog = neutral work/proof ledger only** (RECORD)

and therefore:

- Legacy filenames/paths no longer exist in operational guidance  
- Agents reliably follow: **Step 1 → Step 1b → Steps 2–8**  
- No document mixes strategy with execution law
- 
### Why

- Agents and humans drift when multiple sources disagree about “what to do next”
- Legacy links and paths break automation and onboarding
- The old “audit-era” mental model conflicts with roadmap-driven shaping
- Future work must start from a clean, unambiguous governance base

### Scope Boundaries

**In Scope — Repository-wide convergence**

1. **Reference Convergence (Documentation)**
   - Update all markdown links from:
     - `docs/development-methodology.md`  
       → `docs/process/development-methodology.md`
     - `docs/progress/audit-catalog.md`  
       → `docs/progress/development-catalog.md`
   - Update CLAUDE.md and navigation sections to include the Roadmap explicitly.

2. **Reference Convergence (Code / Comments / Prompts)**
   - Update any in-code comments referencing legacy docs/paths.
   - Update stored prompts or agent instructions using legacy naming.

3. **Semantic Convergence (Language)**
   - Replace governance-active language:
     - “audit process” → “work discovery”
     - “audit catalog” → “development catalog”
   - Align terminology with: methodology / roadmap / catalog / lessons.

4. **Catalog Neutralization**
   - Ensure the catalog reads as a **ledger**, not a plan:
     - neutral header/title wording  
     - no roadmap narrative embedded  
     - proofs and completion evidence preserved

5. **Verification**
   - Repo-wide searches confirm legacy references removed.
   - All links resolve.
   - Start-a-task flow matches: Roadmap → Step 1b → Catalog → Micro-Plan.

**Out of Scope**

- Any change to `docs/system-vision.md`
- Any change to `docs/target-architecture.md`
- Application/runtime behavior changes
- Re-auditing existing catalog items
- Restructuring internal catalog entry format

### Success Criteria

- Zero operational references remain to:
  - `docs/development-methodology.md`
  - `docs/progress/audit-catalog.md`
  - “audit catalog” as a current governance object
- CLAUDE.md navigation reflects the new triad
- Catalog remains intact as a ledger (items + proofs preserved)
- A new agent can start work without inference or ambiguity

### Proof Signals

Evidence this direction is complete:

- Repo search results:
  - `docs/development-methodology.md` → **0 matches**
  - `audit-catalog` → **0 operational matches**
- All documentation links resolve to current paths
- CLAUDE.md “Starting a task?” flow matches the methodology
- A trial run of:
  - select roadmap item  
  - Step 1b shaping  
  - create catalog item  
  - micro-plan  
  works without confusion

**Non-negotiable:**  
If any file contains legacy governance references, it must be updated or removed **before** any new feature work proceeds.

---

## R-02 — [Your Next Direction]

### Intent
(TBD)

### Why
(TBD)

### Scope Boundaries
(TBD)

### Success Criteria
(TBD)

### Proof Signals
(TBD)
