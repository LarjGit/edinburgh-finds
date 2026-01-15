-- CreateTable
CREATE TABLE "ExtractedListing" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "raw_ingestion_id" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "entity_type" TEXT NOT NULL,
    "attributes" TEXT,
    "discovered_attributes" TEXT,
    "external_ids" TEXT,
    "extraction_hash" TEXT,
    "model_used" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "ExtractedListing_raw_ingestion_id_fkey" FOREIGN KEY ("raw_ingestion_id") REFERENCES "RawIngestion" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "FailedExtraction" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "raw_ingestion_id" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "error_message" TEXT NOT NULL,
    "error_details" TEXT,
    "retry_count" INTEGER NOT NULL DEFAULT 0,
    "last_attempt_at" DATETIME,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "FailedExtraction_raw_ingestion_id_fkey" FOREIGN KEY ("raw_ingestion_id") REFERENCES "RawIngestion" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE INDEX "ExtractedListing_raw_ingestion_id_idx" ON "ExtractedListing"("raw_ingestion_id");

-- CreateIndex
CREATE INDEX "ExtractedListing_source_idx" ON "ExtractedListing"("source");

-- CreateIndex
CREATE INDEX "ExtractedListing_entity_type_idx" ON "ExtractedListing"("entity_type");

-- CreateIndex
CREATE INDEX "ExtractedListing_extraction_hash_idx" ON "ExtractedListing"("extraction_hash");

-- CreateIndex
CREATE INDEX "FailedExtraction_raw_ingestion_id_idx" ON "FailedExtraction"("raw_ingestion_id");

-- CreateIndex
CREATE INDEX "FailedExtraction_source_idx" ON "FailedExtraction"("source");

-- CreateIndex
CREATE INDEX "FailedExtraction_retry_count_idx" ON "FailedExtraction"("retry_count");
