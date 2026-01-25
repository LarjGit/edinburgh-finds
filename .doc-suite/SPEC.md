DOC-SUITE (Universal) — Documentation Suite Generator V2

Audience: AI assistants (Claude, GPT, Gemini) in agent/CLI mode
Goal: Generate deterministic repo documentation that builds a MENTAL MODEL, not just an encyclopedia.

============================================================
ENVIRONMENT ADAPTATION (CRITICAL)

This spec is tool-agnostic and MUST work on Windows, Mac, and Linux.

Before ANY file operations:
1. Detect the operating system 
2. Adapt all file operations to the detected environment:
   - Windows: Use Python for file operations
   - Unix/Mac: Use Python or bash
   - Cross-platform: Prefer Python for complex operations

Path handling:
- Store all paths with forward slashes (/) in state files
- Use OS-appropriate separators for actual file operations only
- Normalize paths before comparing or grouping

File enumeration:
- Use Python with os.walk() for recursive traversal
- Apply excludes during traversal (not after)
- Handle both Unix and Windows line endings

The spec defines WHAT outcomes are required, not HOW to achieve them.
Choose tools that work reliably in the detected environment.

============================================================
DISPATCH & CONTROL (NON-NEGOTIABLE)

Dispatch
Execute only if the user message contains exactly one line that starts with:
DOC-SUITE:

Otherwise do nothing.

Atomicity
Execute exactly one command per run. After it completes, STOP with a short summary.

Disk-backed state only
All state MUST be stored on disk. No inventory/queue/state in chat.

State files (source of truth):
- temp/doc-manifest.json
- temp/repo-map.json

Determinism
Given the same repo state and the same limits/excludes, INIT must produce the same
repo-map and manifest (stable ordering, stable grouping, stable work item ids).

============================================================
COMMANDS (ONLY THESE)

DOC-SUITE: INIT
DOC-SUITE: DELTA
DOC-SUITE: STEP
DOC-SUITE: FINALIZE
DOC-SUITE: BUILD

Operator workflows:

Full rebuild (nuke and rebuild):
INIT → STEP (repeat) → FINALIZE

Incremental (delta only):
DELTA → STEP (repeat) → FINALIZE

Automatic (full pipeline):
BUILD

============================================================
LIMITS, EXCLUDES, OUTPUTS

Limits:
- MAX_FILES_PER_STEP = 20
- MAX_LOC_PER_STEP = 2000

Hard excludes (directory name match, case-insensitive):
.git node_modules archive docs temp dist build out
.next .turbo .cache .parcel-cache
__pycache__ .pytest_cache .venv venv env
htmlcov .vscode .idea .obsidian .claude
.doc-suite .prune-suite

Hard excludes (file patterns, case-insensitive):
*.map *.chunk.js *.min.js *.pyc

Output layout:

Subsystem docs:
docs/architecture/subsystems/<subsystem>.md

Cross-cutting docs:
docs/_index.md
docs/architecture/overview.md
docs/architecture/c4-context.md
docs/architecture/c4-container.md

