# PRUNE-SUITE (Universal) — Repository Dead-Code Pruning Engine

**Audience:** Developers

This spec is designed to run on Gemini, Claude, and Codex with the SAME instructions.
It avoids context exhaustion by using disk-backed state and atomic steps.

---

## How to run (same for all agents)

Tell the agent to execute one operation at a time using these exact phrases:

- `PRUNE-SUITE: RESET-FULL`
- `PRUNE-SUITE: INIT`
- `PRUNE-SUITE: VALIDATE`
- `PRUNE-SUITE: STEP`
- `PRUNE-SUITE: RUN` (optional convenience loop)
- `PRUNE-SUITE: VERIFY`
- `PRUNE-SUITE: DRY-RUN`
- `PRUNE-SUITE: APPLY` (optional destructive)

**Important:** STEP must produce exactly ONE output, then stop.

---

## Hard rules (non-negotiable)

**Atomic:** STEP produces exactly ONE analysis output, then stops.

**No chaining:** After producing a STEP result and updating the manifest/graph, you MUST return a text response immediately. Do not start the next work item until the user provides a new prompt.

**Limits:**
- `MAX_FILES_PER_STEP = 25`
- `MAX_LOC_PER_STEP = 2500`
- If exceeded, split into chunks.

**Disk is truth:**
Always read/write:
- `temp/prune-manifest.json`
- `temp/prune-graph.json`
- `temp/prune-candidates.json`
- `temp/prune-config.json` (new: user overrides)

**Conservative by default:**
- If reachability is uncertain → treat as USED (never delete).
- Only mark UNUSED when evidence is strong.
- False negatives are acceptable; false positives are catastrophic.

**Evidence is bounded (cheap citations):**
- Cite only technical claims (imports, edges, entrypoints, loaders, config references).
- Cite only from files opened in that STEP OR from prune-graph.json traversal results.
- Format: `Evidence: {type} | {source} | confidence:{level} | {pattern}`

**No speculation:**
- If you didn't open it in this step, you can't claim it (except for graph traversal results).
- No invented behavior, no assumptions about runtime.

**Read-only by default:**
- Nothing is deleted until `PRUNE-SUITE: APPLY` is explicitly executed.

**Platform note:**
- Prefer PowerShell-compatible commands on Windows.
- Do not assume bash, rg, grep, sed, or awk are installed.
- Git may be used when available.

---

## Output structure
````
temp/
  prune-manifest.json
  prune-graph.json
  prune-candidates.json
  prune-config.json          # NEW: user configuration

reports/
  prune-summary.md
  prune-validation.md         # NEW: pre-flight check
  prune-deletion-plan.md
  prune-dry-run.md           # NEW: impact preview

archive/
  prune_backup_YYYYMMDD_HHMMSS/
````

---

## Configuration File (temp/prune-config.json)

Created during INIT, user can edit before running VALIDATE.
````json
{
  "version": "2.0",
  "entrypointOverrides": [
    "src/workers/*.ts",
    "scripts/cron/*.py",
    "app/api/*/route.ts"
  ],
  "dynamicPatterns": [
    {
      "glob": "src/locale/*.json",
      "reason": "i18n loader",
      "markAsUsed": true
    },
    {
      "glob": "plugins/*.ts",
      "reason": "plugin system",
      "markAsUsed": true
    }
  ],
  "protectedPaths": [
    "migrations/**",
    "db/seeds/**",
    "prisma/schema.prisma",
    ".github/workflows/**",
    "infra/**"
  ],
  "framework": {
    "detected": "nextjs | express | django | unknown",
    "conventionPaths": [
      "pages/**/*.{tsx,jsx}",
      "app/**/route.ts",
      "middleware.ts"
    ]
  },
  "testHandling": {
    "treatTestsAsEntrypoints": false,
    "testPatterns": ["**/*.test.*", "**/*.spec.*", "tests/**"],
    "testUtilsAlwaysUsed": true
  },
  "workspaces": {
    "enabled": false,
    "packages": ["packages/*"]
  }
}
````

