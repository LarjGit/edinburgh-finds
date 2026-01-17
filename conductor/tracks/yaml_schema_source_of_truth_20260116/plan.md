# Track: YAML Schema - Single Source of Truth - Implementation Plan

## Overview

This plan details the phased implementation of YAML-based schema generation to eliminate schema drift and enable horizontal scaling. Each phase builds incrementally toward a complete, production-ready schema management system.

**Implementation Philosophy:** Test-Driven Development (TDD) - Write tests first, implement to pass, refactor for quality.

---

## Phase 1: YAML Schema Format & Parser

**Goal:** Define YAML schema format and build parser with validation

### Tasks

- [x] Research existing schema formats (JSON Schema, OpenAPI) for inspiration
- [x] Design YAML schema format with all required metadata fields
- [x] Write example `listing.yaml` with 3-5 fields as proof of concept
- [x] Write tests for YAML parser (`test_schema_parser.py`)
- [x] Implement `parser.py` - parse YAML to internal SchemaDefinition objects
- [x] Add validation: required fields, valid types, constraint checks
- [x] Write tests for validation edge cases (missing fields, invalid types)
- [x] Test parser with malformed YAML (should fail gracefully)

**Success Criteria:**
- ✅ YAML format documented with examples
- ✅ Parser loads and validates YAML files
- ✅ SchemaDefinition objects have all necessary metadata
- ✅ Validation catches common errors
- ✅ Test coverage >90% for parser

**Phase Checkpoint:** YAML format finalized, parser tested

**Phase 1 Status:** ✅ COMPLETE

**Completion Details:**
- Created YAML schema format in `engine/config/schemas/listing.yaml`
- Implemented parser in `engine/schema/parser.py`
- Created comprehensive test suite: 19 tests, all passing
- Parser supports: field type validation, required field checks, malformed YAML handling
- Supported types: string, integer, float, boolean, datetime, json, list[T]
- Test coverage: 100% of parser functionality
- **Naming convention:** listing.yaml → listing.py, venue.yaml → venue.py

---

## Phase 2: Python FieldSpec Generator

**Goal:** Generate Python listing.py from YAML

### Task 2.1: Generator Infrastructure

- [x] Write tests for Python generator (`test_python_generator.py`)
- [x] Create `generators/python_fieldspec.py` module
- [x] Implement type mapping: YAML types → Python type annotations
  - `string` → `str` or `Optional[str]`
  - `integer` → `int` or `Optional[int]`
  - `float` → `float` or `Optional[float]`
  - `boolean` → `bool` or `Optional[bool]`
  - `json` → `Dict[str, Any]` or `Optional[Dict[str, Any]]`
  - `list[string]` → `List[str]` or `Optional[List[str]]`
- [x] Implement nullable handling (nullable: true → Optional[...])
- [x] Test type mapping with all supported types

### Task 2.2: FieldSpec Generation

- [x] Write tests for FieldSpec generation
- [x] Implement FieldSpec object generation from YAML fields
- [x] Handle all FieldSpec attributes:
  - name, type_annotation, description
  - nullable, required, index, unique
  - search_category, search_keywords
  - exclude, primary_key, foreign_key
  - default values
- [x] Generate Python imports (Optional, List, Dict, etc.)
- [x] Test generated FieldSpecs match manual ones

### Task 2.3: File Generation

- [x] Write tests for complete file generation
- [x] Generate Python module header (imports, docstring)
- [x] Generate LISTING_FIELDS list with all FieldSpecs
- [x] Add "GENERATED FILE - DO NOT EDIT" warning
- [x] Add generation timestamp and source YAML path
- [x] Format output with black or autopep8
- [x] Test generated listing.py imports and runs correctly
- [x] Compare generated listing.py to current manual version

### Task 2.4: Entity-Specific Schemas

- [x] Write tests for venue-specific field generation
- [x] Implement schema inheritance (venue extends listing)
- [x] Generate VENUE_SPECIFIC_FIELDS list
- [x] Test generated venue.py matches manual version

**Success Criteria:**
- ✅ Generate listing.py from listing.yaml (exact match to manual)
- ✅ Generate venue.py from venue.yaml (exact match to manual)
- ✅ Generated files are valid Python, import correctly
- ✅ All FieldSpec attributes preserved
- ✅ Test coverage >90% for generator

