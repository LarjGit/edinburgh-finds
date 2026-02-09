# AI Operating Rules

This document defines mandatory behavior for AI agents that plan or modify this repository.

It exists to ensure architectural integrity, repo-grounded planning, and predictable evolution.
It does not define system architecture or domain behavior — those are governed by
`docs/system-vision.md` and `docs/target-architecture.md`.

---

## 1. Architectural Authority

- `docs/system-vision.md` is the architectural constitution.
- `docs/target-architecture.md` defines the executable runtime model.
- These documents are authoritative and must not be weakened or bypassed.

---

## 2. Repo-Grounded Planning (Non-Negotiable)

When writing plans:

- You MUST verify that every function, method, class, or data contract referenced
  actually exists in the current codebase.
- You MUST NOT invent APIs, methods, or interfaces to satisfy a plan.

If a required seam does not exist:
- You must STOP and revise the plan to introduce **one explicit, bounded adapter**
  consistent with the architecture.
- You may not proceed with implementation until the plan reflects reality.

Plans that assume non-existent symbols are invalid.

---

## 3. No Off-Plan Improvisation

- If implementation reveals a false assumption in the plan, you must STOP.
- Produce a plan correction or patch.
- Do not "hack forward", refactor opportunistically, or invent shortcuts.

---

## 4. Lens Boundary Discipline

- Lens loading and validation occurs only at bootstrap boundaries.
- Runtime components must consume compiled, immutable lens contracts only.
- Engine code must never reach into lens filesystem, YAML, or loader internals.

If a plan requires violating this boundary, it must be redesigned.

---

## 5. Determinism and Purity

- Engine code must remain domain-blind.
- Domain semantics belong exclusively in lens contracts.
- Determinism and idempotency must be preserved at every step.

Plans that compromise these invariants are invalid.

---

## 6. Planning Scope Discipline

- Plans must be small (max 3 tasks).
- Each plan must have a clear STOP point.
- Each task must be tied to a concrete validation signal (test or artifact).

---

## 7. Priority of Failure

- Explicit failure is always preferred to silent fallback.
- If ambiguity exists, surface it rather than guessing.

---

These rules exist to protect long-term architectural integrity.
They are not optional.
