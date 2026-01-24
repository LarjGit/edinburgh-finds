\# PRUNE-SUITE (Universal) — Repository Dead-Code Pruning Engine



Audience: Developers



This spec is designed to run on Gemini, Claude, and Codex with the SAME instructions.

It avoids context exhaustion by using disk-backed state and atomic steps.



How to run (same for all agents)



Tell the agent to execute one operation at a time using these exact phrases:



PRUNE-SUITE: RESET-FULL

PRUNE-SUITE: INIT

PRUNE-SUITE: STEP

PRUNE-SUITE: RUN (optional convenience loop)

PRUNE-SUITE: VERIFY

PRUNE-SUITE: APPLY (optional destructive)



Important: STEP must produce exactly ONE output, then stop.



Hard rules (non-negotiable)



Atomic: STEP produces exactly ONE analysis output, then stops.



No chaining: After producing a STEP result and updating the manifest/graph, you MUST return a text response immediately. Do not start the next work item until the user provides a new prompt.



Limits:



MAX\_FILES\_PER\_STEP = 25

MAX\_LOC\_PER\_STEP = 2500

If exceeded, split into chunks.



Disk is truth:



Always read/write:

temp/prune-manifest.json

temp/prune-graph.json

temp/prune-candidates.json



Conservative by default:



If reachability is uncertain -> treat as USED (never delete).

Only mark UNUSED when evidence is strong.



Evidence is bounded (cheap citations):



Cite only technical claims (imports, edges, entrypoints, loaders, config references).

Cite only from files opened in that STEP OR from prune-graph.json traversal results.

Format: Evidence: path:line-range (or graph: node/edge)



No speculation:



If you didn’t open it in this step, you can’t claim it (except for graph traversal results).

No invented behavior, no assumptions about runtime.



Read-only by default:



Nothing is deleted until PRUNE-SUITE: APPLY is explicitly executed.



Platform note



Prefer PowerShell-compatible commands on Windows.

Do not assume bash, rg, grep, sed, or awk are installed.

Git may be used when available.



Output structure



temp/

&nbsp; prune-manifest.json

&nbsp; prune-graph.json

&nbsp; prune-candidates.json



reports/

&nbsp; prune-summary.md

&nbsp; prune-deletion-plan.md



archive/

&nbsp; prune\_backup\_YYYYMMDD\_HHMMSS/



--------------------------------------------------------------------------------

Operation: PRUNE-SUITE: RESET-FULL



Goal: Remove legacy prune artifacts and start a clean full audit.



Steps:



1\) If temp/ or reports/ outputs exist, archive them to:

&nbsp;  archive/prune\_backup\_<timestamp>/



2\) Delete these files if they exist:

&nbsp;  temp/prune-manifest.json

&nbsp;  temp/prune-graph.json

&nbsp;  temp/prune-candidates.json

&nbsp;  reports/prune-summary.md

&nbsp;  reports/prune-deletion-plan.md



3\) Recreate empty folders:

&nbsp;  temp/

&nbsp;  reports/

&nbsp;  archive/



4\) Then execute PRUNE-SUITE: INIT.



Stop.



Result: Guaranteed no lingering prune state.



--------------------------------------------------------------------------------

Operation: PRUNE-SUITE: INIT



Goal: Create repo inventory + entrypoint roots without deep reading.



Steps:



1\) Inventory all files in the repo, excluding:

&nbsp;  .git/, node\_modules/, dist/, build/, archive/, generated artifacts, docs outputs.



2\) Classify each file as:

&nbsp;  source | config | asset | script | test | doc | other



3\) Detect entrypoints (roots) using metadata-first heuristics:



&nbsp;  - package.json: main, bin, exports, scripts

&nbsp;  - Python: \_\_main\_\_.py, main.py, pyproject console\_scripts

&nbsp;  - Dockerfile: CMD / ENTRYPOINT

&nbsp;  - CI workflows: GitHub Actions, GitLab CI, etc.

&nbsp;  - Server bootstrap patterns (e.g., app/server index files)

&nbsp;  - README quickstart commands (light scan only)



4\) For source/config files collect:

&nbsp;  - LOC

&nbsp;  - lightweight imports/require from headers/signatures only (best effort)

&nbsp;  - file role guess: entrypoint | library | config | asset | unknown



5\) Chunk inventory into work items respecting:

&nbsp;  <= MAX\_FILES\_PER\_STEP

&nbsp;  <= MAX\_LOC\_PER\_STEP



6\) Write:

&nbsp;  temp/prune-manifest.json

&nbsp;  temp/prune-graph.json (initial, may contain only roots)

&nbsp;  reports/prune-summary.md (inventory + detected entrypoints)



Stop. INIT must not do full dependency traversal.



Minimum manifest requirements:



limits

inventory summary

entrypoints\[]

files map:

&nbsp; kind, loc, optional sha256, subsystem(optional), chunk\_id, quick\_imports(optional)

work.queue\[]:

&nbsp; work\_id, chunk\_id, files\[], status(todo/doing/done/blocked)