---

## Operation: PRUNE-SUITE: RESET-FULL

**Goal:** Remove legacy prune artifacts and start a clean full audit.

**Steps:**

1. If temp/ or reports/ outputs exist, archive them to:
   `archive/prune_backup_<timestamp>/`

2. Delete these files if they exist:
   - `temp/prune-manifest.json`
   - `temp/prune-graph.json`
   - `temp/prune-candidates.json`
   - `temp/prune-config.json`
   - `reports/prune-summary.md`
   - `reports/prune-validation.md`
   - `reports/prune-deletion-plan.md`
   - `reports/prune-dry-run.md`

3. Recreate empty folders:
   - `temp/`
   - `reports/`
   - `archive/`

4. Then execute `PRUNE-SUITE: INIT`.

**Stop.**

**Result:** Guaranteed no lingering prune state.

---

## Operation: PRUNE-SUITE: INIT

**Goal:** Create repo inventory + entrypoint roots + generate default config.

**Steps:**

1. **Inventory all files** in the repo, excluding:
   - `.git/`, `node_modules/`, `dist/`, `build/`, `archive/`
   - Generated artifacts, docs outputs

2. **Classify each file** as:
   - `source | config | asset | script | test | doc | other`

3. **Detect framework** (if applicable):
   - Check for: `next.config.js`, `package.json` dependencies, `manage.py`, etc.
   - Store in config as `framework.detected`

4. **Detect entrypoints** using metadata-first heuristics:

   **Package managers:**
   - `package.json`: `main`, `bin`, `exports`, `scripts` commands
   - `pyproject.toml`: `console_scripts`, `__main__.py`
   - `Cargo.toml`: `[[bin]]` entries

   **Framework conventions:**
   - **Next.js**: `pages/**/*.{tsx,jsx,ts,js}`, `app/**/route.ts`, `app/**/page.tsx`, `middleware.ts`
   - **Express/Fastify**: Look for `app.listen()`, router files
   - **Django**: `manage.py`, `wsgi.py`, `asgi.py`, `urls.py`
   - **Flask**: Files with `app.run()`, `create_app()`

   **Infrastructure:**
   - `Dockerfile`: `CMD` / `ENTRYPOINT`
   - CI workflows: GitHub Actions, GitLab CI job scripts
   - Serverless: `serverless.yml`, `lambda` handlers

   **Scripts:**
   - `package.json` scripts that execute files
   - Cron job references
   - Makefile targets

   **README quickstart:**
   - Light scan for command examples (e.g., `npm run dev`, `python main.py`)

5. **Detect workspaces/monorepo:**
   - Check `package.json` workspaces, `pnpm-workspace.yaml`, `lerna.json`
   - If found, each package root is a sub-entrypoint scope

6. **For source/config files collect:**
   - LOC
   - Lightweight imports/require from headers/signatures only (best effort)
   - File role guess: `entrypoint | library | config | asset | test | unknown`

7. **Chunk inventory** into work items respecting:
   - `<= MAX_FILES_PER_STEP`
   - `<= MAX_LOC_PER_STEP`

8. **Generate default config:**
   - Create `temp/prune-config.json` with detected framework, conventional paths, and safe defaults
   - Populate `protectedPaths` with common infrastructure patterns
   - Add framework-specific `entrypointOverrides` if detected

9. **Write:**
   - `temp/prune-manifest.json`
   - `temp/prune-graph.json` (initial, may contain only roots)
   - `temp/prune-config.json`
   - `reports/prune-summary.md` (inventory + detected entrypoints + framework)

**Stop.** INIT must not do full dependency traversal.

