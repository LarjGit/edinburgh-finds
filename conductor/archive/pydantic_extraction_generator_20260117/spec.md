# Track Specification: Pydantic Extraction Generator

## Objective
Implement a generator that reads the "Golden Source" YAML schemas (`listing.yaml`, `venue.yaml`, etc.) and automatically generates the Pydantic models used for LLM extraction (e.g., `entity_extraction.py`).

## Context
Currently, the "Single Source of Truth" track successfully generates database schemas (Prisma), backend types (Python), and frontend types (TypeScript). However, the Pydantic models used by the extraction engine (`engine/extraction/models/entity_extraction.py`) are manually maintained. This creates a risk of drift where new fields added to `listing.yaml` are missing from the extraction logic, as seen with `entity_type`.

## Requirements

### 1. Source of Truth
- The generator MUST read from `engine/config/schemas/*.yaml`.
- It MUST respect all field metadata (name, type, description, nullable).

### 2. Extraction Semantics (The "Detective" Logic)
The generated models must support the specific needs of LLM extraction, which differ from database storage:
- **Aggressive Nulls**: All fields (even required ones) should default to `None` in the Pydantic model to allow the LLM to signal "missing info".
- **Validators**: The generator must support injecting custom validators (e.g., E.164 phone formatting) either via metadata in the YAML or by preserving manual validator code.
- **Docstrings**: Descriptions must be preserved and potentially enhanced for LLM instruction.

### 3. Implementation Details
- Create a new generator module: `engine/schema/generators/pydantic_extraction.py`.
- Update the CLI `engine/schema/cli.py` to include this new generator.
- The output file should be `engine/extraction/models/entity_extraction.py` (or similar).

### 4. Migration
- Replace the current manual `entity_extraction.py` with the generated version.
- Ensure all existing tests pass.

## Success Criteria
- [ ] `entity_extraction.py` is auto-generated from `listing.yaml`.
- [ ] No manual editing of `entity_extraction.py` is required for field updates.
- [ ] Custom validators (phone, url, etc.) are preserved or correctly generated.
- [ ] `entity_type` field is correctly included in the generated model.
- [ ] Tests in `engine/tests/` (especially `test_null_semantics.py`) pass with the generated model.
