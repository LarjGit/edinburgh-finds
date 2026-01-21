-- CreateTable
CREATE TABLE "Entity" (
    "id" TEXT NOT NULL,
    "entity_name" TEXT NOT NULL,
    "entity_class" TEXT NOT NULL,
    "slug" TEXT NOT NULL,
    "summary" TEXT,
    "attributes" TEXT,
    "raw_categories" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "canonical_activities" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "canonical_roles" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "canonical_place_types" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "canonical_access" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "discovered_attributes" JSONB,
    "modules" JSONB NOT NULL,
    "street_address" TEXT,
    "city" TEXT,
    "postcode" TEXT,
    "country" TEXT,
    "latitude" DOUBLE PRECISION,
    "longitude" DOUBLE PRECISION,
    "phone" TEXT,
    "email" TEXT,
    "website_url" TEXT,
    "instagram_url" TEXT,
    "facebook_url" TEXT,
    "twitter_url" TEXT,
    "linkedin_url" TEXT,
    "mainImage" TEXT,
    "opening_hours" JSONB,
    "source_info" JSONB,
    "field_confidence" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    "external_ids" JSONB,

    CONSTRAINT "Entity_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "EntityRelationship" (
    "id" TEXT NOT NULL,
    "sourceEntityId" TEXT NOT NULL,
    "targetEntityId" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "confidence" DOUBLE PRECISION,
    "source" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "EntityRelationship_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ExtractedEntity" (
    "id" TEXT NOT NULL,
    "raw_ingestion_id" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "entity_class" TEXT NOT NULL,
    "attributes" TEXT,
    "discovered_attributes" TEXT,
    "external_ids" TEXT,
    "extraction_hash" TEXT,
    "model_used" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ExtractedEntity_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "FailedExtraction" (
    "id" TEXT NOT NULL,
    "raw_ingestion_id" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "error_message" TEXT NOT NULL,
    "error_details" TEXT,
    "retry_count" INTEGER NOT NULL DEFAULT 0,
    "last_attempt_at" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "FailedExtraction_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "MergeConflict" (
    "id" TEXT NOT NULL,
    "field_name" TEXT NOT NULL,
    "conflicting_values" TEXT NOT NULL,
    "winner_source" TEXT NOT NULL,
    "winner_value" TEXT NOT NULL,
    "trust_difference" INTEGER NOT NULL,
    "severity" DOUBLE PRECISION NOT NULL,
    "entity_id" TEXT,
    "resolved" BOOLEAN NOT NULL DEFAULT false,
    "resolution_notes" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "MergeConflict_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "LensEntity" (
    "lensId" TEXT NOT NULL,
    "entityId" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "LensEntity_pkey" PRIMARY KEY ("lensId","entityId")
);

-- CreateTable
CREATE TABLE "RawIngestion" (
    "id" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "source_url" TEXT NOT NULL,
    "file_path" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "ingested_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "hash" TEXT NOT NULL,
    "metadata_json" TEXT,

    CONSTRAINT "RawIngestion_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "Entity_slug_key" ON "Entity"("slug");

-- CreateIndex
CREATE INDEX "Entity_entity_name_idx" ON "Entity"("entity_name");

-- CreateIndex
CREATE INDEX "Entity_entity_class_idx" ON "Entity"("entity_class");

-- CreateIndex
CREATE INDEX "Entity_city_idx" ON "Entity"("city");

-- CreateIndex
CREATE INDEX "Entity_postcode_idx" ON "Entity"("postcode");

-- CreateIndex
CREATE INDEX "Entity_latitude_longitude_idx" ON "Entity"("latitude", "longitude");

-- CreateIndex
CREATE INDEX "Entity_createdAt_idx" ON "Entity"("createdAt");

-- CreateIndex
CREATE INDEX "Entity_updatedAt_idx" ON "Entity"("updatedAt");

-- CreateIndex
CREATE INDEX "EntityRelationship_sourceEntityId_idx" ON "EntityRelationship"("sourceEntityId");

-- CreateIndex
CREATE INDEX "EntityRelationship_targetEntityId_idx" ON "EntityRelationship"("targetEntityId");

-- CreateIndex
CREATE INDEX "EntityRelationship_type_idx" ON "EntityRelationship"("type");

-- CreateIndex
CREATE INDEX "ExtractedEntity_raw_ingestion_id_idx" ON "ExtractedEntity"("raw_ingestion_id");

-- CreateIndex
CREATE INDEX "ExtractedEntity_source_idx" ON "ExtractedEntity"("source");

-- CreateIndex
CREATE INDEX "ExtractedEntity_entity_class_idx" ON "ExtractedEntity"("entity_class");

-- CreateIndex
CREATE INDEX "ExtractedEntity_extraction_hash_idx" ON "ExtractedEntity"("extraction_hash");

-- CreateIndex
CREATE INDEX "ExtractedEntity_source_entity_class_idx" ON "ExtractedEntity"("source", "entity_class");

-- CreateIndex
CREATE INDEX "ExtractedEntity_createdAt_idx" ON "ExtractedEntity"("createdAt");

-- CreateIndex
CREATE INDEX "FailedExtraction_raw_ingestion_id_idx" ON "FailedExtraction"("raw_ingestion_id");

-- CreateIndex
CREATE INDEX "FailedExtraction_source_idx" ON "FailedExtraction"("source");

-- CreateIndex
CREATE INDEX "FailedExtraction_retry_count_idx" ON "FailedExtraction"("retry_count");

-- CreateIndex
CREATE INDEX "FailedExtraction_last_attempt_at_idx" ON "FailedExtraction"("last_attempt_at");

-- CreateIndex
CREATE INDEX "FailedExtraction_retry_count_last_attempt_at_idx" ON "FailedExtraction"("retry_count", "last_attempt_at");

-- CreateIndex
CREATE INDEX "MergeConflict_field_name_idx" ON "MergeConflict"("field_name");

-- CreateIndex
CREATE INDEX "MergeConflict_winner_source_idx" ON "MergeConflict"("winner_source");

-- CreateIndex
CREATE INDEX "MergeConflict_severity_idx" ON "MergeConflict"("severity");

-- CreateIndex
CREATE INDEX "MergeConflict_resolved_idx" ON "MergeConflict"("resolved");

-- CreateIndex
CREATE INDEX "MergeConflict_entity_id_idx" ON "MergeConflict"("entity_id");

-- CreateIndex
CREATE INDEX "LensEntity_lensId_idx" ON "LensEntity"("lensId");

-- CreateIndex
CREATE INDEX "LensEntity_entityId_idx" ON "LensEntity"("entityId");

-- CreateIndex
CREATE INDEX "RawIngestion_source_idx" ON "RawIngestion"("source");

-- CreateIndex
CREATE INDEX "RawIngestion_status_idx" ON "RawIngestion"("status");

-- CreateIndex
CREATE INDEX "RawIngestion_hash_idx" ON "RawIngestion"("hash");

-- CreateIndex
CREATE INDEX "RawIngestion_ingested_at_idx" ON "RawIngestion"("ingested_at");

-- CreateIndex
CREATE INDEX "RawIngestion_source_status_idx" ON "RawIngestion"("source", "status");

-- CreateIndex
CREATE INDEX "RawIngestion_status_ingested_at_idx" ON "RawIngestion"("status", "ingested_at");

-- AddForeignKey
ALTER TABLE "EntityRelationship" ADD CONSTRAINT "EntityRelationship_sourceEntityId_fkey" FOREIGN KEY ("sourceEntityId") REFERENCES "Entity"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "EntityRelationship" ADD CONSTRAINT "EntityRelationship_targetEntityId_fkey" FOREIGN KEY ("targetEntityId") REFERENCES "Entity"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ExtractedEntity" ADD CONSTRAINT "ExtractedEntity_raw_ingestion_id_fkey" FOREIGN KEY ("raw_ingestion_id") REFERENCES "RawIngestion"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "FailedExtraction" ADD CONSTRAINT "FailedExtraction_raw_ingestion_id_fkey" FOREIGN KEY ("raw_ingestion_id") REFERENCES "RawIngestion"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LensEntity" ADD CONSTRAINT "LensEntity_entityId_fkey" FOREIGN KEY ("entityId") REFERENCES "Entity"("id") ON DELETE CASCADE ON UPDATE CASCADE;
