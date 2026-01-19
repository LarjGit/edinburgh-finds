/**
 * Tests for lens-aware query layer.
 *
 * Tests validate:
 * 1. OR within facet (multiple activities)
 * 2. AND across facets (activities + place_type)
 * 3. Derived grouping computed correctly
 * 4. Grouping not stored in database (read-only property)
 */

import { describe, test, expect } from "@jest/globals";
import {
  queryByFacet,
  queryByValue,
  queryByGrouping,
  buildComplexQuery,
  transformEntityToView,
  type FacetFilter,
} from "./lens-query";

describe("Query Semantics", () => {
  describe("queryByFacet", () => {
    test("OR mode (default) - uses hasSome", () => {
      const filter: FacetFilter = {
        facet: "activity",
        dimensionSource: "canonical_activities",
        selectedValues: ["padel", "tennis"],
        mode: "OR",
      };

      const result = queryByFacet(filter);

      expect(result).toEqual({
        canonical_activities: { hasSome: ["padel", "tennis"] },
      });
    });

    test("AND mode - uses hasEvery", () => {
      const filter: FacetFilter = {
        facet: "activity",
        dimensionSource: "canonical_activities",
        selectedValues: ["padel", "tennis"],
        mode: "AND",
      };

      const result = queryByFacet(filter);

      expect(result).toEqual({
        canonical_activities: { hasEvery: ["padel", "tennis"] },
      });
    });

    test("works with different dimension sources", () => {
      const filter: FacetFilter = {
        facet: "role",
        dimensionSource: "canonical_roles",
        selectedValues: ["provides_instruction", "sells_goods"],
        mode: "OR",
      };

      const result = queryByFacet(filter);

      expect(result).toEqual({
        canonical_roles: { hasSome: ["provides_instruction", "sells_goods"] },
      });
    });

    test("works with place_type dimension", () => {
      const filter: FacetFilter = {
        facet: "place_type",
        dimensionSource: "canonical_place_types",
        selectedValues: ["sports_centre"],
        mode: "OR",
      };

      const result = queryByFacet(filter);

      expect(result).toEqual({
        canonical_place_types: { hasSome: ["sports_centre"] },
      });
    });

    test("works with access dimension", () => {
      const filter: FacetFilter = {
        facet: "access",
        dimensionSource: "canonical_access",
        selectedValues: ["membership", "pay_and_play"],
        mode: "OR",
      };

      const result = queryByFacet(filter);

      expect(result).toEqual({
        canonical_access: { hasSome: ["membership", "pay_and_play"] },
      });
    });
  });

  describe("queryByValue", () => {
    test("uses 'has' filter for single value", () => {
      const result = queryByValue("canonical_activities", "padel");

      expect(result).toEqual({
        canonical_activities: { has: "padel" },
      });
    });

    test("works with different dimensions", () => {
      const result = queryByValue("canonical_roles", "provides_instruction");

      expect(result).toEqual({
        canonical_roles: { has: "provides_instruction" },
      });
    });
  });

  describe("queryByGrouping", () => {
    test("builds OR across rules, AND within each rule", () => {
      const lens = {
        derived_groupings: [
          {
            id: "people",
            label: "People",
            rules: [
              {
                entity_class: "person",
                roles: ["provides_instruction"],
              },
            ],
          },
        ],
      };

      const result = queryByGrouping("people", lens);

      expect(result).toEqual({
        OR: [
          {
            AND: [
              { entity_class: "person" },
              { canonical_roles: { hasSome: ["provides_instruction"] } },
            ],
          },
        ],
      });
    });

    test("handles multiple rules", () => {
      const lens = {
        derived_groupings: [
          {
            id: "people",
            label: "People",
            rules: [
              {
                entity_class: "person",
                roles: ["provides_instruction"],
              },
              {
                entity_class: "person",
                roles: ["sells_goods"],
              },
            ],
          },
        ],
      };

      const result = queryByGrouping("people", lens);

      expect(result).toEqual({
        OR: [
          {
            AND: [
              { entity_class: "person" },
              { canonical_roles: { hasSome: ["provides_instruction"] } },
            ],
          },
          {
            AND: [
              { entity_class: "person" },
              { canonical_roles: { hasSome: ["sells_goods"] } },
            ],
          },
        ],
      });
    });

    test("handles entity_class only rules", () => {
      const lens = {
        derived_groupings: [
          {
            id: "places",
            label: "Places",
            rules: [
              {
                entity_class: "place",
              },
            ],
          },
        ],
      };

      const result = queryByGrouping("places", lens);

      expect(result).toEqual({
        OR: [
          {
            AND: [{ entity_class: "place" }],
          },
        ],
      });
    });

    test("returns empty object for non-existent grouping", () => {
      const lens = {
        derived_groupings: [],
      };

      const result = queryByGrouping("nonexistent", lens);

      expect(result).toEqual({});
    });
  });

  describe("buildComplexQuery", () => {
    test("OR within facet - multiple activities", () => {
      const filters: FacetFilter[] = [
        {
          facet: "activity",
          dimensionSource: "canonical_activities",
          selectedValues: ["padel", "tennis"],
          mode: "OR",
        },
      ];

      const result = buildComplexQuery(filters);

      expect(result).toEqual({
        canonical_activities: { hasSome: ["padel", "tennis"] },
      });
    });

    test("AND across facets - activities + place_type", () => {
      const filters: FacetFilter[] = [
        {
          facet: "activity",
          dimensionSource: "canonical_activities",
          selectedValues: ["padel", "tennis"],
          mode: "OR",
        },
        {
          facet: "place_type",
          dimensionSource: "canonical_place_types",
          selectedValues: ["sports_centre"],
          mode: "OR",
        },
      ];

      const result = buildComplexQuery(filters);

      // Default: OR within facet, AND across facets
      expect(result).toEqual({
        AND: [
          { canonical_activities: { hasSome: ["padel", "tennis"] } },
          { canonical_place_types: { hasSome: ["sports_centre"] } },
        ],
      });
    });

    test("handles three facets - activities + place_type + access", () => {
      const filters: FacetFilter[] = [
        {
          facet: "activity",
          dimensionSource: "canonical_activities",
          selectedValues: ["padel", "tennis"],
          mode: "OR",
        },
        {
          facet: "place_type",
          dimensionSource: "canonical_place_types",
          selectedValues: ["sports_centre"],
          mode: "OR",
        },
        {
          facet: "access",
          dimensionSource: "canonical_access",
          selectedValues: ["pay_and_play"],
          mode: "OR",
        },
      ];

      const result = buildComplexQuery(filters);

      expect(result).toEqual({
        AND: [
          { canonical_activities: { hasSome: ["padel", "tennis"] } },
          { canonical_place_types: { hasSome: ["sports_centre"] } },
          { canonical_access: { hasSome: ["pay_and_play"] } },
        ],
      });
    });

    test("includes grouping filter when provided", () => {
      const filters: FacetFilter[] = [
        {
          facet: "activity",
          dimensionSource: "canonical_activities",
          selectedValues: ["padel"],
          mode: "OR",
        },
      ];

      const lens = {
        derived_groupings: [
          {
            id: "places",
            label: "Places",
            rules: [{ entity_class: "place" }],
          },
        ],
      };

      const result = buildComplexQuery(filters, "places", lens);

      expect(result).toEqual({
        AND: [
          { canonical_activities: { hasSome: ["padel"] } },
          {
            OR: [
              {
                AND: [{ entity_class: "place" }],
              },
            ],
          },
        ],
      });
    });

    test("returns empty object for empty filters", () => {
      const result = buildComplexQuery([]);

      expect(result).toEqual({});
    });
  });

  describe("transformEntityToView", () => {
    test("maps canonical values to rich metadata", () => {
      const entity = {
        id: "1",
        entity_name: "Test Entity",
        entity_class: "place",
        canonical_activities: ["padel", "tennis"],
        canonical_roles: ["provides_facility"],
        canonical_place_types: ["sports_centre"],
        canonical_access: ["pay_and_play"],
      };

      const lens = {
        values: [
          {
            key: "padel",
            facet: "activity",
            display_name: "Padel",
            icon_url: "racket",
            color: "blue",
          },
          {
            key: "tennis",
            facet: "activity",
            display_name: "Tennis",
            icon_url: "tennis-ball",
            color: "green",
          },
          {
            key: "provides_facility",
            facet: "role",
            display_name: "Provides Facility",
          },
          {
            key: "sports_centre",
            facet: "place_type",
            display_name: "Sports Centre",
          },
          {
            key: "pay_and_play",
            facet: "access",
            display_name: "Pay and Play",
          },
        ],
        derived_groupings: [],
      };

      const result = transformEntityToView(entity, lens);

      expect(result.activities).toEqual([
        { key: "padel", label: "Padel", icon: "racket", color: "blue" },
        { key: "tennis", label: "Tennis", icon: "tennis-ball", color: "green" },
      ]);

      expect(result.roles).toEqual([
        { key: "provides_facility", label: "Provides Facility", icon: undefined, color: undefined },
      ]);

      expect(result.place_types).toEqual([
        { key: "sports_centre", label: "Sports Centre", icon: undefined, color: undefined },
      ]);

      expect(result.access).toEqual([
        { key: "pay_and_play", label: "Pay and Play", icon: undefined, color: undefined },
      ]);

      expect(result.id).toBe("1");
      expect(result.entity_name).toBe("Test Entity");
      expect(result.entity_class).toBe("place");
    });

    test("computes grouping from entity_class + roles (not stored)", () => {
      const entity = {
        id: "1",
        entity_name: "Test Person",
        entity_class: "person",
        canonical_activities: [],
        canonical_roles: ["provides_instruction"],
        canonical_place_types: [],
        canonical_access: [],
      };

      const lens = {
        values: [],
        derived_groupings: [
          {
            id: "people",
            label: "People",
            rules: [
              {
                entity_class: "person",
                roles: ["provides_instruction"],
              },
            ],
          },
        ],
      };

      const result = transformEntityToView(entity, lens);

      // Grouping is computed at query time, not stored in database
      expect(result.grouping).toBe("people");

      // Verify original entity doesn't have grouping (it's derived)
      expect(entity).not.toHaveProperty("grouping");
    });

    test("handles missing values gracefully", () => {
      const entity = {
        id: "1",
        entity_name: "Test Entity",
        entity_class: "place",
        canonical_activities: ["unknown_activity"],
        canonical_roles: [],
        canonical_place_types: [],
        canonical_access: [],
      };

      const lens = {
        values: [],
        derived_groupings: [],
      };

      const result = transformEntityToView(entity, lens);

      // Unknown values fall back to key as label
      expect(result.activities).toEqual([
        { key: "unknown_activity", label: "unknown_activity", icon: undefined, color: undefined },
      ]);

      expect(result.roles).toEqual([]);
      expect(result.place_types).toEqual([]);
      expect(result.access).toEqual([]);
      expect(result.grouping).toBeUndefined();
    });

    test("handles entity with no derived grouping match", () => {
      const entity = {
        id: "1",
        entity_name: "Test Entity",
        entity_class: "organization",
        canonical_activities: [],
        canonical_roles: [],
        canonical_place_types: [],
        canonical_access: [],
      };

      const lens = {
        values: [],
        derived_groupings: [
          {
            id: "people",
            label: "People",
            rules: [
              {
                entity_class: "person",
                roles: ["provides_instruction"],
              },
            ],
          },
        ],
      };

      const result = transformEntityToView(entity, lens);

      // No matching grouping
      expect(result.grouping).toBeUndefined();
    });

    test("handles multiple grouping rules with OR logic", () => {
      const entity = {
        id: "1",
        entity_name: "Test Person",
        entity_class: "person",
        canonical_activities: [],
        canonical_roles: ["sells_goods"],
        canonical_place_types: [],
        canonical_access: [],
      };

      const lens = {
        values: [],
        derived_groupings: [
          {
            id: "people",
            label: "People",
            rules: [
              {
                entity_class: "person",
                roles: ["provides_instruction"],
              },
              {
                entity_class: "person",
                roles: ["sells_goods"],
              },
            ],
          },
        ],
      };

      const result = transformEntityToView(entity, lens);

      // Matches second rule (OR across rules)
      expect(result.grouping).toBe("people");
    });
  });

  describe("Query Semantics Integration", () => {
    test("OR within facet semantic - hasSome operator", () => {
      // Semantic: "Show me places with padel OR tennis"
      const filter: FacetFilter = {
        facet: "activity",
        dimensionSource: "canonical_activities",
        selectedValues: ["padel", "tennis"],
        mode: "OR",
      };

      const query = queryByFacet(filter);

      // Verify OR semantics (hasSome = entity has ANY of these values)
      expect(query).toEqual({
        canonical_activities: { hasSome: ["padel", "tennis"] },
      });

      // This would match:
      // ✅ Entity with activities: ["padel"]
      // ✅ Entity with activities: ["tennis"]
      // ✅ Entity with activities: ["padel", "tennis"]
      // ✅ Entity with activities: ["padel", "tennis", "squash"]
      // ❌ Entity with activities: ["squash", "badminton"]
    });

    test("AND across facets semantic", () => {
      // Semantic: "Show me sports centres with padel OR tennis"
      const filters: FacetFilter[] = [
        {
          facet: "activity",
          dimensionSource: "canonical_activities",
          selectedValues: ["padel", "tennis"],
          mode: "OR",
        },
        {
          facet: "place_type",
          dimensionSource: "canonical_place_types",
          selectedValues: ["sports_centre"],
          mode: "OR",
        },
      ];

      const query = buildComplexQuery(filters);

      // Verify AND across facets
      expect(query).toEqual({
        AND: [
          { canonical_activities: { hasSome: ["padel", "tennis"] } },
          { canonical_place_types: { hasSome: ["sports_centre"] } },
        ],
      });

      // This would match:
      // ✅ Sports centre with padel
      // ✅ Sports centre with tennis
      // ✅ Sports centre with padel and tennis
      // ❌ Sports centre with only squash (missing padel/tennis)
      // ❌ Outdoor facility with padel (wrong place_type)
    });

    test("Grouping is view-only, not stored", () => {
      const entity = {
        id: "1",
        entity_name: "Coach",
        entity_class: "person",
        canonical_activities: [],
        canonical_roles: ["provides_instruction"],
        canonical_place_types: [],
        canonical_access: [],
      };

      const lens = {
        values: [],
        derived_groupings: [
          {
            id: "people",
            label: "People",
            rules: [{ entity_class: "person", roles: ["provides_instruction"] }],
          },
        ],
      };

      // Transform entity to view
      const view = transformEntityToView(entity, lens);

      // Grouping is computed (view-only)
      expect(view.grouping).toBe("people");

      // Original entity doesn't have grouping (it's not stored)
      expect(entity).not.toHaveProperty("grouping");
      expect(entity).not.toHaveProperty("grouping_id");

      // This validates the anti-pattern:
      // ❌ NEVER add grouping_id column to entities table
      // ❌ NEVER store computed grouping value
      // ✅ ALWAYS compute grouping at query/view time from entity_class + roles
    });
  });
});