**Phase Checkpoint:** Python generation working for existing schemas

**Phase 2 Status:** ✅ COMPLETE

**Completion Details:**
- Created comprehensive test suite: 32 tests, all passing
- Implemented PythonFieldSpecGenerator with full type mapping
- Generator supports: all YAML types, nullable handling, search metadata, sa_column, schema inheritance
- Generated files include: header comments, imports, generation timestamp, proper formatting
- Schema inheritance working: Venue extends Listing, generates VENUE_SPECIFIC_FIELDS
- Test coverage: 100% of generator functionality
- Created venue.yaml as proof of concept for inheritance

---

## Phase 3: Prisma Schema Generator

**Goal:** Generate schema.prisma from YAML

### Task 3.1: Prisma Type Mapping

- [ ] Write tests for Prisma type mapping (`test_prisma_generator.py`)
- [ ] Create `generators/prisma.py` module
- [ ] Implement type mapping: YAML types → Prisma types
  - `string` → `String` (with `?` if nullable)
  - `integer` → `Int`
  - `float` → `Float`
  - `boolean` → `Boolean`
  - `json` → `String` (SQLite) or `Json` (PostgreSQL)
  - `datetime` → `DateTime`
- [ ] Handle nullable: `nullable: true` → `String?` in Prisma
- [ ] Test type mapping with all supported types

### Task 3.2: Model Generation

- [ ] Write tests for Prisma model generation
- [ ] Generate model definition: `model Listing { ... }`
- [ ] Generate field definitions with correct syntax
- [ ] Add field attributes:
  - `@id` for primary keys
  - `@unique` for unique fields
  - `@default(cuid())` for auto-generated IDs
  - `@default(now())` for timestamps
- [ ] Generate indexes: `@@index([field_name])`
- [ ] Add comments for documentation
- [ ] Test generated model syntax is valid Prisma

### Task 3.3: Complete Schema Generation

- [ ] Generate Prisma schema header (generator, datasource)
- [ ] Generate all models (Listing, ExtractedListing, etc.)
- [ ] Generate enums (EntityType - if using PostgreSQL)
- [ ] Generate relationships between models
- [ ] Add "GENERATED FILE - DO NOT EDIT" warning comment
- [ ] Format output with consistent indentation
- [ ] Validate with `prisma format` command
- [ ] Compare generated schema.prisma to current manual version

### Task 3.4: Database-Specific Handling

- [ ] Handle SQLite vs PostgreSQL differences
- [ ] SQLite: EntityType as String with comment
- [ ] PostgreSQL: EntityType as native enum
- [ ] JSON columns: String (SQLite) vs Json (PostgreSQL)
- [ ] Test generation for both database providers

**Success Criteria:**
- ✅ Generate schema.prisma from YAML (exact match to manual)
- ✅ Generated schema passes `prisma validate`
- ✅ Generated schema passes `prisma format`
- ✅ Handles SQLite and PostgreSQL differences
- ✅ All field attributes preserved (indexes, defaults, etc.)
- ✅ Test coverage >90% for generator

**Phase Checkpoint:** Prisma generation working, matches current schema

---

## Phase 4: YAML Migration & Validation

**Goal:** Convert existing schemas to YAML and validate

### Task 4.1: Create Base YAML Schema

- [ ] Audit current `listing.py` for all fields
- [ ] Create `engine/config/schemas/listing.yaml`
- [ ] Convert each LISTING_FIELDS entry to YAML
- [ ] Preserve all metadata (descriptions, search keywords, etc.)
- [ ] Validate YAML parses correctly
- [ ] Generate listing.py from YAML
- [ ] Diff generated vs manual listing.py (should match exactly)

### Task 4.2: Create Venue YAML Schema

- [ ] Audit current `venue.py` for all fields
- [ ] Create `engine/config/schemas/venue.yaml`
- [ ] Convert each VENUE_SPECIFIC_FIELDS entry to YAML
- [ ] Set up inheritance: `extends: listing`
- [ ] Validate YAML parses correctly
- [ ] Generate venue.py from YAML
- [ ] Diff generated vs manual venue.py (should match exactly)

### Task 4.3: Create Validation Tests