**Minimum manifest requirements:**
````json
{
  "limits": { "maxFiles": 25, "maxLOC": 2500 },
  "inventory": {
    "totalFiles": 1234,
    "byKind": { "source": 456, "test": 123, "config": 45, "..." }
  },
  "entrypoints": [
    {
      "path": "src/index.ts",
      "source": "package.json:main",
      "confidence": "high"
    }
  ],
  "framework": {
    "detected": "nextjs",
    "version": "14.x"
  },
  "files": {
    "src/index.ts": {
      "kind": "source",
      "loc": 234,
      "sha256": "abc123...",
      "subsystem": "core",
      "chunkId": "chunk_1",
      "quickImports": ["./lib/db", "express"]
    }
  },
  "work": {
    "queue": [
      {
        "workId": "chunk_1",
        "files": ["src/index.ts", "..."],
        "status": "todo"
      }
    ]
  }
}
````

---

## Operation: PRUNE-SUITE: VALIDATE

**Goal:** Pre-flight check to ensure pruning is safe and effective.

**Steps:**

1. **Load:**
   - `temp/prune-manifest.json`
   - `temp/prune-config.json`

2. **Check entrypoint coverage:**
   - Verify at least ONE entrypoint was detected
   - If zero entrypoints: **STOP with error** – "No entrypoints detected. Manual review required."

3. **Framework validation:**
   - If framework detected, verify conventional paths are covered
   - Example: If Next.js detected, check if `pages/` or `app/` routes are in entrypoints

4. **Detect problematic patterns:**
   - Scan for: `eval()`, `new Function()`, `require(variable)`
   - Scan for: runtime reflection (e.g., `__import__`, `importlib`)
   - Flag files with these patterns as HIGH RISK

5. **Workspace validation:**
   - If workspaces enabled, verify each package has entrypoints
   - Check for internal package dependencies (`"@myorg/pkg-a"` → `packages/pkg-a`)

6. **Config chain resolution:**
   - Detect config inheritance: `tsconfig.json` → `extends`, `pytest.ini` → `testpaths`
   - Mark parent configs as USED if child is reachable

7. **Estimate coverage confidence:**
   - **HIGH:** Standard framework, clear entrypoints, minimal dynamic loading
   - **MEDIUM:** Some dynamic patterns, but covered by config overrides
   - **LOW:** Heavy reflection, complex plugin systems, missing framework detection

8. **Size analysis:**
   - Count files by category
   - Estimate potential savings (heuristic: test files + doc files if unreachable)

9. **Write:**
   - `reports/prune-validation.md`

10. **Decision:**
    - If confidence < MEDIUM and no user override: **STOP** with recommendation to add overrides
    - If confidence >= MEDIUM: Continue

**Stop.**

**Validation report format:**
````markdown
# PRUNE-SUITE Validation Report

## Repository Overview
- Framework: Next.js 14.x
- Total Files: 1,234
- Entrypoints Detected: 12

## Coverage Confidence: MEDIUM

