-- CreateTable
CREATE TABLE "RawIngestion" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "source" TEXT NOT NULL,
    "source_url" TEXT NOT NULL,
    "file_path" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "ingested_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "hash" TEXT NOT NULL,
    "metadata_json" TEXT
);

-- CreateIndex
CREATE INDEX "RawIngestion_source_idx" ON "RawIngestion"("source");

-- CreateIndex
CREATE INDEX "RawIngestion_status_idx" ON "RawIngestion"("status");

-- CreateIndex
CREATE INDEX "RawIngestion_hash_idx" ON "RawIngestion"("hash");
