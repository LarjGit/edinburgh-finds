// GENERATED FILE - DO NOT EDIT
// This file is auto-generated from YAML schema definitions.
// Any manual changes will be overwritten on next generation.
//
// Source: engine/config/schemas/listing.yaml
// Generated on: 2026-01-17 19:48:44


import { z } from "zod";

export interface Listing {
  /** Unique identifier (auto-generated) */
  listing_id: string;
  /** Official name of the entity */
  entity_name: string;
  /** Type of entity (venue, retailer, cafe, event, members_club, etc) */
  entity_type: string;
  /** URL-safe version of entity name (auto-generated) */
  slug: string;
  /** A short overall description of the entity summarising all gathered data */
  summary: string | null;
  /** Raw free-form categories detected by the LLM (uncontrolled labels) */
  categories: string[] | null;
  /** Cleaned, controlled categories used for navigation and taxonomy */
  canonical_categories: string[] | null;
  /** Dictionary containing any extra attributes not explicitly defined in Listing or Entity models */
  discovered_attributes: Record<string, any> | null;
  /** Full street address including building number, street name, city and postcode */
  street_address: string | null;
  /** City or town */
  city: string | null;
  /** Full UK postcode with correct spacing (e.g., 'SW1A 0AA') */
  postcode: string | null;
  /** Country name */
  country: string | null;
  /** WGS84 Latitude coordinate (decimal degrees) */
  latitude: number | null;
  /** WGS84 Longitude coordinate (decimal degrees) */
  longitude: number | null;
  /** Primary contact phone number with country code. MUST be E.164 UK format (e.g. '+441315397071') */
  phone: string | null;
  /** Primary public email address */
  email: string | null;
  /** Official website URL */
  website_url: string | null;
  /** Instagram profile URL or handle */
  instagram_url: string | null;
  /** Facebook page URL */
  facebook_url: string | null;
  /** Twitter/X profile URL or handle */
  twitter_url: string | null;
  /** LinkedIn company page URL */
  linkedin_url: string | null;
  /** Opening hours per day. May contain strings or nested open/close times. Example: {'monday': {'open': '05:30', 'close': '22:00'}, 'sunday': 'CLOSED'} */
  opening_hours: Record<string, any> | null;
  /** Provenance metadata: URLs, method (tavily/manual), timestamps, notes */
  source_info: Record<string, any> | null;
  /** Per-field confidence scores used for overwrite decisions */
  field_confidence: Record<string, any> | null;
  /** Creation timestamp */
  created_at: Date | null;
  /** Last update timestamp */
  updated_at: Date | null;
  /** External system IDs (e.g., {'wordpress': 123, 'google': 'abc'}) */
  external_ids: Record<string, any> | null;
}

export const ListingSchema = z.object({
  listing_id: z.string(),
  entity_name: z.string(),
  entity_type: z.string(),
  slug: z.string(),
  summary: z.string().nullable(),
  categories: z.array(z.string()).nullable(),
  canonical_categories: z.array(z.string()).nullable(),
  discovered_attributes: z.record(z.string(), z.any()).nullable(),
  street_address: z.string().nullable(),
  city: z.string().nullable(),
  postcode: z.string().nullable(),
  country: z.string().nullable(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  phone: z.string().nullable(),
  email: z.string().nullable(),
  website_url: z.string().nullable(),
  instagram_url: z.string().nullable(),
  facebook_url: z.string().nullable(),
  twitter_url: z.string().nullable(),
  linkedin_url: z.string().nullable(),
  opening_hours: z.record(z.string(), z.any()).nullable(),
  source_info: z.record(z.string(), z.any()).nullable(),
  field_confidence: z.record(z.string(), z.any()).nullable(),
  created_at: z.date().nullable(),
  updated_at: z.date().nullable(),
  external_ids: z.record(z.string(), z.any()).nullable(),
});
