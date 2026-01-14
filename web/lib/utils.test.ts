import { describe, it, expect } from '@jest/globals';
import { parseAttributesJSON, formatAttributeKey, formatAttributeValue } from './utils';

describe('parseAttributesJSON', () => {
  it('should parse valid JSON string', () => {
    const jsonString = '{"capacity": 250, "wheelchair_accessible": true}';
    const result = parseAttributesJSON(jsonString);
    expect(result).toEqual({ capacity: 250, wheelchair_accessible: true });
  });

  it('should return empty object for null input', () => {
    const result = parseAttributesJSON(null);
    expect(result).toEqual({});
  });

  it('should return empty object for undefined input', () => {
    const result = parseAttributesJSON(undefined);
    expect(result).toEqual({});
  });

  it('should return empty object for empty string', () => {
    const result = parseAttributesJSON('');
    expect(result).toEqual({});
  });

  it('should return empty object for invalid JSON', () => {
    const result = parseAttributesJSON('{invalid json}');
    expect(result).toEqual({});
  });

  it('should handle empty JSON object', () => {
    const result = parseAttributesJSON('{}');
    expect(result).toEqual({});
  });

  it('should handle nested objects', () => {
    const jsonString = '{"location": {"lat": 55.9533, "lng": -3.1883}}';
    const result = parseAttributesJSON(jsonString);
    expect(result).toEqual({ location: { lat: 55.9533, lng: -3.1883 } });
  });

  it('should handle arrays', () => {
    const jsonString = '{"facilities": ["Parking", "Cafe", "WiFi"]}';
    const result = parseAttributesJSON(jsonString);
    expect(result).toEqual({ facilities: ["Parking", "Cafe", "WiFi"] });
  });
});

describe('formatAttributeKey', () => {
  it('should capitalize single word', () => {
    expect(formatAttributeKey('capacity')).toBe('Capacity');
  });

  it('should format snake_case to Title Case', () => {
    expect(formatAttributeKey('wheelchair_accessible')).toBe('Wheelchair Accessible');
  });

  it('should format multi-word snake_case', () => {
    expect(formatAttributeKey('total_parking_spaces')).toBe('Total Parking Spaces');
  });

  it('should handle already capitalized words', () => {
    expect(formatAttributeKey('Capacity')).toBe('Capacity');
  });

  it('should handle single character keys', () => {
    expect(formatAttributeKey('a')).toBe('A');
  });

  it('should handle keys with numbers', () => {
    expect(formatAttributeKey('tennis_5_a_side')).toBe('Tennis 5 A Side');
  });
});

describe('formatAttributeValue', () => {
  it('should format boolean true as "Yes"', () => {
    expect(formatAttributeValue(true)).toBe('Yes');
  });

  it('should format boolean false as "No"', () => {
    expect(formatAttributeValue(false)).toBe('No');
  });

  it('should format number as string', () => {
    expect(formatAttributeValue(250)).toBe('250');
    expect(formatAttributeValue(3.14)).toBe('3.14');
    expect(formatAttributeValue(0)).toBe('0');
  });

  it('should return string as-is', () => {
    expect(formatAttributeValue('Test Value')).toBe('Test Value');
  });

  it('should format array as comma-separated string', () => {
    expect(formatAttributeValue(['Tennis', 'Badminton', 'Squash'])).toBe('Tennis, Badminton, Squash');
  });

  it('should format empty array', () => {
    expect(formatAttributeValue([])).toBe('');
  });

  it('should format object as JSON string', () => {
    const obj = { lat: 55.9533, lng: -3.1883 };
    expect(formatAttributeValue(obj)).toBe(JSON.stringify(obj));
  });

  it('should handle null by converting to string', () => {
    expect(formatAttributeValue(null)).toBe('null');
  });

  it('should handle undefined by converting to string', () => {
    expect(formatAttributeValue(undefined)).toBe('undefined');
  });
});
