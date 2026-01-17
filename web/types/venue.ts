// GENERATED FILE - DO NOT EDIT
// This file is auto-generated from YAML schema definitions.
// Any manual changes will be overwritten on next generation.
//
// Source: engine/config/schemas/venue.yaml
// Generated on: 2026-01-17 19:48:44


import { z } from "zod";
import { Listing } from "./listing";

export interface Venue extends Listing {
  /** Foreign key to parent Listing */
  listing_id: string;
  /** A short overall description of the tennis facilities summarising all gathered data */
  tennis_summary: string | null;
  /** Whether tennis is available at this venue */
  tennis: boolean | null;
  /** Total number of tennis courts */
  tennis_total_courts: number | null;
  /** Number of indoor tennis courts */
  tennis_indoor_courts: number | null;
  /** Number of outdoor tennis courts */
  tennis_outdoor_courts: number | null;
  /** Number of covered (but not fully indoor) tennis courts */
  tennis_covered_courts: number | null;
  /** Number of floodlit tennis courts for evening play */
  tennis_floodlit_courts: number | null;
  /** A short overall description of the padel facilities summarising all gathered data */
  padel_summary: string | null;
  /** Whether padel is available at this venue */
  padel: boolean | null;
  /** Total number of padel courts */
  padel_total_courts: number | null;
  /** A short overall description of the pickleball facilities summarising all gathered data */
  pickleball_summary: string | null;
  /** Whether pickleball is available at this venue */
  pickleball: boolean | null;
  /** Total number of pickleball courts */
  pickleball_total_courts: number | null;
  /** A short overall description of the badminton facilities summarising all gathered data */
  badminton_summary: string | null;
  /** Whether badminton is available at this venue */
  badminton: boolean | null;
  /** Total number of badminton courts */
  badminton_total_courts: number | null;
  /** A short overall description of the squash facilities summarising all gathered data */
  squash_summary: string | null;
  /** Whether squash is available at this venue */
  squash: boolean | null;
  /** Total number of squash courts */
  squash_total_courts: number | null;
  /** Number of squash courts with glass back walls */
  squash_glass_back_courts: number | null;
  /** A short overall description of the table tennis facilities summarising all gathered data */
  table_tennis_summary: string | null;
  /** Whether table tennis is available at this venue */
  table_tennis: boolean | null;
  /** Total number of table tennis tables */
  table_tennis_total_tables: number | null;
  /** A short overall description of the football facilities summarising all gathered data */
  football_summary: string | null;
  /** Whether 5-a-side football is available */
  football_5_a_side: boolean | null;
  /** Total number of 5-a-side pitches */
  football_5_a_side_total_pitches: number | null;
  /** Whether 7-a-side football is available */
  football_7_a_side: boolean | null;
  /** Total number of 7-a-side pitches */
  football_7_a_side_total_pitches: number | null;
  /** Whether full-size 11-a-side football is available */
  football_11_a_side: boolean | null;
  /** Total number of full-size 11-a-side pitches */
  football_11_a_side_total_pitches: number | null;
  /** A short overall description of the swimming facilities summarising all gathered data */
  swimming_summary: string | null;
  /** Whether an indoor swimming pool is available */
  indoor_pool: boolean | null;
  /** Whether an outdoor swimming pool is available */
  outdoor_pool: boolean | null;
  /** Length of the indoor pool in metres */
  indoor_pool_length_m: number | null;
  /** Length of the outdoor pool in metres */
  outdoor_pool_length_m: number | null;
  /** Whether family swim sessions are available */
  family_swim: boolean | null;
  /** Whether adult-only swim sessions are available */
  adult_only_swim: boolean | null;
  /** Whether swimming lessons are offered */
  swimming_lessons: boolean | null;
  /** A short overall description of the gym facilities summarising all gathered data */
  gym_summary: string | null;
  /** Whether a gym/fitness centre is available */
  gym_available: boolean | null;
  /** Size of the gym measured in number of stations */
  gym_size: number | null;
  /** A short overall description of the classes available summarising all gathered data */
  classes_summary: string | null;
  /** Total number of fitness classes offered per week */
  classes_per_week: number | null;
  /** Whether HIIT (High Intensity Interval Training) classes are offered */
  hiit_classes: boolean | null;
  /** Whether yoga classes are offered */
  yoga_classes: boolean | null;
  /** Whether pilates classes are offered */
  pilates_classes: boolean | null;
  /** Whether strength/weights classes are offered */
  strength_classes: boolean | null;
  /** Whether an indoor cycling/spin studio is available */
  cycling_studio: boolean | null;
  /** Whether a functional training zone is available */
  functional_training_zone: boolean | null;
  /** A short overall description of the spa and wellness facilities summarising all gathered data */
  spa_summary: string | null;
  /** Whether spa facilities are available */
  spa_available: boolean | null;
  /** Whether a sauna is available */
  sauna: boolean | null;
  /** Whether a steam room is available */
  steam_room: boolean | null;
  /** Whether a hydrotherapy pool is available */
  hydro_pool: boolean | null;
  /** Whether a hot tub/jacuzzi is available */
  hot_tub: boolean | null;
  /** Whether outdoor spa facilities are available */
  outdoor_spa: boolean | null;
  /** Whether an ice bath or cold plunge pool is available */
  ice_cold_plunge: boolean | null;
  /** Whether a dedicated relaxation area is available */
  relaxation_area: boolean | null;
  /** A short overall description of the amenities available (eg. bar, restaurant, cafe etc) summarising all gathered data */
  amenities_summary: string | null;
  /** Whether an on-site restaurant is available */
  restaurant: boolean | null;
  /** Whether an on-site bar is available */
  bar: boolean | null;
  /** Whether an on-site cafe is available */
  cafe: boolean | null;
  /** Whether a children's menu is available at dining facilities */
  childrens_menu: boolean | null;
  /** Whether free WiFi is available */
  wifi: boolean | null;
  /** A short overall description of the family and children facilities (eg. creche, kids lessons, holiday club, play area etc) summarising all gathered data */
  family_summary: string | null;
  /** Whether a creche/childcare facility is available */
  creche_available: boolean | null;
  /** Minimum age accepted at the creche (in months or years depending on venue) */
  creche_age_min: number | null;
  /** Maximum age accepted at the creche (in years) */
  creche_age_max: number | null;
  /** Whether swimming lessons for children are offered */
  kids_swimming_lessons: boolean | null;
  /** Whether tennis lessons for children are offered */
  kids_tennis_lessons: boolean | null;
  /** Whether a holiday club/camp for children is available */
  holiday_club: boolean | null;
  /** Whether a children's play area is available */
  play_area: boolean | null;
  /** A short overall description of the parking and transport facilities summarising all gathered data */
  parking_and_transport_summary: string | null;
  /** Total number of parking spaces available */
  parking_spaces: number | null;
  /** Whether disabled parking spaces are available */
  disabled_parking: boolean | null;
  /** Whether parent and child parking spaces are available */
  parent_child_parking: boolean | null;
  /** Whether electric vehicle charging points are available */
  ev_charging_available: boolean | null;
  /** Number of EV charging connectors available */
  ev_charging_connectors: number | null;
  /** Whether public transport links are nearby */
  public_transport_nearby: boolean | null;
  /** Name of the nearest railway station */
  nearest_railway_station: string | null;
  /** A short overall description of reviews and social proof (eg. rating, review count, likes etc) summarising all gathered data */
  reviews_summary: string | null;
  /** Total number of reviews across all platforms */
  review_count: number | null;
  /** Number of Google reviews */
  google_review_count: number | null;
  /** Number of Facebook page likes */
  facebook_likes: number | null;
}

