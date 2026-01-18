# Plan: Prisma Schema Generation

## Phase 1: Analysis & Templating
- [x] **Audit Models**: Compare `engine/schema.prisma` and `web/prisma/schema.prisma` to identify all "Infrastructure Models" (those not generated from `listing.yaml`).
- [x] **Create Template**: Extract these infrastructure models (e.g., `RawIngestion`, `FailedExtraction`, `MergeConflict`) into a static definition string or a separate `core_schema.prisma` template file.
- [x] **Define Mappings**: Map YAML types (`string`, `float`, `boolean`, `list[string]`, etc.) to Prisma types. Note handling for SQLite limitations (e.g., lists usually stored as strings/JSON).

## Phase 2: Generator Implementation
- [x] **Create Generator Class**: Implement `PrismaGenerator` in `engine/schema/generators/prisma.py`.
    -   Method `generate_model(schema: Schema)`: Converts a YAML-derived schema to a Prisma `model Block {}`.
    -   Method `generate_full_schema(schemas: List[Schema], target: 'web' | 'engine')`: Assembles the full file including headers (`datasource`, `generator`) and infrastructure models.
- [x] **Handle Configuration**: Ensure the generator respects target-specific settings (e.g., `generator client` provider).

## Phase 3: Integration
- [x] **Update CLI**: Modify `engine/schema/cli.py` to include the Prisma generation step.
    -   Default to generating both unless specified.
    -   Add `--prisma` flag if we want to isolate it.
- [x] **Regenerate**: Run the tool to overwrite existing `schema.prisma` files.

## Phase 4: Verification
- [x] **Diff Check**: Verify the generated files contain all necessary models (especially `MergeConflict`).
- [x] **Client Generation**: Run `npx prisma generate` (Web) and `prisma generate` (Python) to ensure validity.
- [x] **Test**: Run `pytest` to ensure no regression in DB access.

**Test Results:**
- All 144 schema-related tests pass (100% success rate)
- Prisma generator: 35/35 tests pass
- Schema sync: 12/12 tests pass
- Schema utils: 8/8 tests pass
- Schema parser: 19/19 tests pass
- Python generator: 30/30 tests pass
- Pydantic extraction generator: 13/13 tests pass
- TypeScript generator: 27/27 tests pass
- No regressions detected in DB access or schema functionality
