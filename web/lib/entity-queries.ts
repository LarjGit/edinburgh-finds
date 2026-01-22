//
/**
 * Entity Query Utilities - Lens-Aware Prisma Queries
 *
 * Uses Prisma array filters (hasSome, has, hasEvery) which work
 * with native PostgreSQL String[] arrays.
 *
 * Key Features:
 * - Faceted filtering using Prisma array filters (has, hasSome, hasEvery)
 * - OR within facet, AND across facets (standard faceted search semantics)
 * - Type-safe query building
 * - Support for all dimension arrays (activities, roles, place_types, access)
 */

import { Prisma } from "@prisma/client";

/**
 * Facet filter configuration.
 * Maps facet names to their values for filtering.
 */
export interface FacetFilters {
  /**
   * Activities to filter by (OR within facet).
   * Example: ["padel", "tennis"] - entities with padel OR tennis
   */
  activities?: string[];

  /**
   * Roles to filter by (OR within facet).
   * Example: ["provides_facility"] - entities that provide facilities
   */
  roles?: string[];

  /**
   * Place types to filter by (OR within facet).
   * Example: ["sports_centre"] - sports centre entities
   */
  place_types?: string[];

  /**
   * Access types to filter by (OR within facet).
   * Example: ["membership", "pay_and_play"] - membership OR pay and play
   */
  access?: string[];

  /**
   * Entity class to filter by.
   * Example: "place" - only place entities
   */
  entity_class?: string;
}

/**
 * Build Prisma where clause for faceted filtering.
 *
 * Query semantics:
 * - OR within facet: Entity matches if it has ANY of the specified values
 * - AND across facets: Entity must match ALL specified facets
 *
 * Example:
 * ```ts
 * buildFacetedWhere({
 *   activities: ["padel", "tennis"],  // Must have padel OR tennis
 *   place_types: ["sports_centre"]    // AND must be sports_centre
 * })
 * // Returns entities that are sports centres offering padel or tennis
 * ```
 *
 * Prisma array filters:
 * - hasSome: Array contains at least one of the specified values (OR within facet)
 * - has: Array contains the exact value
 * - hasEvery: Array contains all specified values
 *
 * @param filters - Facet filters to apply
 * @returns Prisma where clause for Entity.findMany()
 */
export function buildFacetedWhere(filters: FacetFilters): Prisma.EntityWhereInput {
  const where: Prisma.EntityWhereInput = {};

  // AND logic across facets - all conditions must match
  const conditions: Prisma.EntityWhereInput[] = [];

  // Activity facet - OR within facet (hasSome)
  if (filters.activities && filters.activities.length > 0) {
    conditions.push({
      canonical_activities: {
        hasSome: filters.activities, // Entity has at least one of these activities
      },
    });
  }

  // Role facet - OR within facet (hasSome)
  if (filters.roles && filters.roles.length > 0) {
    conditions.push({
      canonical_roles: {
        hasSome: filters.roles, // Entity has at least one of these roles
      },
    });
  }

  // Place type facet - OR within facet (hasSome)
  if (filters.place_types && filters.place_types.length > 0) {
    conditions.push({
      canonical_place_types: {
        hasSome: filters.place_types, // Entity has at least one of these place types
      },
    });
  }

  // Access facet - OR within facet (hasSome)
  if (filters.access && filters.access.length > 0) {
    conditions.push({
      canonical_access: {
        hasSome: filters.access, // Entity has at least one of these access types
      },
    });
  }

  // Entity class - exact match
  if (filters.entity_class) {
    conditions.push({
      entity_class: filters.entity_class,
    });
  }

  // Combine all conditions with AND
  if (conditions.length > 0) {
    where.AND = conditions;
  }

  return where;
}

/**
 * Example queries demonstrating Prisma array filters.
 *
 * These examples show the recommended patterns for querying
 * entities with the new lens-aware schema.
 */
export const EXAMPLE_QUERIES = {
  /**
   * Find all padel venues in Edinburgh.
   * Filters:
   * - activities: padel
   * - roles: provides_facility (venues that provide facilities)
   * - entity_class: place (physical locations only)
   */
  padelVenues: (): Prisma.EntityWhereInput => buildFacetedWhere({
    activities: ["padel"],
    roles: ["provides_facility"],
    entity_class: "place",
  }),

  /**
   * Find all sports centres (any activity).
   * Filters:
   * - place_types: sports_centre
   * - entity_class: place
   */
  sportsCentres: (): Prisma.EntityWhereInput => buildFacetedWhere({
    place_types: ["sports_centre"],
    entity_class: "place",
  }),

  /**
   * Find all coaches (any activity).
   * Filters:
   * - roles: provides_instruction
   * - entity_class: person
   */
  coaches: (): Prisma.EntityWhereInput => buildFacetedWhere({
    roles: ["provides_instruction"],
    entity_class: "person",
  }),

  /**
   * Find tennis or padel coaches.
   * Filters:
   * - activities: tennis OR padel
   * - roles: provides_instruction
   * - entity_class: person
   */
  racquetCoaches: (): Prisma.EntityWhereInput => buildFacetedWhere({
    activities: ["tennis", "padel"],
    roles: ["provides_instruction"],
    entity_class: "person",
  }),

  /**
   * Find pay-and-play venues.
   * Filters:
   * - access: pay_and_play
   * - roles: provides_facility
   * - entity_class: place
   */
  payAndPlayVenues: (): Prisma.EntityWhereInput => buildFacetedWhere({
    access: ["pay_and_play"],
    roles: ["provides_facility"],
    entity_class: "place",
  }),

  /**
   * Find sports centres offering padel with pay-and-play access.
   * Complex query demonstrating AND across facets:
   * - activities: padel (must have)
   * - place_types: sports_centre (AND must be)
   * - access: pay_and_play (AND must have)
   */
  payAndPlayPadelSportsCentres: (): Prisma.EntityWhereInput => buildFacetedWhere({
    activities: ["padel"],
    place_types: ["sports_centre"],
    access: ["pay_and_play"],
    entity_class: "place",
  }),
};

/**
 * Get all entities matching the given facet filters.
 *
 * Usage:
 * ```ts
 * import prisma from "@/lib/prisma";
 * import { queryEntitiesByFacets } from "@/lib/entity-queries";
 *
 * const padelVenues = await queryEntitiesByFacets(prisma, {
 *   activities: ["padel"],
 *   entity_class: "place"
 * });
 * ```
 *
 * @param prisma - Prisma client instance
 * @param filters - Facet filters to apply
 * @param options - Additional query options (take, skip, orderBy, etc.)
 * @returns Array of matching entities
 */
export async function queryEntitiesByFacets(
  prisma: any,
  filters: FacetFilters,
  options?: {
    take?: number;
    skip?: number;
    orderBy?: Prisma.EntityOrderByWithRelationInput;
    select?: Prisma.EntitySelect;
  }
) {
  const where = buildFacetedWhere(filters);

  return prisma.entity.findMany({
    where,
    ...options,
  });
}

/**
 * Count entities matching the given facet filters.
 *
 * Useful for pagination and facet count displays.
 *
 * @param prisma - Prisma client instance
 * @param filters - Facet filters to apply
 * @returns Count of matching entities
 */
export async function countEntitiesByFacets(
  prisma: any,
  filters: FacetFilters
): Promise<number> {
  const where = buildFacetedWhere(filters);

  return prisma.entity.count({
    where,
  });
}
