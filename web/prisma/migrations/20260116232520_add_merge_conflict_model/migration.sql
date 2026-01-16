-- CreateTable
CREATE TABLE "MergeConflict" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "field_name" TEXT NOT NULL,
    "conflicting_values" TEXT NOT NULL,
    "winner_source" TEXT NOT NULL,
    "winner_value" TEXT NOT NULL,
    "trust_difference" INTEGER NOT NULL,
    "severity" REAL NOT NULL,
    "listing_id" TEXT,
    "resolved" BOOLEAN NOT NULL DEFAULT false,
    "resolution_notes" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateIndex
CREATE INDEX "MergeConflict_field_name_idx" ON "MergeConflict"("field_name");

-- CreateIndex
CREATE INDEX "MergeConflict_winner_source_idx" ON "MergeConflict"("winner_source");

-- CreateIndex
CREATE INDEX "MergeConflict_severity_idx" ON "MergeConflict"("severity");

-- CreateIndex
CREATE INDEX "MergeConflict_resolved_idx" ON "MergeConflict"("resolved");

-- CreateIndex
CREATE INDEX "MergeConflict_listing_id_idx" ON "MergeConflict"("listing_id");
