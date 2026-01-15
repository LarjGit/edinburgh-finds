/*
  Warnings:

  - You are about to drop the `EntityType` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `_CategoryToEntityType` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the column `entityTypeId` on the `Listing` table. All the data in the column will be lost.
  - Added the required column `entityType` to the `Listing` table without a default value. This is not possible if the table is not empty.

*/
-- DropIndex
DROP INDEX "EntityType_slug_key";

-- DropIndex
DROP INDEX "EntityType_name_key";

-- DropIndex
DROP INDEX "_CategoryToEntityType_B_index";

-- DropIndex
DROP INDEX "_CategoryToEntityType_AB_unique";

-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "EntityType";
PRAGMA foreign_keys=on;

-- DropTable
PRAGMA foreign_keys=off;
DROP TABLE "_CategoryToEntityType";
PRAGMA foreign_keys=on;

-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Listing" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "entity_name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "entityType" TEXT NOT NULL,
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
    "updatedAt" DATETIME NOT NULL
);
INSERT INTO "new_Listing" ("attributes", "city", "country", "createdAt", "discovered_attributes", "email", "entity_name", "external_ids", "facebook_url", "field_confidence", "id", "instagram_url", "latitude", "linkedin_url", "longitude", "mainImage", "opening_hours", "phone", "postcode", "slug", "source_info", "street_address", "summary", "twitter_url", "updatedAt", "website_url") SELECT "attributes", "city", "country", "createdAt", "discovered_attributes", "email", "entity_name", "external_ids", "facebook_url", "field_confidence", "id", "instagram_url", "latitude", "linkedin_url", "longitude", "mainImage", "opening_hours", "phone", "postcode", "slug", "source_info", "street_address", "summary", "twitter_url", "updatedAt", "website_url" FROM "Listing";
DROP TABLE "Listing";
ALTER TABLE "new_Listing" RENAME TO "Listing";
CREATE UNIQUE INDEX "Listing_slug_key" ON "Listing"("slug");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
