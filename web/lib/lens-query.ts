/**
 * Lens-aware query layer for entity filtering and transformation.
 *
 * This module provides query functions that use Prisma array filters to query
 * entities using lens-interpreted dimensions. All queries operate on Postgres
 * text[] arrays (canonical_activities, canonical_roles, canonical_place_types,
 * canonical_access), not JSON.
 *
 * Default query semantics: OR within facet, AND across facets
 * Example: activities=[padel, tennis] AND place_type=[sports_centre]
 *   Result: (has padel OR tennis) AND (is sports_centre)
 *
 * Grouping is computed at query time from entity_class + roles, not stored in database.
 *
 * NOTE on LensContract vs VerticalLens usage:
 * - Web layer (TypeScript, outside engine): CAN use lens runtime objects (VerticalLens)
 * - Engine layer (Python): MUST ONLY use LensContract (plain dict), NEVER import from lenses/
 * - This query layer is in web/ (outside engine), so VerticalLens usage is allowed
 */

/**
 * Interface for facet-based filtering.
 *
 * A facet filter specifies which values to match within a specific facet dimension.
 */
export interface FacetFilter {
  /** Facet key (e.g., "activity", "role", "place_type") */
  facet: string;

  /** Actual DB column name (e.g., "canonical_activities", "canonical_roles", "canonical_place_types", "canonical_access") */
  dimensionSource: string;

  /** Selected canonical values to filter by */
  selectedValues: string[];

  /** Filter mode: 'OR' (hasSome - default) or 'AND' (hasEvery) */
  mode: "OR" | "AND";
}

/**
 * Query by facet using Prisma array filters.
 *
 * Uses dimensionSource (actual DB column name) to build query conditions.
 * Default is OR mode (entity has ANY of these values).
 *
 * @param filter - Facet filter configuration
 * @returns Prisma where clause for array filtering
 *
 * @example
 * // OR mode (default): Entity has padel OR tennis
 * queryByFacet({
 *   facet: "activity",
 *   dimensionSource: "canonical_activities",
 *   selectedValues: ["padel", "tennis"],
 *   mode: "OR"
 * })
 * // Returns: { canonical_activities: { hasSome: ["padel", "tennis"] } }
 * // Uses Postgres && operator
 *
 * @example
 * // AND mode: Entity has BOTH padel AND tennis (rare case)
 * queryByFacet({
 *   facet: "activity",
 *   dimensionSource: "canonical_activities",
 *   selectedValues: ["padel", "tennis"],
 *   mode: "AND"
 * })
 * // Returns: { canonical_activities: { hasEvery: ["padel", "tennis"] } }
 * // Uses Postgres @> operator
 */
export function queryByFacet(filter: FacetFilter): Record<string, any> {
  const { dimensionSource, selectedValues, mode } = filter;

  // Default is OR mode (entity has ANY of these values)
  if (mode === "AND") {
    // Postgres array @> operator (contains all)
    return { [dimensionSource]: { hasEvery: selectedValues } };
  } else {
    // Postgres array && operator (has at least one)
    return { [dimensionSource]: { hasSome: selectedValues } };
  }
}

/**
 * Query by single value in a dimension.
 *
 * Uses Prisma 'has' filter to check if array contains a specific value.
 *
 * @param dimension - DB column name (e.g., "canonical_activities")
 * @param value - Canonical value to match
 * @returns Prisma where clause for single value match
 *
 * @example
 * queryByValue("canonical_activities", "padel")
 * // Returns: { canonical_activities: { has: "padel" } }
 * // Uses Postgres ? operator
 */
export function queryByValue(
  dimension: string,
  value: string
): Record<string, any> {
  // Postgres array ? operator (contains value)
  return { [dimension]: { has: value } };
}

/**
 * Query by derived grouping.
 *
 * Grouping is computed at query time, not stored in database.
 * Builds OR across rules, AND within each rule.
 *
 * @param groupingId - Grouping identifier (e.g., "people", "places")
 * @param lens - Vertical lens instance with derived_groupings configuration
 * @returns Prisma where clause for grouping match
 *
 * @example
 * // Grouping "people" = entity_class:person AND roles:provides_instruction
 * queryByGrouping("people", lens)
 * // Returns:
 * // {
 * //   OR: [
 * //     {
 * //       AND: [
 * //         { entity_class: "person" },
 * //         { canonical_roles: { hasSome: ["provides_instruction"] } }
 * //       ]
 * //     }
 * //   ]
 * // }
 */
export function queryByGrouping(
  groupingId: string,
  lens: any
): Record<string, any> {
  const grouping = lens.derived_groupings?.find(
    (g: any) => g.id === groupingId
  );

  if (!grouping || !grouping.rules) {
    return {};
  }

  // Build OR across rules
  const ruleConditions = grouping.rules.map((rule: any) => {
    const conditions: any[] = [];

    // Add entity_class condition if present
    if (rule.entity_class) {
      conditions.push({ entity_class: rule.entity_class });
    }

    // Add canonical_roles hasSome condition if roles present
    if (rule.roles && rule.roles.length > 0) {
      conditions.push({ canonical_roles: { hasSome: rule.roles } });
    }

    // AND within each rule
    return { AND: conditions };
  });

  // OR of all rules
  // Grouping is computed at query time, not stored in database
  return { OR: ruleConditions };
}