### Entrypoints Found
- ✅ pages/index.tsx (convention)
- ✅ app/api/*/route.ts (glob: 8 files)
- ✅ scripts/build.ts (package.json)

### Risk Factors
- ⚠️ Dynamic imports detected in `src/plugins/loader.ts:45`
- ⚠️ 3 files use `require(variable)` pattern
- ✅ Config overrides cover i18n loader

### Recommendations
- Framework conventions are covered
- Consider adding `dynamicPatterns` for plugin system
- Proceed with STEP operations

**SAFE TO PROCEED** (with normal caution)
````

---

## Operation: PRUNE-SUITE: STEP

**Goal:** Analyze exactly ONE queued chunk and extend the reachability graph.

**Steps:**

1. **Load:**
   - `temp/prune-manifest.json`
   - `temp/prune-graph.json`
   - `temp/prune-config.json`

2. **Select** next work item with `status = todo`.

3. **Mark it `doing`** and persist manifest immediately.

4. **Open only** the files listed for that work item.

5. **Extract edges** (best effort, language-appropriate):
   
   **Static edges (high confidence):**
   - `import X from 'Y'`, `require('Z')`
   - `from X import Y`
   - `use X;` (Rust)
   
   **Config references:**
   - `tsconfig.json` → `extends: "./base.json"`
   - `package.json` → `workspaces: ["packages/*"]`
   - Environment file references (`.env` → code)
   
   **Dynamic imports (where detectable):**
   - `import(\`./locale/${lang}.json\`)` → flag pattern, check against config `dynamicPatterns`
   - Plugin registration: `registerPlugin(name)` → check convention paths
   
   **Asset references:**
   - `<Image src="/images/logo.png" />`
   - `url('/assets/bg.jpg')`
   - `require('./styles.css')`
   
   **File path loads:**
   - Template references: `render('template.html')`
   - SQL file loads: `open('queries/user.sql')`
   - Migration runners: migrations directory scans

6. **For each edge record:**
````json
   {
     "from": "src/app.ts",
     "to": "src/lib/db.ts",
     "edgeType": "static_import",
     "confidence": "high",
     "evidence": {
       "type": "static_import",
       "source": "src/app.ts:3",
       "pattern": "import { connectDB } from './lib/db'"
     }
   }
````

7. **Apply config overrides:**
   - If file matches `dynamicPatterns.glob`, add edge with `edgeType: "config_override"`
   - If file matches `entrypointOverrides`, mark as entrypoint

8. **Handle test files:**
   - If `testHandling.treatTestsAsEntrypoints = false`:
     - Don't mark test-imported files as USED unless also imported by non-test
     - DO mark test utilities as USED if `testUtilsAlwaysUsed = true`

9. **Append edges** into `temp/prune-graph.json`.

10. **Update manifest:**
    - Mark work item `done`
    - Store updated hashes (optional)

11. **Terminate turn immediately** with:
    - Chunk analyzed
    - Number of edges added
    - Any ambiguous/dynamic patterns detected
    - Any config overrides applied

**Stop.**

**Prohibitions:**
- No deletions
- No reachability claims beyond observed edges
- No references to unopened files (except when noting unresolved targets as strings)

---

## Operation: PRUNE-SUITE: RUN (optional)

**Goal:** Convenience loop to finish all todo work items.

**Behavior:**

Repeatedly execute STEP until no todo items remain.

If the agent cannot guarantee context stability, do not use RUN.

**Stop.**

---

## Operation: PRUNE-SUITE: VERIFY

**Goal:** Compute reachability from entrypoints and produce deletion candidates.

**Steps:**

1. **Load:**
   - `temp/prune-manifest.json`
   - `temp/prune-graph.json`
   - `temp/prune-config.json`

2. **Build reachability set:**
   - Start from all entrypoints (detected + overrides)
   - Traverse graph edges to mark reachable files/nodes as USED
   - Include config chain inheritance (tsconfig extends, etc.)

3. **Apply workspace logic:**
   - If workspaces enabled, treat each package's entrypoints as roots
   - Mark internal package dependencies as USED

4. **Classify each repo file:**

   **USED:**
   - Reachable from entrypoints, OR
   - Referenced by reachable config/assets, OR
   - Referenced via high-confidence dynamic loader evidence, OR
   - Matches `protectedPaths`, OR
   - Covered by `dynamicPatterns` with `markAsUsed: true`, OR
   - Config file that extends/inherits from a USED config

   **UNUSED:**
   - Not reachable AND
   - No inbound edges from reachable nodes AND
   - Not an entrypoint AND
   - Not protected AND
   - Not ambiguous

   **AMBIGUOUS:**
   - Only referenced by low-confidence dynamic patterns
   - Runtime reflection patterns detected without concrete targets
   - Glob loads where file matching cannot be proven
   - Files with `eval()`, `new Function()`, `__import__` detected

   **PROTECTED:**
   - Matches `protectedPaths` from config
   - Migrations, schemas, seed data
   - Infrastructure (CI workflows, Docker, K8s)
   - Shared configs in monorepos

5. **Test file special handling:**
   - If `treatTestsAsEntrypoints = false`:
     - Mark test files as UNUSED unless referenced by non-test code
     - Exception: Test utilities marked USED if any test is reachable

6. **Sanity check:**
   - If >20% of repo is UNUSED: flag for manual review (likely missing entrypoints)
   - If >50% of source files are UNUSED in a mature repo: **HIGH RISK – likely incomplete analysis**

7. **Write:**
   - `temp/prune-candidates.json`
   - `reports/prune-deletion-plan.md`
   - `reports/prune-summary.md` (updated with counts + risk)

**Deletion plan must include per file:**
````json
{
  "path": "src/old-utils.ts",
  "classification": "unused",
  "reason": "No inbound edges, not reachable from any entrypoint",
  "evidence": {
    "graphTraversal": "Not in reachable set from entrypoints",
    "inboundEdges": 0,
    "isEntrypoint": false,
    "matchesProtected": false
  },
  "risk": "low",
  "loc": 156,
  "lastModified": "2023-08-15",
  "suggestedAction": "delete"
}
````

**Stop.**

---

## Operation: PRUNE-SUITE: DRY-RUN

**Goal:** Preview deletion impact without making changes.

**Steps:**

1. **Load:**
   - `temp/prune-candidates.json`
   - `temp/prune-manifest.json`

2. **Generate impact report:**
   - Total files to delete
   - Total LOC to remove
   - Disk space reclamation estimate
   - Breakdown by category (source/test/doc/other)

3. **Highlight top deletions:**
   - Top 10 largest files marked UNUSED
   - Recently modified files (within 30 days) marked UNUSED – **FLAG AS SURPRISING**
   - Any files >1000 LOC marked UNUSED – **FLAG FOR REVIEW**

4. **Risk summary:**
   - Count by risk level (low/medium/high)
   - List all HIGH risk deletions

5. **Comparison check:**
   - If deleting >30% of source files: **WARNING**
   - If deleting any files modified in last 7 days: **CAUTION**

6. **Write:**
   - `reports/prune-dry-run.md`

**Stop.**

**Dry-run report format:**
````markdown
# PRUNE-SUITE Dry Run Report

## Impact Summary
- Files to delete: 87
- LOC to remove: 12,456
- Estimated disk savings: ~2.3 MB

## Breakdown by Category
- Source: 23 files (3,456 LOC)
- Test: 45 files (6,789 LOC)
- Doc: 12 files (1,234 LOC)
- Other: 7 files (977 LOC)

## Risk Distribution
- Low risk: 78 files ✅
- Medium risk: 7 files ⚠️
- High risk: 2 files 🚨

## Surprising Deletions (review recommended)
- ⚠️ src/analytics.ts (1,245 LOC, modified 12 days ago)
- 🚨 src/payment-processor.ts (856 LOC, modified 3 days ago) – **HIGH RISK**

## Top 10 Largest Deletions
1. test/legacy-suite.spec.ts (2,134 LOC)
2. src/analytics.ts (1,245 LOC)
3. ...

**Proceed to APPLY only after manual review of HIGH and MEDIUM risk items.**
````

---

## Operation: PRUNE-SUITE: APPLY (optional destructive)

**Goal:** Apply deletion plan safely (never hard-delete without backup).

**IMPORTANT:** Only run after human review of DRY-RUN report.

**Steps:**

1. **Require explicit confirmation:**
   The user prompt MUST include the exact phrase:
````
   CONFIRM DELETE
````
   If missing, output: "Deletion aborted. Include 'CONFIRM DELETE' to proceed." and **STOP**.

2. **Load:**
   - `reports/prune-deletion-plan.md`
   - `temp/prune-candidates.json`

3. **Create backup:**
   - Archive path: `archive/prune_backup_<timestamp>/`
   - Preserve full directory structure

4. **For each file marked UNUSED with risk=low:**
   - Copy to archive preserving path structure
   - Verify copy succeeded
   - Delete from working tree only after successful copy

5. **Do NOT delete:**
   - Anything with `classification: ambiguous`
   - Anything with `classification: protected`
   - Anything with `risk: medium` or `risk: high` (unless user adds override)
   - Anything not explicitly listed as `unused` + `low` risk

6. **After completion:**
   - Run basic project health check (if possible):
     - `npm run build` (if Node.js)
     - `pytest --collect-only` (if Python)
     - Compile check (if Rust/Go)
   - If health check fails: **WARN** user but don't auto-rollback

7. **Update reports:**
   - Record what was moved/deleted
   - Record timestamp + archive path
   - Add rollback instructions to `reports/prune-summary.md`

8. **Generate rollback script:**
   - Create `archive/prune_backup_<timestamp>/ROLLBACK.sh` (or `.ps1` for Windows)
   - Script to restore all deleted files

**Stop.**

**Post-deletion summary:**
````markdown
# Deletion Complete

## What was deleted
- 78 files removed (10,234 LOC)
- Backup location: archive/prune_backup_20250125_143022/

## Rollback available
To restore deleted files:
```bash
# Unix/Mac
./archive/prune_backup_20250125_143022/ROLLBACK.sh

# Windows
.\archive\prune_backup_20250125_143022\ROLLBACK.ps1
```

## Health check
- ✅ Build passed
- ✅ Tests still runnable

**Recommendation:** Run full test suite and verify app functionality before committing.
````

---

## Safety defaults

- **Never delete ambiguous files.**
- **Never delete migrations/schemas/seeds by default.**
- **Never delete infrastructure configs by default.**
- **Prefer false negatives over false positives.**
- **If >20% of repo ends up UNUSED, flag for manual review** (likely missing entrypoints).
- **If >50% of source files marked UNUSED in mature repo, abort with warning.**
- **Recently modified files (< 7 days) marked UNUSED should be flagged as HIGH RISK.**

---

## Recommended workflows

### Full audit (safe):
````
PRUNE-SUITE: RESET-FULL
PRUNE-SUITE: VALIDATE
PRUNE-SUITE: RUN (or repeated STEP)
PRUNE-SUITE: VERIFY
PRUNE-SUITE: DRY-RUN
````

Then (after manual review of dry-run report):
````
PRUNE-SUITE: APPLY
(with CONFIRM DELETE in prompt)
````

### Incremental audit:
````
PRUNE-SUITE: INIT
PRUNE-SUITE: VALIDATE
PRUNE-SUITE: RUN
PRUNE-SUITE: VERIFY
PRUNE-SUITE: DRY-RUN
````

### Quick check (no deletion):
````
PRUNE-SUITE: INIT
PRUNE-SUITE: VALIDATE
PRUNE-SUITE: RUN
PRUNE-SUITE: VERIFY
````
Review `reports/prune-summary.md` for insights.

---

## Framework-Specific Notes

### Next.js
- **Entrypoints:** All files in `pages/`, `app/*/page.tsx`, `app/*/route.ts`, `middleware.ts`
- **Convention-based imports:** Public folder assets, API routes
- **Common pitfall:** Dynamic routes (`[id].tsx`) may not show static imports

### Express/Fastify
- **Entrypoints:** Main server file, route loaders
- **Common pitfall:** Route files loaded via `fs.readdirSync('routes/')` won't show static edges
- **Solution:** Add `dynamicPatterns` for route directories

### Django
- **Entrypoints:** `manage.py`, `wsgi.py`, `urls.py`, view files
- **Convention-based:** Template references, static files
- **Common pitfall:** `{% include 'template.html' %}` in templates

### Monorepos (Turborepo, Nx, Lerna)
- **Enable workspaces in config**
- **Each package is a sub-graph**
- **Internal dependencies** (e.g., `@myorg/shared`) must be resolved

---

## Version History

**v2.0** (Current)
- Added VALIDATE operation for pre-flight checks
- Added DRY-RUN operation for impact preview
- Added prune-config.json for user overrides
- Added framework detection and convention-based entrypoints
- Added workspace/monorepo support
- Enhanced evidence format with structured metadata
- Added test file special handling
- Added config chain resolution (extends, inheritance)
- Added rollback script generation
- Improved safety checks and sanity thresholds

**v1.0**
- Initial spec with basic graph traversal