// GENERATED FILE - DO NOT EDIT
// This file is auto-generated from YAML schema definitions.
// Any manual changes will be overwritten on next generation.
//
// Source: engine/config/schemas/winery.yaml
// Generated on: 2026-01-17 19:48:44


import { z } from "zod";
import { Listing } from "./listing";

export interface Winery extends Listing {
  /** Foreign key to parent Listing */
  listing_id: string;
  /** Grape varieties grown or featured at this winery */
  grape_varieties: string[] | null;
  /** Wine appellation or region (e.g., Bordeaux, Napa Valley) */
  appellation: string | null;
  /** Size of vineyard in hectares */
  vineyard_size_hectares: number | null;
  /** Whether the winery is certified organic */
  organic_certified: boolean | null;
  /** Types of wine produced (red, white, rosé, sparkling, dessert) */
  wine_types: string[] | null;
  /** Annual production volume in bottles */
  annual_production_bottles: number | null;
  /** Whether a tasting room is available */
  tasting_room: boolean | null;
  /** Whether vineyard or winery tours are offered */
  tours_available: boolean | null;
  /** Whether reservations are required for tastings/tours */
  reservation_required: boolean | null;
  /** Whether the winery has event space for weddings, corporate events, etc. */
  event_space: boolean | null;
  /** A short overall description of the winery and its offerings */
  winery_summary: string | null;
}

export const WinerySchema = z.object({
  listing_id: z.string(),
  grape_varieties: z.array(z.string()).nullable(),
  appellation: z.string().nullable(),
  vineyard_size_hectares: z.number().nullable(),
  organic_certified: z.boolean().nullable(),
  wine_types: z.array(z.string()).nullable(),
  annual_production_bottles: z.number().int().nullable(),
  tasting_room: z.boolean().nullable(),
  tours_available: z.boolean().nullable(),
  reservation_required: z.boolean().nullable(),
  event_space: z.boolean().nullable(),
  winery_summary: z.string().nullable(),
});
