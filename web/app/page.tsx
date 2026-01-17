import prisma from "@/lib/prisma";
import { parseAttributesJSON, formatAttributeKey, formatAttributeValue } from "@/lib/utils";

export default async function Home() {
  const listings = await prisma.listing.findMany({
    take: 5,
    select: {
      id: true,
      entity_name: true,
      summary: true,
      entityType: true,
      attributes: true,
      discovered_attributes: true,
    },
  });

  return (
    <main className="flex min-h-screen flex-col items-center p-24 bg-zinc-50 dark:bg-zinc-900">
      <h1 className="text-4xl font-bold mb-8 text-zinc-900 dark:text-zinc-50">Edinburgh Finds</h1>
      <div className="w-full max-w-2xl">
        <h2 className="text-2xl font-semibold mb-4 text-zinc-800 dark:text-zinc-200">Database Connection Check</h2>
        {listings.length === 0 ? (
          <p className="text-zinc-500">No listings found in the database.</p>
        ) : (
          <ul className="space-y-4">
            {listings.map((listing) => {
              const attributes = parseAttributesJSON(listing.attributes);
              const discoveredAttributes = parseAttributesJSON(listing.discovered_attributes);
              const hasAttributes = Object.keys(attributes).length > 0;
              const hasDiscoveredAttributes = Object.keys(discoveredAttributes).length > 0;

              return (
                <li key={listing.id} className="p-6 border border-zinc-200 rounded-lg shadow-sm bg-white dark:bg-zinc-800 dark:border-zinc-700">
                  <div className="flex justify-between items-start">
                    <h3 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">{listing.entity_name}</h3>
                    <span className="px-2 py-1 text-xs font-medium bg-zinc-100 text-zinc-600 rounded-full dark:bg-zinc-700 dark:text-zinc-300">
                      {listing.entityType}
                    </span>
                  </div>
                  {listing.summary && (
                    <p className="mt-2 text-zinc-600 dark:text-zinc-400">{listing.summary}</p>
                  )}

                  {/* Structured Attributes Section */}
                  {hasAttributes && (
                    <div className="mt-4">
                      <h4 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2">Attributes</h4>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(attributes).map(([key, value]) => (
                          <div key={key} className="text-sm">
                            <span className="text-zinc-500 dark:text-zinc-400">{formatAttributeKey(key)}:</span>{' '}
                            <span className="text-zinc-700 dark:text-zinc-200 font-medium">{formatAttributeValue(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Discovered Attributes Badge */}
                  {hasDiscoveredAttributes && (
                    <div className="mt-3">
                      <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded dark:bg-blue-900 dark:text-blue-200">
                        + {Object.keys(discoveredAttributes).length} additional properties
                      </span>
                    </div>
                  )}

                  <p className="mt-4 text-xs font-mono text-zinc-400">ID: {listing.id}</p>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </main>
  );
}