Operational docs (generated in FINALIZE):
docs/reference/*.md (API reference, data models)
docs/howto/*.md (setup, deployment, development guides)
docs/operations/*.md (monitoring, maintenance, troubleshooting)

Path separators:
- Use forward slashes (/) in all generated documentation
- Use OS-appropriate separators for actual file operations

Splitting (STRICT):
- Default is ONE file per subsystem: <subsystem>.md
- Multiple STEP runs for a subsystem MUST append to the SAME <subsystem>.md
- Never create .part-XX.md files
- The manifest MUST NEVER use .part-XX.md as output_path

============================================================
EVIDENCE (STRICT)

Technical claims require citations from files opened in the current STEP/FINALIZE.

Evidence format: Evidence: path:lineStart-lineEnd
(Always use forward slashes in citations regardless of OS)

If not observed: "Not observed in opened files."

It is forbidden to cite a file that was not opened in the current operation.

============================================================
INTELLIGENT SUBSYSTEM GROUPING (DETERMINISTIC)

Philosophy: Group files by PURPOSE and DOMAIN, not just directory structure.

Detection rules (in priority order, using normalized paths with /):

1. **Frontend/UI Code**
   Patterns: src/app/**, src/pages/**, src/components/**, app/**, pages/**, components/**
   Extensions: .tsx, .jsx, .vue, .svelte
   → subsystem "frontend"

2. **Backend/API Code**
   Patterns: src/api/**, api/**, server/**, backend/**, routes/**, controllers/**
   Extensions: .py, .ts, .js (in backend contexts)
   → subsystem "backend" or "api"

3. **Database/Schema**
   Patterns: prisma/**, migrations/**, alembic/**, src/db/**, database/**, models/**, schema/**
   Files: schema.prisma, *.sql
   → subsystem "database"

4. **Core Business Logic**
   Patterns: src/lib/**, lib/**, src/core/**, core/**, src/engine/**, engine/**, domain/**
   → subsystem by directory name (e.g., "engine", "core") or "lib"

5. **Testing**
   Patterns: tests/**, test/**, __tests__/**, **/*.test.*, **/*.spec.*
   → subsystem "tests"

6. **Scripts & Automation**
   Patterns: scripts/**, tools/**, bin/**
   Extensions: .sh, .bash, .py (in scripts contexts)
   → subsystem "scripts"

7. **Infrastructure & CI/CD**
   Patterns: .github/workflows/**, docker/**, k8s/**, terraform/**, .gitlab-ci.yml
   Files: Dockerfile, docker-compose*.yml, *.tf
   → subsystem "infrastructure"

8. **Configuration**
   Root-level files only: .env*, *.config.js, *.config.ts, pyproject.toml, package.json, tsconfig.json, next.config.js, etc.
   → subsystem "config"

9. **Documentation Source**
   Patterns: README*, CONTRIBUTING*, LICENSE*, *.md (root level only)
   → subsystem "docs-source"

10. **Fallback**
    Otherwise → subsystem = first path segment (top-level directory)

Special rules:
- Root-level single files (including dotfiles) → subsystem "root"
- Generated files (check for headers like "generated", "auto-generated", "@generated") → EXCLUDE entirely
- Files in excluded directories → EXCLUDE entirely

Path normalization for grouping:
- Convert all paths to use forward slashes
- Make paths relative to repo root
- Trim leading ./ or .\

============================================================
STATE FILE REQUIREMENTS

temp/repo-map.json schema:
{
  "repo_root": "/absolute/path/to/repo",
  "excludes": {
    "directories": ["node_modules", ".git", ...],
    "patterns": ["*.map", "*.min.js", ...]
  },
  "limits": {
    "max_files_per_step": 20,
    "max_loc_per_step": 2000
  },
  "files": [
    {
      "path": "src/app/page.tsx",
      "subsystem": "frontend",
      "kind": "source",
      "loc": 145,
      "extension": ".tsx"
    }
  ],
  "subsystems": {
    "frontend": {
      "file_count": 12,
      "total_loc": 2340,
      "primary_extensions": [".tsx", ".ts"]
    }
  }
}

temp/doc-manifest.json schema:
{
  "version": "1.0",
  "limits": {
    "max_files_per_step": 20,
    "max_loc_per_step": 2000
  },
  "excludes": {
    "directories": ["node_modules", ".git", ...],
    "patterns": ["*.map", "*.min.js", ...]
  },
  "baseline": {
    "timestamp": "2025-01-25T14:30:00Z",
    "commit": "abc123def456 or null"
  },
  "work_queue": [
    {
      "id": "frontend",
      "subsystem": "frontend",
      "files": ["src/app/page.tsx", "src/components/Header.tsx"],
      "file_count": 2,
      "total_loc": 450,
      "output_path": "docs/architecture/subsystems/frontend.md",
      "status": "todo|doing|done|blocked"
    }
  ],
  "outputs": [
    "docs/architecture/subsystems/frontend.md",
    "docs/howto/setup.md"
  ]
}

============================================================
OPERATION: DOC-SUITE: INIT

Goal:
Reset docs state and create fresh repo-map + manifest WITHOUT generating docs.
This is the "nuke everything" operation.

Required outcomes:

1. Backup and reset docs/
   - If docs/ exists: move to archive/docs_backup_<timestamp>/
     where timestamp = YYYYMMDD_HHMMSS
   - Create fresh directory structure:
     - docs/architecture/subsystems/
     - docs/reference/
     - docs/howto/
     - docs/operations/

2. Reset temp/ state
   - Create temp/ directory if it doesn't exist
   - Delete temp/doc-manifest.json if present
   - Delete temp/repo-map.json if present  
   - Delete temp/doc-coverage-report.md if present

3. Scan repository (use Python for reliability)
   - Start from current working directory as repo root
   - Recursively enumerate ALL files using os.walk()
   - Apply hard excludes DURING traversal (modify dirnames in-place)
   - Skip files matching excluded patterns
   - For each included file:
     - Normalize path to forward slashes
     - Make relative to repo root
     - Detect file kind: source/config/script/doc/other
     - Count lines of code (for source files)
     - Assign subsystem using INTELLIGENT SUBSYSTEM GROUPING rules
   - Sort file list alphabetically by path

4. Build repo-map.json
   - Store complete file inventory with metadata
   - Calculate per-subsystem statistics
   - Include exclude rules and limits for reference
   - Write to temp/repo-map.json

5. Build work queue
   - Group files by subsystem
   - Create one work item per subsystem
   - Sort work items by:
     1. Priority (infrastructure > scripts > config > backend > frontend > tests)
     2. Alphabetically by subsystem name
   - Calculate file counts and LOC totals per work item
   - If work item exceeds MAX_FILES_PER_STEP:
     - Split into multiple work items: subsystem-part1, subsystem-part2, etc.
     - Each part respects MAX_FILES_PER_STEP
     - BUT output_path remains the SAME (parts append to same doc)
   - All work items start with status: "todo"
   - Write to temp/doc-manifest.json

6. Record baseline
   - If git available: run `git rev-parse HEAD` to get commit hash
   - Always record current timestamp (ISO 8601 format)
   - Store in manifest baseline

7. STOP with summary
   Display:
   - Repository root: <path>
   - Files scanned: X
   - Files included: Y
   - Files excluded: Z
   - Subsystems identified: N
   - Work items created: M
   - State files: temp/repo-map.json, temp/doc-manifest.json
   - Ready for: DOC-SUITE: STEP

Implementation notes:
- Use Python for file enumeration (cross-platform)
- Handle encoding errors gracefully (use errors='ignore')
- Exclude binary files from LOC counting
- Preserve all state in JSON (no in-memory state)

============================================================
OPERATION: DOC-SUITE: DELTA

Precondition:
temp/doc-manifest.json AND temp/repo-map.json must exist.
If not: "State files not found. Run DOC-SUITE: INIT first." STOP.

Goal:
Mark impacted work items as todo WITHOUT rebuilding entire inventory.
This is the "incremental update" operation.

Required outcomes:

1. Load existing state
   - Read temp/doc-manifest.json
   - Read temp/repo-map.json
   - Extract baseline commit/timestamp

2. Detect changed files
   Method A (if git available):
   - Run: git diff --name-only <baseline_commit>..HEAD
   - Get list of changed/added/deleted files
   
   Method B (if no git):
   - Enumerate current files (applying excludes)
   - Compare modification timestamps against baseline timestamp
   - Identify files modified after baseline
   
   Result: List of changed file paths

3. Check for inventory drift
   - Enumerate current files (applying same excludes as INIT)
   - Compare against repo-map.json file list
   - Detect:
     - New files not in repo-map
     - Deleted files in repo-map but not on disk
     - New directories that might be new subsystems
   
   If significant drift detected (>10 new files or new subsystems):
   - Output: "Inventory drift detected: X new files, Y new directories"
   - Recommend: "Run DOC-SUITE: INIT to rebuild inventory"
   - STOP (don't proceed with delta)

4. Map changes to subsystems
   - For each changed file:
     - Look up its subsystem in repo-map.json
     - If file is new: assign subsystem using grouping rules
   - Build set of affected subsystems

5. Mark work items for update
   - For each affected subsystem:
     - Find corresponding work item(s) in manifest
     - Set status to "todo"
   - Preserve "done" status for unaffected subsystems
   - Update manifest baseline to current commit/timestamp

6. Persist updated manifest
   - Write temp/doc-manifest.json with updated statuses

7. STOP with summary
   Display:
   - Changes detected: X files
   - Subsystems affected: Y
   - Work items marked for update: Z
   - Ready for: DOC-SUITE: STEP

Implementation notes:
- Handle deleted files gracefully (don't fail if file missing)
- If git not available, fall back to timestamp comparison
- Be conservative: if unsure, mark as changed

============================================================
OPERATION: DOC-SUITE: STEP

Goal:
Generate documentation for exactly ONE work item.
This is the core documentation generation operation.

Required outcomes:

1. Select next work item
   - Read temp/doc-manifest.json
   - Find first item in work_queue with status="todo"
   - If none found: "No pending work items. All documentation up to date." STOP

2. Mark as in-progress
   - Set selected work item status="doing"
   - Write temp/doc-manifest.json immediately (persist state)

3. Load file contents
   - Open ONLY the files listed in this work item
   - Respect MAX_FILES_PER_STEP limit
   - For each file:
     - Read full contents using view tool
     - Parse structure (functions, classes, imports, etc.)
     - Identify key patterns and dependencies
   - If work item is a "part" (e.g., subsystem-part2):
     - Also read existing subsystem doc to understand context

4. Analyze subsystem (WORKFLOW & VISUAL AWARENESS)
 Based on subsystem type, extract NOT JUST static facts but DYNAMIC flows:
   
   For CODE subsystems (frontend, backend, core, lib):
   - **Workflows:** Identify the top 3 tasks a developer performs (e.g., "Add new Entity", "Handle 404").
   - **Orchestration:** If "Ingestion" or "Orchestrator" detected, trace the "Life of a Request".
   - **Data Flow:** How data transforms from Input -> Process -> Output.
   - Purpose, components, patterns, dependencies. 
   
   For DATABASE subsystems:
   - **Relationships:** Identify 1:1, 1:N, N:M relationships for ERD generation.
   - **Schema:** Models, fields, constraints. 
   
   For INFRASTRUCTURE/SCRIPTS subsystems:
   - **Usage:** Flags, arguments, environment variables.
   - **Examples:** Valid command invocations.
   
   For CONFIG subsystems:
   - **Examples:** Valid configuration snippets (10 lines).

5. Generate/update documentation
 Target: docs/architecture/subsystems/<subsystem>.md
   
   If file does NOT exist (first STEP for this subsystem):
   - Create new file with full structure:
```markdown
     # Subsystem: <subsystem-name>
     
     ## Purpose
     [What this subsystem does and why it exists]

     ## Common Workflows
     [Step-by-step guides for the 3 most common dev tasks in this subsystem]

     ## Key Components
     [List of main files/classes/functions with descriptions]
     
     ## Architecture & Diagrams
     [Mermaid diagram MANDATORY based on type]
     - Database: classDiagram
     - Orchestration: sequenceDiagram
     - General: graph TD (Data Flow/Dependency)

     ## Dependencies
     ### Internal
     [Other subsystems this depends on]
     
     ### External
     [Third-party libraries, services, APIs]
     
     ## Configuration & Examples
     [Code snippets, Config examples, CLI usage tables]

     ## Evidence
     [All citations to source files analyzed]
```
   
   If file EXISTS (subsequent STEP for multi-part subsystem):
   - Read existing content
   - Append/merge new findings to appropriate sections
   - **Enhance Diagrams:** Update existing Mermaid diagrams with new nodes/edges.
   - **Add Examples:** Add new CLI/Config examples found. 
   
   Content quality requirements (V2):
   - **Visuals:** MUST include at least one Mermaid diagram per subsystem.
   - **Examples:** MUST include 2+ code/config/CLI examples per subsystem.
   - **Narrative:** Describe *how it works*, not just *what it is*.
   - **Specifics:** No vague logic descriptions. Use pseudo-code for complex logic.

6. Update manifest
   - Set work item status="done"
   - Add output file path to outputs[] array (if not already present)
   - Update work item metadata (e.g., last_updated timestamp)
   - Write temp/doc-manifest.json

7. STOP with summary
   Display:
   - Subsystem documented: <subsystem-name>
   - Files analyzed: X
   - Output: docs/architecture/subsystems/<subsystem>.md
   - Status: Work item completed
   - Remaining work items: Y

Implementation notes:
- Use view tool to read files (handles encoding properly)
- Use create_file for new docs, str_replace for updates
- Keep memory usage low (don't load all files at once)
- Evidence citations MUST reference actually opened files only

============================================================
OPERATION: DOC-SUITE: FINALIZE

Goal:
Generate cross-cutting documentation and operational guides.
This is where howto, reference, and operations docs are created.

Required outcomes:

1. Verify all work items completed
   - Read temp/doc-manifest.json
   - Check that all work items have status="done"
   - If any are "todo" or "doing": 
     - "Cannot finalize: X work items still pending. Run DOC-SUITE: STEP to complete."
     - STOP

2. Generate cross-cutting architecture docs

   docs/_index.md:
   - Project name and description
   - Technology stack (extracted from package.json, pyproject.toml, etc.)
   - High-level purpose and scope
   - Quick start links
   - Link to architecture overview
   - Link to how-to guides
   Evidence: Root config files, README files from docs-source subsystem
   
   docs/architecture/overview.md:
   - System architecture narrative
   - Subsystem map (list all documented subsystems with one-line descriptions)
   - Key architectural decisions
   - Technology choices and rationale
   - Data flow overview (if database subsystem exists)
   - Integration points
   Evidence: All subsystem docs, config files, infrastructure files
   
   docs/architecture/c4-context.md:
   - C4 Context diagram (Mermaid format)
   - External systems and actors
   - System boundaries
   - High-level interactions
   Evidence: API endpoints, external dependencies from subsystem docs
   
   docs/architecture/c4-container.md:
   - C4 Container diagram (Mermaid format)
   - Major subsystems as containers
   - Inter-subsystem dependencies
   - Technology per container
   Evidence: Subsystem dependencies, tech stack

3. Generate operational docs (CONDITIONAL - only if evidence exists)

   docs/reference/ (only if APIs or data models found):
   
   docs/reference/api.md:
   - IF backend/api subsystem exists with HTTP endpoints
   - Extract and document API endpoints
   - Request/response formats
   - Authentication requirements
   Evidence: Backend subsystem analysis, route definitions
   
   docs/reference/data-models.md:
   - IF database subsystem exists
   - Document database schema
   - Entity relationships
   - Key constraints and indexes
   - **Visual:** Mermaid ERD (Entity Relationship Diagram)
   Evidence: schema.prisma, SQL migrations, model files
   
   docs/howto/ (only if scripts or infrastructure found):
   
   docs/howto/development-setup.md:
   - IF scripts subsystem contains setup/install scripts
   - Extract setup steps from scripts
   - Prerequisites and dependencies
   - Environment configuration
   - Common issues and solutions
   Evidence: scripts/setup*, scripts/install*, README sections
   
   docs/howto/deployment.md:
   - IF infrastructure subsystem or deployment scripts exist
   - Deployment process and steps
   - Environment requirements
   - Configuration needed
   - Rollback procedures if documented
   Evidence: docker-compose.yml, Dockerfile, deploy scripts, CI/CD workflows
   
   docs/howto/testing.md:
   - IF tests subsystem exists
   - How to run tests
   - Test organization
   - Coverage requirements
   - Writing new tests
   Evidence: test files, CI workflows, package.json scripts
   
   docs/operations/ (only if ops configs or monitoring found):
   
   docs/operations/monitoring.md:
   - IF monitoring/observability configs found
   - Monitoring setup
   - Key metrics
   - Alerting rules
   Evidence: Prometheus configs, logging configs, APM setup
   
   docs/operations/troubleshooting.md:
   - **Log Patterns:** Extract regex/error messages from code (e.g., `logger.error("Failed to X")`).
   - **Error Classes:** List custom exception classes and their triggers.
   - **Debug Workflow:** Step-by-step guide to diagnose common failures.
   Evidence: Error handlers, logging code, runbooks if present

   docs/operations/maintenance.md:
   - **Tasks:** Routine cleanup, rotation, or backfill tasks found in scripts.
   - **Commands:** Exact CLI commands to perform these tasks.
   Evidence: Cron scripts, maintenance utility scripts.

4. Generate coverage report
   - Create temp/doc-coverage-report.md
   - List all subsystems with documentation status
   - Calculate coverage: documented_files / total_files
   - Identify gaps (files not assigned to any subsystem)
   - List all generated documentation files
   - Suggest improvements

5. Update baseline
   - If git available: record current commit hash
   - Always record current timestamp (ISO 8601)
   - Update temp/doc-manifest.json baseline

6. STOP with summary
   Display:
   - Cross-cutting docs created: X
   - Operational docs created: Y
   - Total documentation files: Z
   - Coverage: XX%
   - Coverage report: temp/doc-coverage-report.md
   - Documentation complete: docs/

Implementation notes:
- Only create operational docs if clear evidence exists
- Don't hallucinate setup steps - extract from actual scripts
- For how-to docs, prefer showing actual commands from scripts
- Keep operational docs actionable and specific
- Link between docs (e.g., overview links to subsystem docs)

============================================================
OPERATION: DOC-SUITE: BUILD

Goal:
Automatic end-to-end documentation generation (full pipeline).
This runs INIT → STEP (loop) → FINALIZE without user intervention.

Required behavior:

1. Execute INIT
   - Reset all state
   - Scan repository
   - Build work queue
   - If INIT fails: report error and STOP

2. Execute STEP loop
   - While work items with status="todo" exist:
     - Execute STEP
     - If STEP fails: report error and STOP
   - Continue until all work items are "done"
   - Maximum iterations: 1000 (safety limit)
   - If limit reached: "Safety limit reached. Manual intervention required." STOP

3. Execute FINALIZE
   - Generate cross-cutting docs
   - Generate operational docs
   - Create coverage report
   - If FINALIZE fails: report error and STOP

4. STOP with summary
   Display:
   - Total subsystems documented: X
   - Total files analyzed: Y
   - Documentation files generated: Z
   - Coverage: XX%
   - Time elapsed: Approximate duration
   - Success: Documentation complete at docs/

Implementation notes:
- This is the ONLY multi-operation command
- Operations execute sequentially without user prompts
- Each operation must complete successfully before next begins
- Preserve all intermediate state in case of failure
- Report which operation failed if error occurs

============================================================
ERROR HANDLING

If any operation fails:
1. Report the error clearly with operation name
2. Show the specific failure (file not found, parse error, etc.)
3. Preserve state files (don't delete partial work)
4. Suggest recovery action

Common errors and recovery:

- "State file not found" 
  → Run DOC-SUITE: INIT first

- "Permission denied writing to docs/"
  → Check file/directory permissions
  → Ensure docs/ is not open in another program

- "Path too long" (Windows)
  → Use shorter subsystem names
  → Move repo closer to drive root

- "Invalid JSON in state file"
  → Show parse error location
  → Suggest deleting corrupt state and running INIT

- "No files found in repository"
  → Check that you're in correct directory
  → Verify excludes aren't too aggressive

- "Git command failed"
  → DELTA will fall back to timestamp comparison
  → Not a fatal error, continue

- "Cannot read file (encoding error)"
  → Skip file and continue
  → Log skipped file in coverage report

Recovery strategy:
- For INIT failures: Safe to re-run (idempotent)
- For STEP failures: Re-run STEP (will pick up where it left off)
- For FINALIZE failures: Fix issue and re-run FINALIZE
- For BUILD failures: Check state, run individual commands manually

============================================================
IMPLEMENTATION REFERENCE

Cross-platform file enumeration (Python):
```python
import os
import json
from pathlib import Path
from datetime import datetime

EXCLUDE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.next', 
    '.turbo', 'dist', 'build', 'venv', '.venv',
    'docs', 'temp', 'archive'
}

EXCLUDE_PATTERNS = {'.map', '.min.js', '.pyc'}

def scan_repository(root_path):
    """Scan repository and return file inventory"""
    files = []
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Exclude directories in-place (modifies dirnames)
        dirnames[:] = [
            d for d in dirnames 
            if d.lower() not in EXCLUDE_DIRS
        ]
        
        for filename in filenames:
            # Check exclude patterns
            if any(filename.endswith(ext) for ext in EXCLUDE_PATTERNS):
                continue
            
            # Build full and relative paths
            full_path = Path(dirpath) / filename
            rel_path = full_path.relative_to(root_path)
            
            # Normalize to forward slashes
            normalized = str(rel_path).replace('\\', '/')
            
            # Detect file properties
            file_info = {
                'path': normalized,
                'subsystem': detect_subsystem(normalized),
                'kind': detect_kind(normalized),
                'loc': count_lines(full_path),
                'extension': full_path.suffix
            }
            
            files.append(file_info)
    
    return sorted(files, key=lambda f: f['path'])

def detect_subsystem(path):
    """Assign subsystem based on path patterns"""
    parts = path.split('/')
    ext = Path(path).suffix
    
    # Frontend
    if any(p in parts for p in ['components', 'pages', 'app']) and ext in ['.tsx', '.jsx']:
        return 'frontend'
    
    # Backend/API
    if any(p in parts for p in ['api', 'routes', 'server']) and ext in ['.ts', '.js', '.py']:
        return 'backend'
    
    # Database
    if 'prisma' in path or 'schema' in path or ext == '.sql':
        return 'database'
    
    # Tests
    if 'test' in path or '__tests__' in parts:
        return 'tests'
    
    # Scripts
    if 'scripts' in parts or ext in ['.sh', '.bash', '.ps1']:
        return 'scripts'
    
    # Infrastructure
    if '.github' in parts or 'docker' in path:
        return 'infrastructure'
    
    # Config (root level only)
    if len(parts) == 1 and ext in ['.json', '.yml', '.yaml', '.toml', '.env']:
        return 'config'
    
    # Default: use first directory
    return parts[0] if len(parts) > 1 else 'root'

def detect_kind(path):
    """Detect file kind based on extension"""
    ext = Path(path).suffix.lower()
    
    source_exts = {'.py', '.ts', '.tsx', '.js', '.jsx', '.vue', '.svelte'}
    config_exts = {'.json', '.yml', '.yaml', '.toml', '.env'}
    script_exts = {'.sh', '.bash', '.ps1'}
    
    if ext in source_exts:
        return 'source'
    elif ext in config_exts:
        return 'config'
    elif ext in script_exts:
        return 'script'
    elif ext == '.md':
        return 'doc'
    else:
        return 'other'

def count_lines(filepath):
    """Count lines of code, handling encoding errors"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except:
        return 0

def build_work_queue(files, max_files_per_step=20):
    """Group files by subsystem into work items"""
    from collections import defaultdict
    
    subsystem_files = defaultdict(list)
    for file_info in files:
        subsystem_files[file_info['subsystem']].append(file_info)
    
    work_queue = []
    
    for subsystem, sub_files in sorted(subsystem_files.items()):
        # Calculate totals
        file_count = len(sub_files)
        total_loc = sum(f['loc'] for f in sub_files)
        
        # Split if needed
        if file_count <= max_files_per_step:
            work_queue.append({
                'id': subsystem,
                'subsystem': subsystem,
                'files': [f['path'] for f in sub_files],
                'file_count': file_count,
                'total_loc': total_loc,
                'output_path': f'docs/architecture/subsystems/{subsystem}.md',
                'status': 'todo'
            })
        else:
            # Split into parts
            for i in range(0, file_count, max_files_per_step):
                part_files = sub_files[i:i+max_files_per_step]
                part_num = i // max_files_per_step + 1
                
                work_queue.append({
                    'id': f'{subsystem}-part{part_num}',
                    'subsystem': subsystem,
                    'files': [f['path'] for f in part_files],
                    'file_count': len(part_files),
                    'total_loc': sum(f['loc'] for f in part_files),
                    'output_path': f'docs/architecture/subsystems/{subsystem}.md',  # Same output!
                    'status': 'todo'
                })
    
    return work_queue
```

Git integration (optional):
```python
import subprocess

def get_git_commit():
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except:
        return None

def get_changed_files(baseline_commit):
    """Get files changed since baseline"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', f'{baseline_commit}..HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n')
    except:
        return []
```

============================================================
QUALITY STANDARDS

Documentation quality checklist:

Subsystem docs must include:
- Clear purpose statement (2-3 sentences)
- **Visuals:** At least one Mermaid diagram (Sequence, Class, or Flowchart).
- **Workflows:** "Life of a Request" or "Common Tasks" section.
- **Examples:** 2+ Concrete code/config/CLI snippets.
- Architecture explanation (patterns, structure)
- Dependencies (internal and external)
- Evidence citations for all claims

Cross-cutting docs must include:
- Overview that makes sense standalone
- Links to relevant subsystem docs
- Diagrams where helpful (Mermaid)
- Technology stack explanation

Operational docs must include:
- Step-by-step instructions
- Actual commands (extracted from scripts)
- Prerequisites clearly stated
- **Troubleshooting:** Derived from actual log patterns/errors.

Writing style:
- Technical and precise
- Assume reader is skilled developer
- Focus on "why" and "how", not just "what"
- No speculation or assumptions
- Cite evidence for technical claims
- Use active voice
- Keep it concise

Forbidden:
- Vague statements like "handles various tasks"
- Copying large code blocks (use descriptions)
- Speculation about future plans
- Marketing language or hype
- Outdated information
- Broken links

============================================================
EXPECTED OUTCOMES

For a typical full-stack web project after DOC-SUITE: BUILD:

docs/
├── _index.md                           # Project overview
├── architecture/
│   ├── overview.md                     # System architecture
│   ├── c4-context.md                   # C4 context diagram
│   ├── c4-container.md                 # C4 container diagram
│   └── subsystems/
│       ├── frontend.md                 # React/Next.js frontend
│       ├── backend.md                  # API routes and logic
│       ├── database.md                 # Prisma schema and models
│       ├── tests.md                    # Test organization
│       ├── scripts.md                  # Automation scripts
│       └── infrastructure.md           # CI/CD and deployment
├── reference/
│   ├── api.md                          # API endpoint reference
│   └── data-models.md                  # Database schema
├── howto/
│   ├── development-setup.md            # Getting started
│   ├── deployment.md                   # Deployment guide
│   └── testing.md                      # Running tests
└── operations/
    ├── troubleshooting.md              # Common issues & Log patterns
    └── maintenance.md                  # Cleanup & Rotation tasks

temp/
├── doc-state.json                      # Current state
├── repo-map.json                       # File inventory
└── doc-coverage-report.md              # Coverage analysis

Typical metrics:
- Files analyzed: 80-200
- Subsystems: 5-12
- Documentation files: 10-20
- Coverage: 85-95%
- Time: 3-10 minutes (depending on repo size)

============================================================
FINAL NOTES

This spec is designed to:
1. Work reliably across operating systems
2. Handle repos from 10 to 10,000 files
3. Be resumable (state persisted to disk)
4. Be deterministic (same input → same output)
5. Generate useful documentation, not bureaucratic overhead

The AI executing this spec should:
- Use judgment in analyzing code
- Focus on what matters
- Write for developers
- Cite evidence
- Be thorough but concise

Documentation is a tool for understanding codebases, not an end in itself.
The goal is to help developers (including your future self) understand the system quickly and accurately.

