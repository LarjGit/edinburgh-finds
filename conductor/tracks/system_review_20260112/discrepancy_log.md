# Discrepancy Log - 2026-01-12

| ID | Severity | Location | Description | Expected | Actual |
|---|---|---|---|---|---|
| D-001 | **CRITICAL** | `web/prisma/schema.prisma` | Missing Database URL configuration | `url = env("DATABASE_URL")` inside `datasource db` block | `url` property is missing |
| D-002 | Minor | Documentation | None | N/A | N/A |
