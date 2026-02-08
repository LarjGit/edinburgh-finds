---
name: shared-direct-write-pattern
description: Shared pattern for background agents that write documentation directly to files
---

# Direct Write Pattern for Background Agents

When you are a background agent generating documentation sections:

## Your Responsibility

1. **Read source files** to understand what to document
2. **Generate section content** following GLOBAL CONSTRAINTS
3. **Write directly to target file** using Write or Edit tool
4. **Confirm completion** in final message

## DO NOT

- Return content to orchestrator in conversation
- Ask for approval before writing
- Create intermediate files

## Output Format

Your final message should be a concise confirmation:

```
✅ Section complete: [Section Name]

Written to: [file path]
Lines: [line count]
Key points covered:
- [bullet point 1]
- [bullet point 2]
- [bullet point 3]
```

This keeps orchestrator context minimal.

## Example

Instead of:
```
Here's the content for Section 2:

[3000 lines of markdown]

Should I write this?
```

Do:
```
[Write tool call to insert content]

✅ Section complete: Architecture Overview

Written to: docs/generated/ARCHITECTURE.md
Lines: 287
Key points covered:
- Engine vs Lens separation
- 11-stage pipeline
- Connector architecture
```