- [ ] Write `test_schema_sync.py` - validates all schemas match YAML
- [ ] Test: Parse listing.yaml → Generate listing.py → Compare to manual
- [ ] Test: Parse venue.yaml → Generate venue.py → Compare to manual
- [ ] Test: Parse listing.yaml → Generate schema.prisma → Compare to manual
- [ ] Test: Detect if manual files are edited (checksum validation)
- [ ] Run validation tests in CI
- [ ] Document how to run validation locally

### Task 4.4: Update schema_utils.py

- [ ] Update `get_extraction_fields()` to use generated schemas
- [ ] Ensure backward compatibility (same API)
- [ ] Test all extraction utilities still work
- [ ] Update imports if needed
- [ ] Run all extraction tests (89 tests should pass)

**Success Criteria:**
- ✅ listing.yaml and venue.yaml created
- ✅ Generated schemas match manual schemas exactly
- ✅ Validation tests pass
- ✅ All existing tests pass (89 extraction tests)
- ✅ No breaking changes to extraction engine

**Phase Checkpoint:** YAML schemas are source of truth, validation working

---

## Phase 5: CLI Tool & Automation

**Goal:** Create command-line tool for schema generation

### Task 5.1: CLI Implementation

- [ ] Create `engine/schema/cli.py` module
- [ ] Implement command: `python -m engine.schema.generate`
- [ ] Add flags:
  - `--validate`: Check schemas match YAML (exit 1 if drift)
  - `--force`: Overwrite existing files without prompt
  - `--output-dir`: Specify output directory
  - `--schema`: Generate specific schema (base, venue, etc.)
  - `--format`: Format generated files (prisma format, black)
- [ ] Add dry-run mode: show what would be generated
- [ ] Pretty-print output with colors (success=green, error=red)
- [ ] Add progress indicators for long operations
- [ ] Test CLI with all flags

### Task 5.2: Git Integration

- [ ] Add pre-commit hook suggestion (check schemas are in sync)
- [ ] Add git hook: detect manual edits to generated files
- [ ] Create `.gitattributes` marking generated files
- [ ] Document git workflow in README

### Task 5.3: CI Integration

- [ ] Add CI job: validate schemas on every push
- [ ] Fail CI if schemas drift from YAML
- [ ] Add CI job: regenerate schemas and check for changes
- [ ] Document CI setup for other projects

**Success Criteria:**
- ✅ CLI tool runs successfully
- ✅ `--validate` flag catches schema drift
- ✅ CI job validates schemas on push
- ✅ Git hooks prevent manual edits to generated files
- ✅ Documentation complete

**Phase Checkpoint:** Automated workflow established

---

## Phase 6: Documentation & Knowledge Transfer

**Goal:** Complete documentation for schema management

### Tasks

- [ ] Write `docs/schema_management.md` - comprehensive guide
  - Schema YAML format reference
  - Supported field types and attributes
  - How to add new fields
  - How to create new entity types
- [ ] Write `docs/adding_entity_type.md` - step-by-step tutorial
  - Create YAML file for new entity (e.g., winery.yaml)
  - Generate schemas
  - Update extraction engine
  - Test and validate
- [ ] Update ARCHITECTURE.md - document schema generation system
- [ ] Add inline code documentation (docstrings)
- [ ] Create example: French Vineyards (winery.yaml)
  - Define grape_varieties, appellation, etc.
  - Generate schemas
  - Document as proof of concept
- [ ] Record video walkthrough (optional)

**Success Criteria:**
- ✅ Documentation complete and accurate
- ✅ New developer can add entity type in <2 hours using docs
- ✅ Example winery.yaml demonstrates horizontal scaling
- ✅ ARCHITECTURE.md updated with schema generation section
- ✅ Code documentation >90% coverage

**Phase Checkpoint:** Knowledge transfer complete

---

## Phase 7: Replacement & Cleanup

**Goal:** Replace manual schemas with generated versions

### Tasks

- [ ] Backup current manual schemas (git tag: `pre-yaml-migration`)
- [ ] Run schema generation for all schemas
- [ ] Run full test suite (all 89+ extraction tests)
- [ ] Fix any issues discovered
- [ ] Replace manual listing.py with generated version
- [ ] Replace manual venue.py with generated version
- [ ] Mark manual schemas as DEPRECATED (add warnings)
- [ ] Update all imports to use generated schemas
- [ ] Remove manual schema files (after 1 sprint safety period)
- [ ] Update README.md with new schema workflow

