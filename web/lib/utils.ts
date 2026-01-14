import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Safely parse a JSON string, returning an empty object if parsing fails.
 * Used for parsing the attributes field from listings.
 *
 * @param jsonString - The JSON string to parse
 * @returns The parsed object or an empty object if parsing fails
 */
export function parseAttributesJSON(jsonString: string | null | undefined): Record<string, any> {
  if (!jsonString) {
    return {};
  }

  try {
    return JSON.parse(jsonString);
  } catch (error) {
    console.warn('Failed to parse attributes JSON:', error);
    return {};
  }
}

/**
 * Format an attribute key for display (e.g., "capacity" -> "Capacity", "wheelchair_accessible" -> "Wheelchair Accessible")
 *
 * @param key - The attribute key
 * @returns Formatted string for display
 */
export function formatAttributeKey(key: string): string {
  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Format an attribute value for display
 *
 * @param value - The attribute value
 * @returns Formatted string for display
 */
export function formatAttributeValue(value: any): string {
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }
  if (typeof value === 'number') {
    return value.toString();
  }
  if (typeof value === 'string') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value);
  }
  return String(value);
}
