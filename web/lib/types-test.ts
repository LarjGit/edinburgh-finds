/**
 * Type checking test for generated schemas
 * This file verifies that the generated TypeScript types and Zod schemas work correctly.
 */

import { Listing, ListingSchema, Venue } from "../types";

// Test 1: TypeScript interface type checking
const testListing: Listing = {
  listing_id: "test-123",
  entity_name: "Test Venue",
  entity_type: "venue",
  slug: "test-venue",
  summary: "A test venue for TypeScript validation",
  categories: ["sports", "recreation"],
  canonical_categories: ["Sports Venue"],
  discovered_attributes: { parking: true },
  street_address: "123 Test St",
  city: "Edinburgh",
  postcode: "EH1 1AA",
  country: "Scotland",
  latitude: 55.9533,
  longitude: -3.1883,
  phone: "+441234567890",
  email: "test@example.com",
  website_url: "https://example.com",
  instagram_url: null,
  facebook_url: null,
  twitter_url: null,
  linkedin_url: null,
  opening_hours: { monday: { open: "09:00", close: "17:00" } },
  source_info: { source: "test" },
  field_confidence: {},
  created_at: new Date(),
  updated_at: new Date(),
  external_ids: {},
};

// Test 2: Zod schema runtime validation (valid data)
const validationResult = ListingSchema.safeParse(testListing);
if (!validationResult.success) {
  console.error("Zod validation failed:", validationResult.error);
  throw new Error("Type test failed: Valid listing did not pass Zod validation");
}

// Test 3: Partial Venue (more realistic for actual usage)
const partialVenue: Partial<Venue> = {
  ...testListing,
  tennis_summary: "2 courts available",
  tennis: true,
  tennis_total_courts: 2,
  tennis_indoor_courts: 0,
  tennis_outdoor_courts: 2,
  tennis_covered_courts: 0,
  tennis_floodlit_courts: 1,
  padel: false,
  padel_total_courts: null,
};

// Test 4: Verify type narrowing works
function processListing(listing: Listing | Venue) {
  // Should work for both types
  console.log(listing.entity_name);

  // Type narrowing
  if ("tennis" in listing) {
    const venue = listing as Venue;
    console.log(venue.tennis_total_courts);
  }
}

processListing(testListing);
if (partialVenue.entity_name) {
  processListing(partialVenue as Venue);
}

// Test 5: Verify Record types work correctly
const attributes: Record<string, any> = {
  custom_field1: "value1",
  custom_field2: 123,
  custom_field3: true,
};

testListing.discovered_attributes = attributes;

console.log("✓ All type tests passed!");

export { testListing, partialVenue };
