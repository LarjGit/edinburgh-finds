# Specification: Universal Entity Model Refactor

## Context
In the `category_entity_decoupling` track, we removed the logic that defaulted all extracted items to `entity_type="VENUE"`. We also added an `entity_type` field to the Pydantic model used by LLMs to allow them to classify items as "RETAIL", "COACH", etc.

## Problem
The Pydantic model is still named `VenueExtraction` and lives in `venue_extraction.py`.
This is:
1.  **Confusing**: It implies the model is only for Venues, contradicting the new logic that it handles all entity types.
2.  **Tech Debt**: It represents a "naming debt" where the code's structure (class names) lags behind its actual behavior (universal extraction).

## Goal
Holistically refactor the extraction models to reflect their universal nature.
The system should use `EntityExtraction` as the primary extraction container, making it clear that a "Venue" is just one *type* of Entity, not the definition of the Entity itself.

## Requirements
1.  **Rename Model**: Change `VenueExtraction` to `EntityExtraction`.
2.  **Rename File**: Move `engine/extraction/models/venue_extraction.py` to `engine/extraction/models/entity_extraction.py`.
3.  **Update Consumers**: Refactor `OSMExtractor`, `SerperExtractor`, and all associated tests to use the new class and module.
4.  **Review "Venue" Usage**: Scan the extraction engine for other instances where "Venue" is used as a synonym for "Entity" and refactor where appropriate to generic terms (e.g., `extracted_venue` -> `extracted_entity`).

## Non-Goals
- Changing the database schema (`Listing`, `ExtractedListing`).
- Changing the `EntityType` enum values.
- Modifying the extraction logic itself (logic is already correct, this is a structural/naming refactor).
