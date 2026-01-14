-- CreateTable
CREATE TABLE "ListingRelationship" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "sourceListingId" TEXT NOT NULL,
    "targetListingId" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "confidence" REAL,
    "source" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "ListingRelationship_sourceListingId_fkey" FOREIGN KEY ("sourceListingId") REFERENCES "Listing" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "ListingRelationship_targetListingId_fkey" FOREIGN KEY ("targetListingId") REFERENCES "Listing" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE INDEX "ListingRelationship_sourceListingId_idx" ON "ListingRelationship"("sourceListingId");

-- CreateIndex
CREATE INDEX "ListingRelationship_targetListingId_idx" ON "ListingRelationship"("targetListingId");

-- CreateIndex
CREATE INDEX "ListingRelationship_type_idx" ON "ListingRelationship"("type");
