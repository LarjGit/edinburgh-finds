-- CreateTable
CREATE TABLE "Category" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "description" TEXT,
    "image" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "EntityType" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "Listing" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "entity_name" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "entityTypeId" TEXT NOT NULL,
    "summary" TEXT,
    "other_attributes" TEXT,
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

-- CreateTable
CREATE TABLE "Venue" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "listingId" TEXT NOT NULL,
    "tennis_summary" TEXT,
    "tennis" BOOLEAN,
    "tennis_total_courts" INTEGER,
    "tennis_indoor_courts" INTEGER,
    "tennis_outdoor_courts" INTEGER,
    "tennis_covered_courts" INTEGER,
    "tennis_floodlit_courts" INTEGER,
    "padel_summary" TEXT,
    "padel" BOOLEAN,
    "padel_total_courts" INTEGER,
    "pickleball_summary" TEXT,
    "pickleball" BOOLEAN,
    "pickleball_total_courts" INTEGER,
    "badminton_summary" TEXT,
    "badminton" BOOLEAN,
    "badminton_total_courts" INTEGER,
    "squash_summary" TEXT,
    "squash" BOOLEAN,
    "squash_total_courts" INTEGER,
    "squash_glass_back_courts" INTEGER,
    "table_tennis_summary" TEXT,
    "table_tennis" BOOLEAN,
    "table_tennis_total_tables" INTEGER,
    "football_summary" TEXT,
    "football_5_a_side" BOOLEAN,
    "football_5_a_side_total_pitches" INTEGER,
    "football_7_a_side" BOOLEAN,
    "football_7_a_side_total_pitches" INTEGER,
    "football_11_a_side" BOOLEAN,
    "football_11_a_side_total_pitches" INTEGER,
    "swimming_summary" TEXT,
    "indoor_pool" BOOLEAN,
    "outdoor_pool" BOOLEAN,
    "indoor_pool_length_m" INTEGER,
    "outdoor_pool_length_m" INTEGER,
    "family_swim" BOOLEAN,
    "adult_only_swim" BOOLEAN,
    "swimming_lessons" BOOLEAN,
    "gym_summary" TEXT,
    "gym_available" BOOLEAN,
    "gym_size" INTEGER,
    "classes_summary" TEXT,
    "classes_per_week" INTEGER,
    "hiit_classes" BOOLEAN,
    "yoga_classes" BOOLEAN,
    "pilates_classes" BOOLEAN,
    "strength_classes" BOOLEAN,
    "cycling_studio" BOOLEAN,
    "functional_training_zone" BOOLEAN,
    "spa_summary" TEXT,
    "spa_available" BOOLEAN,
    "sauna" BOOLEAN,
    "steam_room" BOOLEAN,
    "hydro_pool" BOOLEAN,
    "hot_tub" BOOLEAN,
    "outdoor_spa" BOOLEAN,
    "ice_cold_plunge" BOOLEAN,
    "relaxation_area" BOOLEAN,
    "amenities_summary" TEXT,
    "restaurant" BOOLEAN,
    "bar" BOOLEAN,
    "cafe" BOOLEAN,
    "childrens_menu" BOOLEAN,
    "wifi" BOOLEAN,
    "family_summary" TEXT,
    "creche_available" BOOLEAN,
    "creche_age_min" INTEGER,
    "creche_age_max" INTEGER,
    "kids_swimming_lessons" BOOLEAN,
    "kids_tennis_lessons" BOOLEAN,
    "holiday_club" BOOLEAN,
    "play_area" BOOLEAN,
    "parking_and_transport_summary" TEXT,
    "parking_spaces" INTEGER,
    "disabled_parking" BOOLEAN,
    "parent_child_parking" BOOLEAN,
    "ev_charging_available" BOOLEAN,
    "ev_charging_connectors" INTEGER,
    "public_transport_nearby" BOOLEAN,
    "nearest_railway_station" TEXT,
    "reviews_summary" TEXT,
    "review_count" INTEGER,
    "google_review_count" INTEGER,
    "facebook_likes" INTEGER,
    CONSTRAINT "Venue_listingId_fkey" FOREIGN KEY ("listingId") REFERENCES "Listing" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Coach" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "listingId" TEXT NOT NULL,
    "hourlyRate" REAL,
    "bio" TEXT,
    "experience" TEXT,
    CONSTRAINT "Coach_listingId_fkey" FOREIGN KEY ("listingId") REFERENCES "Listing" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "_CategoryToEntityType" (
    "A" TEXT NOT NULL,
    "B" TEXT NOT NULL,
    CONSTRAINT "_CategoryToEntityType_A_fkey" FOREIGN KEY ("A") REFERENCES "Category" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "_CategoryToEntityType_B_fkey" FOREIGN KEY ("B") REFERENCES "EntityType" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "_CategoryToListing" (
    "A" TEXT NOT NULL,
    "B" TEXT NOT NULL,
    CONSTRAINT "_CategoryToListing_A_fkey" FOREIGN KEY ("A") REFERENCES "Category" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "_CategoryToListing_B_fkey" FOREIGN KEY ("B") REFERENCES "Listing" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "Category_name_key" ON "Category"("name");

-- CreateIndex
CREATE UNIQUE INDEX "Category_slug_key" ON "Category"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "EntityType_name_key" ON "EntityType"("name");

-- CreateIndex
CREATE UNIQUE INDEX "EntityType_slug_key" ON "EntityType"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "Listing_slug_key" ON "Listing"("slug");

-- CreateIndex
CREATE UNIQUE INDEX "Venue_listingId_key" ON "Venue"("listingId");

-- CreateIndex
CREATE UNIQUE INDEX "Coach_listingId_key" ON "Coach"("listingId");

-- CreateIndex
CREATE UNIQUE INDEX "_CategoryToEntityType_AB_unique" ON "_CategoryToEntityType"("A", "B");

-- CreateIndex
CREATE INDEX "_CategoryToEntityType_B_index" ON "_CategoryToEntityType"("B");

-- CreateIndex
CREATE UNIQUE INDEX "_CategoryToListing_AB_unique" ON "_CategoryToListing"("A", "B");

-- CreateIndex
CREATE INDEX "_CategoryToListing_B_index" ON "_CategoryToListing"("B");