export const VenueSchema = z.object({
  listing_id: z.string(),
  tennis_summary: z.string().nullable(),
  tennis: z.boolean().nullable(),
  tennis_total_courts: z.number().int().nullable(),
  tennis_indoor_courts: z.number().int().nullable(),
  tennis_outdoor_courts: z.number().int().nullable(),
  tennis_covered_courts: z.number().int().nullable(),
  tennis_floodlit_courts: z.number().int().nullable(),
  padel_summary: z.string().nullable(),
  padel: z.boolean().nullable(),
  padel_total_courts: z.number().int().nullable(),
  pickleball_summary: z.string().nullable(),
  pickleball: z.boolean().nullable(),
  pickleball_total_courts: z.number().int().nullable(),
  badminton_summary: z.string().nullable(),
  badminton: z.boolean().nullable(),
  badminton_total_courts: z.number().int().nullable(),
  squash_summary: z.string().nullable(),
  squash: z.boolean().nullable(),
  squash_total_courts: z.number().int().nullable(),
  squash_glass_back_courts: z.number().int().nullable(),
  table_tennis_summary: z.string().nullable(),
  table_tennis: z.boolean().nullable(),
  table_tennis_total_tables: z.number().int().nullable(),
  football_summary: z.string().nullable(),
  football_5_a_side: z.boolean().nullable(),
  football_5_a_side_total_pitches: z.number().int().nullable(),
  football_7_a_side: z.boolean().nullable(),
  football_7_a_side_total_pitches: z.number().int().nullable(),
  football_11_a_side: z.boolean().nullable(),
  football_11_a_side_total_pitches: z.number().int().nullable(),
  swimming_summary: z.string().nullable(),
  indoor_pool: z.boolean().nullable(),
  outdoor_pool: z.boolean().nullable(),
  indoor_pool_length_m: z.number().int().nullable(),
  outdoor_pool_length_m: z.number().int().nullable(),
  family_swim: z.boolean().nullable(),
  adult_only_swim: z.boolean().nullable(),
  swimming_lessons: z.boolean().nullable(),
  gym_summary: z.string().nullable(),
  gym_available: z.boolean().nullable(),
  gym_size: z.number().int().nullable(),
  classes_summary: z.string().nullable(),
  classes_per_week: z.number().int().nullable(),
  hiit_classes: z.boolean().nullable(),
  yoga_classes: z.boolean().nullable(),
  pilates_classes: z.boolean().nullable(),
  strength_classes: z.boolean().nullable(),
  cycling_studio: z.boolean().nullable(),
  functional_training_zone: z.boolean().nullable(),
  spa_summary: z.string().nullable(),
  spa_available: z.boolean().nullable(),
  sauna: z.boolean().nullable(),
  steam_room: z.boolean().nullable(),
  hydro_pool: z.boolean().nullable(),
  hot_tub: z.boolean().nullable(),
  outdoor_spa: z.boolean().nullable(),
  ice_cold_plunge: z.boolean().nullable(),
  relaxation_area: z.boolean().nullable(),
  amenities_summary: z.string().nullable(),
  restaurant: z.boolean().nullable(),
  bar: z.boolean().nullable(),
  cafe: z.boolean().nullable(),
  childrens_menu: z.boolean().nullable(),
  wifi: z.boolean().nullable(),
  family_summary: z.string().nullable(),
  creche_available: z.boolean().nullable(),
  creche_age_min: z.number().int().nullable(),
  creche_age_max: z.number().int().nullable(),
  kids_swimming_lessons: z.boolean().nullable(),
  kids_tennis_lessons: z.boolean().nullable(),
  holiday_club: z.boolean().nullable(),
  play_area: z.boolean().nullable(),
  parking_and_transport_summary: z.string().nullable(),
  parking_spaces: z.number().int().nullable(),
  disabled_parking: z.boolean().nullable(),
  parent_child_parking: z.boolean().nullable(),
  ev_charging_available: z.boolean().nullable(),
  ev_charging_connectors: z.number().int().nullable(),
  public_transport_nearby: z.boolean().nullable(),
  nearest_railway_station: z.string().nullable(),
  reviews_summary: z.string().nullable(),
  review_count: z.number().int().nullable(),
  google_review_count: z.number().int().nullable(),
  facebook_likes: z.number().int().nullable(),
});
