# Discrepancy Log - 2026-01-12

| ID | Severity | Location | Description | Status |
|---|---|---|---|---|
| D-001 | Info | `web/prisma/schema.prisma` | Missing `url` in schema file. Initially flagged as Critical. | **False Positive** - Project uses Prisma 7 `prisma.config.ts`. State is valid. |
| D-002 | Minor | Documentation | None | N/A |