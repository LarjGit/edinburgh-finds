---
name: shared-context-budget
description: Shared context budget rules for all documentation agents to prevent context bloat
---

# Context Budget Rules

All agents must respect these limits to prevent context bloat in the orchestrator.

## Hard Limits

- **Outline response**: 50 lines max
- **Section content**: 400 lines max
- **Patch content**: 300 lines max per patch
- **Diagram**: 150 lines max
- **GLOBAL CONSTRAINTS**: 100 lines max

## Orchestrator Budget

At any moment, orchestrator context contains:
- GLOBAL CONSTRAINTS: ~100 lines
- Current outline: ~50 lines
- Current section being written: ~400 lines
- **Total: ~550 lines maximum**

This scales to unlimited doc size because we process incrementally.

## Why These Limits?

Without these limits, the orchestrator accumulates full documents in context, defeating the purpose of using subagents.

### Problem (Before):
```
Orchestrator calls doc agent
→ Agent returns 3000-line document
→ Orchestrator context grows by 3000 lines
→ For 10 docs = 30,000 lines in context
→ Context bloat, degraded performance, higher costs
```

### Solution (After):
```
Orchestrator calls doc agent for outline
→ Agent returns 50-line outline
→ Orchestrator context: +50 lines

Orchestrator calls doc agent for each section
→ Agent returns 400-line section
→ Orchestrator replaces placeholder with content
→ Context grows by 400 lines per section
→ But only ONE section in working memory at a time

For 10 docs × 5 sections = 50 total calls
→ Peak context per iteration: ~550 lines
→ Total generated: 20,000+ lines
→ Context stays lean throughout
```

## Enforcement

If a subagent exceeds limits:
1. Orchestrator truncates the response at the limit
2. Logs a warning to CHANGELOG.md
3. Requests rewrite with explicit line count reminder

Example:
```
WARNING: architecture-docs exceeded section limit
Requested: section "System Overview"
Returned: 487 lines (limit: 400)
Action: Truncated to 400 lines, requested rewrite
```

## Benefits

1. **Scalability**: Generate docs of any size without context explosion
2. **Performance**: Faster processing with smaller working sets
3. **Cost**: Lower token costs from reduced context
4. **Reliability**: Less risk of hitting model context limits
5. **Modularity**: Each section is independent and reviewable

## Implementation Notes

### For Doc Agents

When you receive `task: "section: X"`:
- Focus ONLY on that section
- Stay under 400 lines
- Reference but don't repeat other sections
- Use diagrams efficiently (reference, don't duplicate)

### For Orchestrator

When calling doc agents:
- Call outline first (one call per doc)
- Create skeleton from outline
- Fill sections one at a time (N calls per doc)
- Never accumulate multiple sections in memory
- Process linearly: outline → section 1 → section 2 → ...

### For Review Agent

When reviewing:
- Review ONE doc at a time
- Return patches, not full rewrites
- Max 300 lines per patch
- Be surgical, not comprehensive
