# Pull Request

## Description

<!-- Provide a brief description of the changes in this PR -->

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Architectural Validation Checklist

All PRs must pass these validation checks (enforced in CI):

### Engine Purity
- [ ] Engine does not import from lenses/ (receives LensContract dict only)
- [ ] No value-based branching on dimension values (structural purity)
- [ ] All dimension values treated as opaque strings
- [ ] Engine may ONLY: branch on entity_class, perform set operations, check emptiness, pass opaque strings through
- [ ] CI purity checks pass: `bash scripts/check_engine_purity.sh`

### Lens Contract Validation
- [ ] All facets use valid dimension sources (canonical_activities, canonical_roles, canonical_place_types, canonical_access)
- [ ] All value.facet references exist in facets section
- [ ] All mapping_rules.canonical references exist in values section
- [ ] No duplicate value keys
- [ ] Lens validation tests pass: `pytest tests/lenses/test_validator.py -v`

### Module Composition
- [ ] Modules properly namespaced in JSONB (no flattened structure)
- [ ] No duplicate module keys in YAML
- [ ] Module composition tests pass: `pytest tests/modules/test_composition.py -v`

### Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality (if applicable)
- [ ] Deduplication tests pass: `pytest tests/lenses/test_lens_processing.py::TestDedupePreserveOrder -v`
- [ ] Prisma array filter tests pass (if using PostgreSQL): `pytest tests/query/test_prisma_array_filters.py -v`

## Documentation
- [ ] README.md updated (if applicable)
- [ ] ARCHITECTURE.md updated (if applicable)
- [ ] Inline code comments added for complex logic
- [ ] YAML schema files updated (if schema changes)

## Manual Testing

<!-- Describe the manual testing performed -->

- [ ] I have manually tested these changes
- [ ] I have verified the changes work in both development and production environments (if applicable)

## Related Issues

<!-- Link to related issues, e.g., "Closes #123" or "Relates to #456" -->

## Additional Notes

<!-- Any additional information that reviewers should know -->