**Success Criteria:**
- ✅ All schemas generated from YAML
- ✅ All tests pass (no regressions)
- ✅ Manual schemas removed
- ✅ Git history shows clean migration
- ✅ README updated

**Phase Checkpoint:** Migration complete, manual schemas retired

---

## Phase 8: TypeScript Generator (Optional - Nice to Have)

**Goal:** Generate TypeScript types for web app

### Tasks

- [ ] Research TypeScript type generation best practices
- [ ] Write tests for TypeScript generator (`test_typescript_generator.py`)
- [ ] Create `generators/typescript.py` module
- [ ] Implement type mapping: YAML types → TypeScript types
  - `string` → `string`
  - `integer` → `number`
  - `float` → `number`
  - `boolean` → `boolean`
  - `json` → `Record<string, any>`
  - nullable → `| null`
- [ ] Generate TypeScript interfaces
- [ ] Generate Zod schemas for validation (optional)
- [ ] Add to generation CLI
- [ ] Test in web app

**Success Criteria:**
- ✅ Generate TypeScript types from YAML
- ✅ Web app uses generated types
- ✅ Type safety maintained
- ✅ Frontend tests pass

**Phase Checkpoint:** Full-stack type safety from single source

---

## Success Metrics (Overall Track)

### Must-Have (Phases 1-7)

- [ ] Single YAML source defines all schemas
- [ ] Zero manual schema editing required
- [ ] Validation tests catch drift automatically
- [ ] CLI tool for generation and validation
- [ ] All existing tests pass (89+ extraction tests)
- [ ] Documentation enables self-service entity addition
- [ ] Example winery.yaml demonstrates horizontal scaling

### Nice-to-Have (Phase 8)

- [ ] TypeScript types generated
- [ ] Full-stack type safety
- [ ] Zod validation in frontend

---

## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Generator produces invalid schemas | Comprehensive tests, validate against Prisma/Python |
| Breaking existing functionality | Maintain backward compatibility, extensive testing |
| YAML format too complex | Keep simple, provide good examples and templates |
| Performance issues parsing YAML | Cache parsed schemas, only parse during generation |
| Generated files accidentally edited | Git hooks, CI validation, clear warnings |

---

## Checkpoints for User Verification

**After Phase 2:**
- Run: `python -m engine.schema.generate --schema=listing`
- Verify: Generated `listing.py` matches current manual version exactly
- Confirm: All imports work, no syntax errors

**After Phase 3:**
- Run: `python -m engine.schema.generate --schema=listing`
- Verify: Generated `schema.prisma` matches current manual version
- Confirm: `prisma validate` passes, `prisma format` shows no changes

**After Phase 4:**
- Run: `python -m pytest engine/tests/test_schema_sync.py`
- Verify: All validation tests pass
- Confirm: All extraction tests still pass (89 tests)

**After Phase 5:**
- Run: `python -m engine.schema.generate --validate`
- Verify: CLI reports all schemas in sync
- Confirm: CI job runs successfully

**After Phase 7:**
- Run full test suite: `python -m pytest engine/tests/`
- Verify: All tests pass with generated schemas
- Confirm: No manual schema files remain

---

## Definition of Done

A phase is complete when:

1. All tasks marked `[x]` complete
2. All tests passing (pytest with >90% coverage for new code)
3. Code passes linting and type checking
4. User verification checkpoint passed (if applicable)
5. Changes committed with proper message
6. Documentation updated
7. Plan.md updated with checkpoint notes

Track is complete when:

1. All 7 phases (1-7) marked complete
2. Must-have success metrics achieved
3. Documentation published
4. Example winery.yaml working
5. User acceptance confirmed

---

## Future Enhancements (Not in Scope)

These are valuable but deferred to future tracks:

- Schema versioning system with breaking change detection
- Schema registry service (API for dynamic retrieval)
- Runtime schema validation middleware
- Schema diffing and migration suggestions
- Multi-database schema generation (MongoDB, DynamoDB)
- GraphQL schema generation
- API documentation generation from schemas
