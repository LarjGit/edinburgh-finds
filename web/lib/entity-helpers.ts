/**
 * Entity Helper Functions
 *
 * Utilities for working with entities in the Engine-Lens architecture.
 * Handles JSON parsing for dimension arrays and modules (SQLite workaround).
 */

/**
 * Parse dimension array from JSON string.
 *
 * SQLite workaround: Dimensions are stored as JSON strings (e.g., '["padel","tennis"]')
 * In Postgres, these will be native String[] arrays.
 *
 * @param jsonString - JSON string or null
 * @returns Parsed array or empty array if null/invalid
 */
export function parseDimensionArray(jsonString: string | null | undefined): string[] {
  if (!jsonString) {
    return [];
  }

  try {
    const parsed = JSON.parse(jsonString);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error("Failed to parse dimension array:", jsonString, error);
    return [];
  }
}

/**
 * Parse modules object from JSON string.
 *
 * SQLite workaround: Modules are stored as JSON strings
 * In Postgres, these will be native Json/JSONB type.
 *
 * @param jsonString - JSON string or null
 * @returns Parsed object or empty object if null/invalid
 */
export function parseModules(jsonString: string | null | undefined): Record<string, any> {
  if (!jsonString) {
    return {};
  }

  try {
    const parsed = JSON.parse(jsonString);
    return typeof parsed === "object" && parsed !== null ? parsed : {};
  } catch (error) {
    console.error("Failed to parse modules:", jsonString, error);
    return {};
  }
}

/**
 * Stringify dimension array to JSON string.
 *
 * For inserting/updating dimension arrays in SQLite.
 *
 * @param array - Array of strings
 * @returns JSON string representation
 */
export function stringifyDimensionArray(array: string[]): string {
  return JSON.stringify(array || []);
}

/**
 * Stringify modules object to JSON string.
 *
 * For inserting/updating modules in SQLite.
 *
 * @param modules - Modules object
 * @returns JSON string representation
 */
export function stringifyModules(modules: Record<string, any>): string {
  return JSON.stringify(modules || {});
}
