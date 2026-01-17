-- CreateIndex
CREATE INDEX "ExtractedListing_source_entity_type_idx" ON "ExtractedListing"("source", "entity_type");

-- CreateIndex
CREATE INDEX "ExtractedListing_createdAt_idx" ON "ExtractedListing"("createdAt");

-- CreateIndex
CREATE INDEX "FailedExtraction_last_attempt_at_idx" ON "FailedExtraction"("last_attempt_at");

-- CreateIndex
CREATE INDEX "FailedExtraction_retry_count_last_attempt_at_idx" ON "FailedExtraction"("retry_count", "last_attempt_at");

-- CreateIndex
CREATE INDEX "Listing_entityType_idx" ON "Listing"("entityType");

-- CreateIndex
CREATE INDEX "Listing_city_idx" ON "Listing"("city");

-- CreateIndex
CREATE INDEX "Listing_postcode_idx" ON "Listing"("postcode");

-- CreateIndex
CREATE INDEX "Listing_latitude_longitude_idx" ON "Listing"("latitude", "longitude");

-- CreateIndex
CREATE INDEX "Listing_createdAt_idx" ON "Listing"("createdAt");

-- CreateIndex
CREATE INDEX "Listing_updatedAt_idx" ON "Listing"("updatedAt");

-- CreateIndex
CREATE INDEX "RawIngestion_ingested_at_idx" ON "RawIngestion"("ingested_at");

-- CreateIndex
CREATE INDEX "RawIngestion_source_status_idx" ON "RawIngestion"("source", "status");

-- CreateIndex
CREATE INDEX "RawIngestion_status_ingested_at_idx" ON "RawIngestion"("status", "ingested_at");
