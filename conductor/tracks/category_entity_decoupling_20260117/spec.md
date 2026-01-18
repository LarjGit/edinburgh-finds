# Product Spec: Category-Entity Decoupling

## Context
Currently, the system models categories hierarchically with `parent: venue` for sports like "Padel", "Tennis", etc. This implies that these categories are subtypes of "Venue".

## Problem
Currently, the system code and configuration contain remnants of a hierarchical category structure (e.g., `parent: venue` in YAML, `get_category_hierarchy` in Python). This conflates **Entity Type** (what something *is*) with **Category** (what something *has* or *offers*).

The user has explicitly stated:
1.  **Absolutely no parent hierarchy** in relation to categories.
2.  **No hierarchy** between categories and entity types.
3.  **No hierarchy** of category-to-category.

## Solution
We must flatten the taxonomy entirely.
- **Categories** are just tags/labels (e.g., "Padel", "Gym", "Sports Centre").
- **Entity Types** are high-level classifications (e.g., "Venue", "Retail", "Coach").
- A "Sports Centre" is a Category. It is likely associated with the Entity Type "Venue", but this link is descriptive, not hierarchical/structural in the code.
- We will remove all `parent` fields from the `canonical_categories.yaml` and all hierarchy traversal logic from the Python codebase.

## Key Changes
1.  **`canonical_categories.yaml`**: Remove all `parent` keys.
2.  **`category_mapper.py`**: Remove hierarchy resolution logic.
3.  **Docs**: Update to reflect a flat tag-based system.
