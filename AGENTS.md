# [GLOBAL RULES]
### Mermaid Diagram Standards
- **Orientation:** Always start with `graph TD` or `flowchart TD` (Top-Down). Never use `LR` unless explicitly told.
- **Quoting:** Wrap ALL display labels in double quotes `" "` to escape special characters (e.g., `Node["Label (Info)"]`).
- **Special Characters:** Never use `(`, `)`, `[`, `]`, `{`, `}`, or `-->` directly in a label; they MUST be inside double quotes.
- **Formatting:** - Use alphanumeric IDs for nodes (e.g., `Step1`, `DB_Audit`).
  - Use `<br/>` for line breaks within a node; do not use actual newlines.
- **Subgraphs:** Include `direction TD` inside every `subgraph` block to maintain vertical consistency.
- **Links:** Use labels on arrows as follows: `A -->|"Step Description"| B`.
- **Lists**: Avoid edge labels that begin with list-like patterns (e.g., 1., -, *) in Mermaid diagrams; use words or move numbering into node labels instead.

# [PROJECT CONTEXT]
# Conductor - Context-Driven Development for Claude Code

Conductor is an AI agent skill that enables **Context-Driven Development**. It transforms Claude Code into a proactive project manager that follows a strict protocol to specify, plan, and implement software features and bug fixes.

**Philosophy: Measure twice, code once.**

Instead of just writing code, Conductor ensures a consistent, high-quality lifecycle for every task: **Context → Spec & Plan → Implement**.

## How Conductor Works

Conductor treats context as a managed artifact alongside your code, transforming your repository into a single source of truth that drives every agent interaction with deep, persistent project awareness.

### Key Principles

- **Plan before you build**: Create specs and plans that guide development for new and existing codebases
- **Maintain context**: Ensure AI follows style guides, tech stack choices, and product goals
- **Iterate safely**: Review plans before code is written, keeping you firmly in the loop
- **Work as a team**: Set project-level context that becomes a shared foundation for your team

## File Structure

Conductor creates and maintains the following structure in your project:

```
conductor/
├── product.md                    # Product vision, users, goals
├── product-guidelines.md         # Brand/style guidelines
├── tech-stack.md                 # Technology choices and constraints
├── workflow.md                   # Development methodology (TDD, commits, coverage)
├── tracks.md                     # Master track list with status markers
├── code_styleguides/            # Language-specific style guides
└── tracks/                       # Individual track folders
    └── <track_id>/
        ├── spec.md              # Feature specification
        ├── plan.md              # Implementation plan with tasks
        └── metadata.json        # Track metadata
```

## User Interaction Patterns

When a user references context or plans, they're likely referring to Conductor files:

- If a user mentions a "**plan**" or asks about the plan, they are likely referring to:
  - `conductor/tracks.md` (master track list), OR
  - `conductor/tracks/<track_id>/plan.md` (specific track plan)

- If a user mentions "**the spec**" or asks about specifications, they are likely referring to:
  - `conductor/tracks/<track_id>/spec.md`

- If a user mentions "**product context**" or "**project goals**", they are likely referring to:
  - `conductor/product.md`

- If a user mentions "**tech stack**" or asks about technology choices, they are likely referring to:
  - `conductor/tech-stack.md`

- If a user mentions "**workflow**" or development process, they are likely referring to:
  - `conductor/workflow.md`

## Core Workflows

### 1. Setup (Run Once Per Project)

**User triggers**: "set up conductor", "initialize conductor", "set up the project"

**What happens**:
1. Analyze the current workspace to understand the project
2. Guide the user through creating project context documents:
   - **Product**: Define project context (users, product goals, high-level features)
   - **Product guidelines**: Define standards (prose style, brand messaging, visual identity)
   - **Tech stack**: Configure technical preferences (language, database, frameworks)
   - **Workflow**: Set team preferences (TDD, commit strategy, code coverage goals)
3. Create the conductor directory structure
4. Generate initial context files with intelligent defaults based on workspace analysis

**For existing (Brownfield) projects**:
- Analyze existing code, dependencies, and documentation
- Infer tech stack from package files, imports, and code patterns
- Suggest workflow based on existing test structure and commit history
- Preserve existing conventions while formalizing them

