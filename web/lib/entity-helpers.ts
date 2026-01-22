/**
 * Entity Helper Functions
 *
 * Utilities for working with entities in the Engine-Lens architecture.
 * Supports native PostgreSQL data types (arrays, JSONB).
 */

/**
 * Helper to ensure we have an array for dimension fields.
 * In Postgres, these are native String[] arrays, but defensive coding helps.
 *
 * @param val - The dimension value (should be string[])
 * @returns Valid string array
 */
export function ensureArray(val: string[] | null | undefined): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  return [];
}

/**
 * Helper to ensure we have an object for module fields.
 * In Postgres, these are native JSONB objects.
 *
 * @param val - The module value (should be object)
 * @returns Valid object
 */
export function ensureModules(val: Record<string, any> | null | undefined): Record<string, any> {
  if (!val) return {};
  if (typeof val === "object") return val;
  return {};
}

// Legacy parse/stringify functions removed as we now use native types.
// Kept as pass-throughs temporarily if needed for API compatibility,
// but logic now assumes input is already correct type.

export function parseDimensionArray(val: string[] | null | undefined): string[] {
  return ensureArray(val);
}

export function parseModules(val: Record<string, any> | null | undefined): Record<string, any> {
  return ensureModules(val);
}