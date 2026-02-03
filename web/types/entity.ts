// GENERATED FILE - DO NOT EDIT
// This file is auto-generated from YAML schema definitions.
// Any manual changes will be overwritten on next generation.
//
// Source: engine/config/schemas/entity.yaml
// Generated on: 2026-02-03 09:13:47


export interface Entity {
  /** Unique identifier (auto-generated) */
  entity_id: string;
  /** Official name of the entity */
  entity_name: string;
  /** Universal entity classification (place, person, organization, event, thing) */
  entity_class: string | null;
  /** URL-safe version of entity name (auto-generated) */
  slug: string;
  /** A short overall description of the entity summarising all gathered data */
  summary: string | null;
  /** Long-form aggregated evidence from multiple sources (reviews, snippets, editorial summaries) */
  description: string | null;
  /** Raw free-form categories detected by the LLM (uncontrolled observational labels - NOT indexed, NOT used for filtering) */
  raw_categories: string[] | null;
  /** Activities provided/supported (opaque values, lens-interpreted) */
  canonical_activities: string[] | null;
  /** Roles this entity plays (opaque values, universal function-style keys) */
  canonical_roles: string[] | null;
  /** Physical place classifications (opaque values, lens-interpreted) */
  canonical_place_types: string[] | null;
  /** Access requirements (opaque values, lens-interpreted) */
  canonical_access: string[] | null;
  /** Dictionary containing any extra attributes not explicitly defined in Listing or Entity models */
  discovered_attributes: Record<string, any> | null;
  /** Namespaced module data (JSONB) organized by module key */
  modules: Record<string, any> | null;
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