--------------------------------------------------------------------------------

Operation: PRUNE-SUITE: STEP



Goal: Analyze exactly ONE queued chunk and extend the reachability graph.



Steps:



1\) Load temp/prune-manifest.json and temp/prune-graph.json.



2\) Select next work item with status = todo.



3\) Mark it doing and persist manifest immediately.



4\) Open only the files listed for that work item.



5\) Extract edges (best effort, language-appropriate):

&nbsp;  - static imports / requires

&nbsp;  - dynamic imports where detectable

&nbsp;  - plugin registration / router registration

&nbsp;  - config references (keys/files)

&nbsp;  - file path loads (templates, SQL, JSON, YAML, migrations)

&nbsp;  - asset references (images/css, etc.)



6\) For each edge record:

&nbsp;  from, to, edge\_type, confidence(high/med/low), evidence(path:line-range)



7\) Append edges into temp/prune-graph.json.



8\) Update manifest:

&nbsp;  mark work item done

&nbsp;  store updated hashes (optional)



9\) Terminate turn immediately with:

&nbsp;  - chunk analyzed

&nbsp;  - number of edges added

&nbsp;  - any ambiguous/dynamic patterns detected



Stop.



Prohibitions:



No deletions

No reachability claims beyond observed edges

No references to unopened files (except when noting unresolved targets as strings)



--------------------------------------------------------------------------------

Operation: PRUNE-SUITE: RUN (optional)



Goal: Convenience loop to finish all todo work items.



Behavior:



Repeatedly execute STEP until no todo items remain.

If the agent cannot guarantee context stability, do not use RUN.



Stop.



--------------------------------------------------------------------------------

Operation: PRUNE-SUITE: VERIFY



Goal: Compute reachability from entrypoints and produce deletion candidates.



Steps:



1\) Load:

&nbsp;  temp/prune-manifest.json

&nbsp;  temp/prune-graph.json



2\) Traverse graph from entrypoints to mark reachable files/nodes as USED.



3\) Classify each repo file:



&nbsp;  USED:

&nbsp;    - reachable from entrypoints, OR

&nbsp;    - referenced by reachable config/assets, OR

&nbsp;    - referenced via high-confidence dynamic loader evidence



&nbsp;  UNUSED:

&nbsp;    - not reachable AND

&nbsp;    - no inbound edges from reachable nodes AND

&nbsp;    - not an entrypoint AND

&nbsp;    - not marked protected (see Safety) AND

&nbsp;    - not ambiguous



&nbsp;  AMBIGUOUS:

&nbsp;    - only referenced by low-confidence dynamic patterns

&nbsp;    - runtime reflection patterns detected without concrete targets

&nbsp;    - glob loads where file matching cannot be proven



&nbsp;  PROTECTED:

&nbsp;    - migrations, schemas, seed data, infra (unless explicitly scoped)

&nbsp;    - anything under tools/ used by CI

&nbsp;    - files matching ignore-protect list



4\) Write:

&nbsp;  temp/prune-candidates.json

&nbsp;  reports/prune-deletion-plan.md

&nbsp;  reports/prune-summary.md (updated with counts + risk)



Deletion plan must include per file:



\- path

\- classification (unused/ambiguous/protected)

\- reason

\- evidence (graph + file citations)

\- risk level (low/med/high)

\- suggested action (delete | review | keep)



Stop.



--------------------------------------------------------------------------------

Operation: PRUNE-SUITE: APPLY (optional destructive)



Goal: Apply deletion plan safely (never hard-delete without backup).



IMPORTANT: Only run after human review.



Steps:



1\) Require the user prompt to include the exact phrase:

&nbsp;  CONFIRM DELETE



If missing, do nothing and stop.



2\) Read reports/prune-deletion-plan.md and temp/prune-candidates.json.



3\) For each file marked UNUSED with risk=low:

&nbsp;  - Move it to archive/prune\_backup\_<timestamp>/ (preserve paths)

&nbsp;  - Delete from working tree after successful move



4\) Do NOT delete:

&nbsp;  - ambiguous

&nbsp;  - protected

&nbsp;  - anything not explicitly listed as UNUSED + low risk



5\) Update reports:

&nbsp;  - record what was moved/deleted

&nbsp;  - record timestamp + archive path



Stop.



--------------------------------------------------------------------------------

Safety defaults



\- Never delete ambiguous files.

\- Never delete migrations/schemas/seeds by default.

\- Never delete infra configs by default.

\- Prefer false negatives over false positives.

\- If >20% of repo ends up UNUSED, flag for manual review (likely missing entrypoints).



Recommended workflows



Full audit (safe):



PRUNE-SUITE: RESET-FULL

PRUNE-SUITE: RUN (or repeated STEP)

PRUNE-SUITE: VERIFY



Then (after review):



PRUNE-SUITE: APPLY  (with CONFIRM DELETE)



Incremental audit:



PRUNE-SUITE: INIT

PRUNE-SUITE: RUN

PRUNE-SUITE: VERIFY



