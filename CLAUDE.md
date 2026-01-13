# Instructions for Claude Code

## Conductor Workflow System

This project uses a strict, file-based project management system in `conductor/`. The complete workflow is documented in `conductor/workflow.md`.

## Session Startup Protocol

On first interaction each session, automatically execute:

1. **Read `conductor/tracks.md`** - Identify active tracks
2. **Read `conductor/tech-stack.md`** - Load current architecture
3. **Read `conductor/product.md`** - Understand product vision
4. **If active track exists:** Read `conductor/tracks/<track_id>/plan.md`
5. **Report status** - Tell user what track is active and next task

## Project Context

**Product:** Hyper-local directory platform for Edinburgh, starting with Padel
**Vision:** Connect enthusiasts with venues, coaches, retailers, clubs, events
**Monetization:** Business subscriptions/advertising
**Launch Strategy:** Single niche (Padel) → expand to other hobbies

**Tech Stack:**
- Frontend: Next.js/React/TypeScript, Tailwind CSS, shadcn/ui
- Backend: Next.js API Routes, Prisma 5 (pinned for SQLite stability)
- Database: SQLite (dev) → Supabase PostgreSQL (production)
- Data Engine: Python with Pydantic validation

**Design Principles:**
- Niche-agnostic, premium aesthetic
- "Local Expert" tone - warm, helpful, authoritative
- Progressive disclosure UX
- Mobile-first responsive design

## Working on Tasks

Follow the TDD workflow in `conductor/workflow.md`:

### Standard Task Workflow (10 Steps)

1. **Select Task** - Choose next `[ ]` task from plan.md
2. **Mark In Progress** - Change `[ ]` to `[~]` in plan.md
3. **Write Failing Tests** - Red phase of TDD
4. **Implement to Pass** - Green phase of TDD
5. **Refactor** - Improve code with test safety net
6. **Verify Coverage** - Target >80%
7. **Document Deviations** - Update tech-stack.md if needed
8. **Commit Code** - With clear message
9. **Attach Git Note** - Task summary with file list
10. **Update Plan** - Mark `[x]` with commit SHA (first 7 chars)
11. **Commit Plan Update** - `conductor(plan): Mark task 'X' as complete`

### Phase Completion Protocol

When a phase ends, execute the full verification protocol:

1. Announce phase completion
2. Ensure test coverage for all phase changes
3. Run automated tests (announce command first)
4. Propose detailed manual verification plan
5. **AWAIT USER CONFIRMATION** - Do not proceed without explicit "yes"
6. Create checkpoint commit
7. Attach verification report as git note
8. Update plan.md with checkpoint SHA
9. Commit plan update: `conductor(plan): Mark phase 'X' as complete`

## Critical Rules

### Code Without Plan = ❌ FORBIDDEN

- **NEVER write features without an active `plan.md`** in `conductor/tracks/<track_id>/`
- If no track exists and user requests work, say: "I need to create a track first. What should we call it?"

### Other Non-Negotiables

- ✅ **TDD Always** - Write failing tests before implementation
- ✅ **Sequential Phases** - Complete Phase N before starting Phase N+1
- ✅ **Tech Stack Sync** - Update `tech-stack.md` BEFORE architectural changes
- ✅ **Non-Interactive Commands** - Use `CI=true` for test runners
- ✅ **Git Notes Audit Trail** - Attach notes to task and checkpoint commits
- ✅ **Quality Gates** - See workflow.md for complete checklist

## Common User Requests

### "Start next task"
→ Read plan.md, find next `[ ]`, mark `[~]`, begin TDD workflow

### "Create new track for [feature]"
→ Create `conductor/tracks/<track_id>/` folder with `plan.md` and optional `spec.md`

### "What's the status?"
→ Read tracks.md and active plan.md, report progress with completion %

### "Follow conductor workflow"
→ Re-read workflow.md and ensure strict adherence

### "Update tech stack"
→ Read current tech-stack.md, make updates, commit with explanation note

## When Creating New Tracks

1. **Ask for track name** - e.g., "listing_detail_pages"
2. **Create folder** - `conductor/tracks/<track_id>/`
3. **Create plan.md** - Include:
   - Track description
   - Phases with tasks (use `[ ]` for pending)
   - Success criteria
4. **Add to tracks.md** - Create entry with link
5. **Optional:** Create spec.md for detailed requirements

## Testing Requirements

- **Unit tests:** Every module must have tests
- **Coverage:** Target >80% for new code
- **Test files:** Match naming convention of existing tests
- **Commands:** Check workflow.md for project-specific test commands

## Git Commit Format

```
<type>(<scope>): <description>

[optional body]
```

**Types:** feat, fix, docs, style, refactor, test, chore

**Examples:**
- `feat(listings): Add detail page with venue attributes`
- `fix(prisma): Resolve connection pooling issue`
- `test(search): Add integration tests for filters`
- `conductor(plan): Mark task 'Create search API' as complete`
- `conductor(checkpoint): Checkpoint end of Phase 2`

## Quality Gates (Before Task Completion)

- [ ] All tests pass
- [ ] Coverage >80%
- [ ] Follows code style guides (see `conductor/code_styleguides/`)
- [ ] Public functions documented
- [ ] Type safety enforced
- [ ] No linting errors
- [ ] Works on mobile (if applicable)
- [ ] No security vulnerabilities

## File Structure Reference

```
conductor/
├── product.md              # Product vision and strategy
├── product-guidelines.md   # Design principles and UX
├── tech-stack.md          # Current architecture (SOURCE OF TRUTH)
├── workflow.md            # Complete TDD workflow (READ THIS)
├── tracks.md              # Master track list
├── tracks/
│   └── <track_id>/
│       ├── plan.md        # Active work buffer
│       └── spec.md        # Detailed requirements (optional)
├── archive/               # Completed tracks
└── code_styleguides/      # Language-specific style guides
```

## Important Notes

- **The plan is the source of truth** - Always sync plan.md with reality
- **Documentation matters** - Keep tech-stack.md current with actual code
- **User experience first** - Every decision prioritizes UX
- **Don't over-engineer** - Implement only what's needed
- **Test-driven development** - Red → Green → Refactor cycle

## Emergency Overrides

If the user explicitly says "skip the workflow" or "just do it quickly", you may bypass the formal process for trivial changes (typos, comments, minor tweaks). For anything substantive, politely remind them of the workflow benefits and ask if they want to proceed formally.

---

**Version:** 1.0
**Last Updated:** 2026-01-13
**For Questions:** See conductor/workflow.md for detailed protocols
