# Troubleshooting Guide

Common gotchas and debugging tips for the Edinburgh Finds project.

---

## 1. Lens Implementation is Incomplete

**Problem:** The canonical dimension extraction system is partially implemented. Extractors currently don't populate `canonical_activities`, `canonical_roles`, `canonical_place_types`, or `canonical_access` arrays from lens mapping rules.

**Details:** See `docs/target-architecture.md` Section 4 (Orchestration Pipeline) for the full pipeline specification.

**Current Workaround:** Manual population or extraction logic until lens-driven extraction is wired up. The system requires at least one "perfect entity" flowing end-to-end through the complete pipeline (see `docs/system-vision.md` Section 6.3).

---

## 2. Schema Changes Require Regeneration

**Problem:** You modified a YAML schema but your changes aren't reflected in Python/Prisma/TypeScript.

**Solution:**
```bash
python -m engine.schema.generate --all  # Must regenerate Python/Prisma/TypeScript
```

**Important:** Never manually edit generated files - they have "DO NOT EDIT" headers and will be overwritten.

---

## 3. Tests Use CI=true for Non-Interactive Mode

**Frontend tests hang in watch mode:**
```bash
CI=true npm test  # Frontend: Prevents watch mode
```

**Backend tests are already non-interactive:**
```bash
pytest  # Backend: Already non-interactive
```

---

## 4. Entity Class vs. Vertical-Specific Types

**Wrong approach (vertical-specific):**
```python
if entity_type == "Venue":  # ❌ Vertical-specific
    ...
```

**Correct approach (universal):**
```python
if entity.entity_class == "place":  # ✅ Universal
    # Use lenses/modules for vertical interpretation
```

**Why:** The engine must remain domain-agnostic. All vertical semantics belong in Lens YAML configs.

---

## 5. Pytest Markers for Test Performance

**Problem:** Tests are slow during development iteration.

**Solution - Run fast tests only:**
```bash
pytest -m "not slow"  # Fast tests only (for quick iteration)
```

**For comprehensive testing:**
```bash
pytest  # All tests (some slow)
```

**How to mark slow tests:**
```python
@pytest.mark.slow
def test_expensive_operation():
    ...
```

---

## 6. Orchestration Registry

**Problem:** Adding a new connector and it's not being recognized.

**Solution - Three-step checklist:**
1. Add to `engine/orchestration/registry.py` with `ConnectorSpec` (cost, trust, phase, timeout)
2. Add adapter mapping in `engine/orchestration/adapters.py`
3. Write tests in `tests/engine/orchestration/test_registry.py`

**Why:** The orchestration system uses a registry-driven architecture. All connectors must be explicitly registered with metadata.

---

## 7. Git Workflow Issues

### Pre-commit hooks failing

**Problem:** Commit fails due to pre-commit hook.

**Wrong approach:**
```bash
git commit --no-verify  # ❌ Bypasses safety checks
```

**Correct approach:**
1. Fix the issue the hook identified
2. Re-stage files: `git add <files>`
3. Create a NEW commit (don't amend unless explicitly requested)

**Why:** Pre-commit hooks catch architectural violations and code quality issues. Bypassing them can introduce defects.

### Accidentally committed secrets

**Problem:** You committed `.env` or credentials.

**Immediate action:**
1. `git reset --soft HEAD~1` (undo commit, keep changes)
2. Add file to `.gitignore`
3. Verify with `git status`
4. Commit again without sensitive files

**Why:** Secrets in git history can't be fully removed without rewriting history.

---

## Testing Strategy

### Unit Tests
- Every module must have corresponding tests
- Mock external dependencies (API calls, LLM calls)
- Test both success and failure cases
- Use fixtures for common setup

### Integration Tests
- Test complete data flows (ingest → extract → dedupe → merge)
- Verify database transactions
- Snapshot testing for extraction outputs

### Coverage Requirements
```bash
pytest --cov=engine --cov-report=html  # Generate HTML coverage report
# Target: >80% coverage for all modules
```

---

## Getting Help

- **Architectural questions:** Read `docs/system-vision.md` first
- **Process questions:** Read `docs/development-methodology.md`
- **Implementation details:** Check `docs/target-architecture.md`
- **Test examples:** Browse `tests/engine/` for patterns and fixtures
