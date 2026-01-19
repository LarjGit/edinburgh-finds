#!/bin/bash
# Engine Purity Check Script
#
# This script validates that the engine layer maintains architectural purity:
# 1. No imports from lenses/ directory (LensContract boundary violation)
# 2. No literal string comparisons against dimension values (structural purity violation)
#
# Usage: ./scripts/check_engine_purity.sh
# Exit codes: 0 = success, 1 = violations found

set -e

echo "Checking engine purity..."
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VIOLATIONS_FOUND=0

# Check 1: Engine must not import from lenses/
echo "Check 1: Verifying no lens imports in engine..."
if grep -r --include="*.py" -n "^\s*from\s\+lenses\|^\s*import\s\+lenses" engine/; then
    echo -e "${RED}ERROR: Engine imports from lenses/ (LensContract boundary violation)${NC}"
    echo ""
    echo "The engine layer must remain decoupled from lens implementations."
    echo "Engine receives lens_contract as a plain dict; it never imports from lenses/"
    echo ""
    VIOLATIONS_FOUND=1
else
    echo -e "${GREEN}✓ No lens imports found${NC}"
fi

echo ""

# Check 2: Engine must not do literal string comparisons on dimension values
echo "Check 2: Verifying no literal string comparisons on dimensions..."
# Pattern: (if|elif).*canonical_(activities|roles|place_types|access).*(==|in).*["']
# This catches patterns like:
#   if "padel" in canonical_activities
#   if canonical_roles[0] == "coach"
#   elif "winery" in canonical_place_types
if grep -r --include="*.py" -n -E '(if|elif).*canonical_(activities|roles|place_types|access).*(==|in).*["\x27]' engine/; then
    echo -e "${RED}ERROR: Engine has literal string comparisons against dimension values (structural purity violation)${NC}"
    echo ""
    echo "Engine may only:"
    echo "  - Branch on entity_class (e.g., if entity_class == \"place\")"
    echo "  - Perform set operations on opaque strings (union, intersection, membership)"
    echo "  - Check emptiness/existence (e.g., if canonical_activities)"
    echo "  - Pass opaque strings through unchanged"
    echo ""
    echo "FORBIDDEN: Literal comparisons like if \"padel\" in canonical_activities"
    echo ""
    VIOLATIONS_FOUND=1
else
    echo -e "${GREEN}✓ No literal string comparisons on dimensions${NC}"
fi

echo ""

# Summary
if [ $VIOLATIONS_FOUND -eq 1 ]; then
    echo -e "${RED}✗ Engine purity checks FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}✓ All engine purity checks PASSED${NC}"
    exit 0
fi
