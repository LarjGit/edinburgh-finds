/*
  Warnings:

  - You are about to drop the `Coach` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `Venue` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the column `other_attributes` on the `Listing` table. All the data in the column will be lost.

*/
-- DropIndex
DROP INDEX "Coach_listingId_key";

-- DropIndex
DROP INDEX "Venue_listingId_key";

-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "Coach";
PRAGMA foreign_keys=on;

-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "Venue";
PRAGMA foreign_keys=on;

-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Listing" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "entity_name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "entityTypeId" TEXT NOT NULL,
    "summary" TEXT,
    "attributes" TEXT,
    "discovered_attributes" TEXT,
    "street_address" TEXT,
    "city" TEXT,
    "postcode" TEXT,
    "country" TEXT,
    "latitude" REAL,
    "longitude" REAL,
    "phone" TEXT,
    "email" TEXT,
    "website_url" TEXT,
    "instagram_url" TEXT,
    "facebook_url" TEXT,
    "twitter_url" TEXT,
    "linkedin_url" TEXT,
    "mainImage" TEXT,
    "opening_hours" TEXT,
    "source_info" TEXT,
    "field_confidence" TEXT,
    "external_ids" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "Listing_entityTypeId_fkey" FOREIGN KEY ("entityTypeId") REFERENCES "EntityType" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);
INSERT INTO "new_Listing" ("city", "country", "createdAt", "email", "entityTypeId", "entity_name", "external_ids", "facebook_url", "field_confidence", "id", "instagram_url", "latitude", "linkedin_url", "longitude", "mainImage", "opening_hours", "phone", "postcode", "slug", "source_info", "street_address", "summary", "twitter_url", "updatedAt", "website_url") SELECT "city", "country", "createdAt", "email", "entityTypeId", "entity_name", "external_ids", "facebook_url", "field_confidence", "id", "instagram_url", "latitude", "linkedin_url", "longitude", "mainImage", "opening_hours", "phone", "postcode", "slug", "source_info", "street_address", "summary", "twitter_url", "updatedAt", "website_url" FROM "Listing";
DROP TABLE "Listing";
ALTER TABLE "new_Listing" RENAME TO "Listing";
CREATE UNIQUE INDEX "Listing_slug_key" ON "Listing"("slug");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