**For new (Greenfield) projects**:
- Start with templates and guide user through decisions
- Help establish foundational choices from scratch
- Set up best practices from the beginning

**Generated artifacts**:
- `conductor/product.md`
- `conductor/product-guidelines.md`
- `conductor/tech-stack.md`
- `conductor/workflow.md`
- `conductor/code_styleguides/`
- `conductor/tracks.md`

### 2. Create New Track (Feature or Bug)

**User triggers**: "create a new feature", "start a new track", "add [feature description]", "fix [bug description]"

**What happens**:
1. Initialize a **track** - a high-level unit of work with a unique ID
2. Generate two critical artifacts through iterative discussion:
   
   **Spec (spec.md)**: The detailed requirements
   - What are we building and why?
   - User stories and acceptance criteria
   - Success metrics
   - Technical constraints
   
   **Plan (plan.md)**: An actionable implementation roadmap
   - Organized into **phases** (major milestones)
   - Each phase contains **tasks** (concrete work items)
   - Each task may have **sub-tasks** (detailed steps)
   - Status tracking for each item (pending, in-progress, complete)
   - Checkpoints for verification at phase boundaries

3. Present the spec and plan to the user for review and approval
4. Update `conductor/tracks.md` with the new track entry

**Generated artifacts**:
- `conductor/tracks/<track_id>/spec.md`
- `conductor/tracks/<track_id>/plan.md`
- `conductor/tracks/<track_id>/metadata.json`
- Updates to `conductor/tracks.md`

### 3. Implement Track

**User triggers**: "implement the track", "start implementing", "work on [track name]", "continue implementation"

**What happens**:
1. Read the current track's `plan.md` to understand the work
2. Follow the implementation protocol:
   - **Select the next pending task** from the plan
   - **Follow the defined workflow** (e.g., TDD: Write Test → Fail → Implement → Pass)
   - **Update task status** in plan.md as work progresses
   - **Mark tasks complete** when finished
   - **Commit work** according to workflow guidelines
3. At the end of each **phase**:
   - **Announce phase completion**
   - **List changed files** in this phase
   - **Run automated tests** if available
   - **Request manual verification** from the user
   - **Create checkpoint commit** after verification
   - **Update plan.md** with checkpoint commit hash
4. Continue to next phase or complete the track

**Task completion protocol**:
- Stage the modified files
- Update plan.md to mark task as complete
- Commit with descriptive message (e.g., `conductor(plan): Mark task 'X' as complete`)

**Phase completion and verification protocol**:
1. Announce protocol start to user
2. Determine phase scope (git diff from previous checkpoint or start)
3. List all changed files in this phase
4. Run automated tests if available
5. Request manual verification from user with specific steps
6. Wait for user confirmation
7. Create checkpoint commit with clear message
8. Attach verification report using git notes
9. Update plan.md with checkpoint commit hash
10. Stage and commit the plan update

**Updated artifacts**:
- `conductor/tracks.md` (status updates)
- `conductor/tracks/<track_id>/plan.md` (task/phase status, checkpoint hashes)
- Project files (actual implementation)
- Git commits with proper messages and checkpoints

### 4. Check Status

**User triggers**: "check project status", "what's the status", "show progress", "where are we"

**What happens**:
1. Read `conductor/tracks.md` to get overview of all tracks
2. For active tracks, read their `plan.md` files
3. Present a summary showing:
   - Current phase and task
   - Overall progress (completed/total)
   - Next action needed
   - Any blockers or issues
   - Active track details

**Reads**:
- `conductor/tracks.md`
- `conductor/tracks/<track_id>/plan.md` for active tracks

### 5. Revert Work

**User triggers**: "revert the last track", "undo the feature", "revert [track/phase/task name]"

**What happens**:
1. Analyze git history to understand the scope of work to revert
2. Identify relevant commits based on Conductor's commit conventions
3. Present options to user:
   - Revert entire track
   - Revert specific phase
   - Revert specific task
4. After user confirmation, execute git revert operations
5. Update `conductor/tracks.md` and relevant `plan.md` files
6. Clean up or archive reverted artifacts

**Git-aware revert logic**:
- Understands logical units (tracks, phases, tasks)
- Uses checkpoint commits as boundaries
- Preserves git history with proper revert commits
- Updates Conductor state files accordingly