/**
 * Build complex query with multiple filters.
 *
 * Default semantics: OR within facet, AND across facets
 *
 * @param filters - Array of facet filters
 * @param groupingId - Optional grouping identifier
 * @param lens - Optional vertical lens instance (required if groupingId provided)
 * @returns Prisma where clause combining all filters
 *
 * @example
 * // User selects: activities=[padel, tennis], place_type=[sports_centre]
 * // Result: (activities HAS padel OR tennis) AND (place_type HAS sports_centre)
 * buildComplexQuery([
 *   {
 *     facet: "activity",
 *     dimensionSource: "canonical_activities",
 *     selectedValues: ["padel", "tennis"],
 *     mode: "OR"
 *   },
 *   {
 *     facet: "place_type",
 *     dimensionSource: "canonical_place_types",
 *     selectedValues: ["sports_centre"],
 *     mode: "OR"
 *   }
 * ])
 * // Returns:
 * // {
 * //   AND: [
 * //     { canonical_activities: { hasSome: ["padel", "tennis"] } },  // OR within facet
 * //     { canonical_place_types: { hasSome: ["sports_centre"] } }    // AND across facets
 * //   ]
 * // }
 */
export function buildComplexQuery(
  filters: FacetFilter[],
  groupingId?: string,
  lens?: any
): Record<string, any> {
  const conditions: any[] = [];

  // Add facet filters (OR within facet, AND across facets)
  filters.forEach((filter) => {
    conditions.push(queryByFacet(filter));
  });

  // Add grouping filter if present
  if (groupingId && lens) {
    conditions.push(queryByGrouping(groupingId, lens));
  }

  if (conditions.length === 0) {
    return {};
  }

  if (conditions.length === 1) {
    return conditions[0];
  }

  // Default: OR within facet, AND across facets
  return { AND: conditions };
}

/**
 * Entity view with rich metadata after lens transformation.
 */
export interface EntityView {
  /** Entity ID */
  id: string;

  /** Entity name */
  entity_name: string;

  /** Entity class (place, person, organization, event, thing) */
  entity_class: string;

  /** Rich activity metadata with labels, icons, colors */
  activities: Array<{
    key: string;
    label: string;
    icon?: string;
    color?: string;
  }>;

  /** Rich role metadata */
  roles: Array<{
    key: string;
    label: string;
  }>;

  /** Rich place type metadata */
  place_types: Array<{
    key: string;
    label: string;
  }>;

  /** Rich access metadata */
  access: Array<{
    key: string;
    label: string;
  }>;

  /** Computed grouping (derived from entity_class + roles, not stored) */
  grouping?: string;

  /** Other entity fields */
  [key: string]: any;
}

/**
 * Transform entity to view with lens interpretation.
 *
 * Applies lens interpretation to opaque dimension values, converting them
 * to rich metadata with labels, icons, and colors. Computes grouping using
 * lens logic (derived, not stored in database).
 *
 * @param entity - Raw entity from database
 * @param lens - Vertical lens instance with interpretation metadata
 * @returns Entity view with rich metadata
 *
 * @example
 * transformEntityToView(entity, lens)
 * // Input entity: { canonical_activities: ["padel", "tennis"], ... }
 * // Output: {
 * //   activities: [
 * //     { key: "padel", label: "Padel", icon: "racket", color: "blue" },
 * //     { key: "tennis", label: "Tennis", icon: "tennis-ball", color: "green" }
 * //   ],
 * //   grouping: "places",  // Computed at query time, not stored
 * //   ...
 * // }
 */
export function transformEntityToView(
  entity: any,
  lens: any
): EntityView {
  // Build lookup map for canonical values
  const valuesMap = new Map<string, any>();
  if (lens.values) {
    lens.values.forEach((value: any) => {
      valuesMap.set(value.key, value);
    });
  }

  // Helper to map opaque values to rich metadata
  const mapValues = (
    keys: string[],
    facet: string
  ): Array<{ key: string; label: string; icon?: string; color?: string }> => {
    return keys.map((key) => {
      const value = valuesMap.get(key);
      return {
        key,
        label: value?.display_name || key,
        icon: value?.icon_url,
        color: value?.color,
      };
    });
  };

  // Map activities to rich metadata
  const activities = mapValues(
    entity.canonical_activities || [],
    "activity"
  );

  // Map roles to rich metadata
  const roles = mapValues(entity.canonical_roles || [], "role");

  // Map place types to rich metadata
  const place_types = mapValues(
    entity.canonical_place_types || [],
    "place_type"
  );

  // Map access to rich metadata
  const access = mapValues(entity.canonical_access || [], "access");

  // Compute grouping using lens.compute_grouping (derived, not stored)
  // Grouping is a VIEW-ONLY concept, derived from entity_class + roles
  let grouping: string | undefined;
  if (lens.derived_groupings) {
    for (const g of lens.derived_groupings) {
      // Check if entity matches grouping rules
      const matches = g.rules?.some((rule: any) => {
        // Check entity_class
        if (rule.entity_class && entity.entity_class !== rule.entity_class) {
          return false;
        }

        // Check roles (entity must have at least one of required roles)
        if (rule.roles && rule.roles.length > 0) {
          const entityRoles = entity.canonical_roles || [];
          if (!rule.roles.some((r: string) => entityRoles.includes(r))) {
            return false;
          }
        }

        return true;
      });

      if (matches) {
        grouping = g.id;
        break;
      }
    }
  }

  return {
    id: entity.id,
    entity_name: entity.entity_name,
    entity_class: entity.entity_class,
    activities,
    roles,
    place_types,
    access,
    grouping, // Computed at query time from entity_class + roles, not stored in database
    ...entity, // Include all other fields
  };
}