## Development Workflow Guidelines

### Test-Driven Development (TDD)

Conductor enforces TDD by default through the workflow.md template:

1. **Red Phase**: Write one or more unit tests that define expected behavior
   - Tests must fail initially
   - Critical: Run tests and confirm failure before proceeding
2. **Green Phase**: Write minimum code necessary to make tests pass
   - Focus on making tests pass, not on perfection
   - Run tests and confirm they pass
3. **Refactor Phase**: Improve code quality while keeping tests green
   - Improve readability, maintainability, performance
   - Run tests after each refactor to ensure they still pass

### Commit Strategy

- **Task completion commits**: When a task is finished
  - Format: `conductor(plan): Mark task 'X' as complete`
- **Checkpoint commits**: At the end of each phase
  - Format: `conductor(checkpoint): Checkpoint end of Phase X`
  - Include verification report in git notes
- **Regular commits**: During development as appropriate
  - Follow project conventions defined in workflow.md

### Code Coverage Goals

- Target >80% code coverage for all modules
- Coverage checked at phase boundaries
- Gaps identified during manual verification

## Important Implementation Notes

### Non-Interactive & CI-Aware Execution

- Prefer non-interactive commands
- Use `CI=true` environment variable for watch-mode tools
- Ensure single execution in automated environments

### The Plan is the Source of Truth

- All work must be tracked in `plan.md`
- Plan updates are committed separately from implementation
- Status changes are auditable through git history

### Tech Stack is Deliberate

- Changes to tech stack must be documented in `tech-stack.md` before implementation
- Ensure team alignment on technology choices
- Document rationale for significant technology decisions

### Context Synchronization

- When a track is completed, relevant learnings update the main context files
- `product.md`, `tech-stack.md`, and `workflow.md` evolve with the project
- Context stays fresh and accurate across tracks

## Token Consumption Awareness

Conductor's context-driven approach involves reading and analyzing project context, specifications, and plans. This can lead to increased token consumption, especially in:

- Larger projects with extensive context
- Extensive planning phases
- Implementation phases that reference multiple context files

Optimize by:
- Keeping context files focused and concise
- Using the most relevant context for each task
- Periodically reviewing and refining context documents

## Best Practices

1. **Setup thoroughly**: Take time during initial setup to create comprehensive context
2. **Review plans before implementing**: Catch issues early in the planning stage
3. **Follow the workflow**: TDD and verification protocols catch bugs before they compound
4. **Keep context updated**: Update product.md and tech-stack.md as the project evolves
5. **Use checkpoints**: They provide safety nets for experimentation
6. **Commit frequently**: Proper git history makes revert operations more precise
7. **Manual verification matters**: Don't skip verification steps at phase boundaries

## Natural Language Usage

Users don't need to memorize specific commands. Natural language works:

- "Let's set up conductor for this project"
- "I want to add user authentication"
- "Start implementing the authentication feature"
- "What's our current progress?"
- "I need to undo the last feature we added"

Claude Code will recognize these requests and invoke the appropriate Conductor protocols automatically.

## Context Drift Prevention

In long conversations, context can drift. Conductor combats this through:

1. **Persistent markdown files**: State lives in files, not just conversation
2. **Explicit status tracking**: Progress is recorded in plan.md
3. **Phase boundaries**: Verification steps create natural checkpoints
4. **Git integration**: Commit history provides additional state tracking
5. **Context file references**: Always consult the latest state from files

## Integration with Claude Code Features

Conductor works seamlessly with:

- **Skills**: Can be invoked as part of custom skills
- **Subagents**: Can delegate work to subagents while maintaining context
- **MCP Servers**: Can integrate with external tools and services
- **Git integration**: Leverages git for state management and revert operations

## Summary

Conductor transforms ad-hoc AI coding into a structured, repeatable process. By externalizing context into versioned markdown files and enforcing a spec → plan → implement workflow, it ensures:

- **Quality**: TDD and verification prevent bugs
- **Continuity**: State persists across sessions
- **Collaboration**: Team members share common context
- **Control**: Humans approve plans before code is written
- **Auditability**: Git history tracks all decisions and changes

The result is code that feels like it was written by a cohesive, experienced team following established practices - even when it's generated by AI.