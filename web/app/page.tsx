import prisma from "@/lib/prisma";
import { parseAttributesJSON, formatAttributeKey, formatAttributeValue } from "@/lib/utils";
import { parseDimensionArray, parseModules } from "@/lib/entity-helpers";

export default async function Home() {
  // Example 1: Get all listings (unfiltered)
  const listings = await prisma.listing.findMany({
    take: 5,
    select: {
      id: true,
      entity_name: true,
      summary: true,
      entityType: true,
      entity_class: true,
      canonical_activities: true,
      canonical_roles: true,
      canonical_place_types: true,
      canonical_access: true,
      modules: true,
      attributes: true,
      discovered_attributes: true,
    },
  });

  // Example 2: Filtered query using Prisma array filters (demonstrates new architecture)
  // NOTE: Prisma array filters (hasSome, has, hasEvery) only work with native PostgreSQL arrays.
  // SQLite stores dimensions as JSON strings, so array filters are not supported.
  // This will be fully functional when migrating to Postgres/Supabase.
  const filteredListings = await prisma.listing.findMany({
    where: {
      entity_class: "place", // Basic filtering still works
    },
    take: 3,
    select: {
      id: true,
      entity_name: true,
      entity_class: true,
      canonical_activities: true,
      canonical_roles: true,
    },
  });

  return (
    <main className="flex min-h-screen flex-col items-center p-24 bg-zinc-50 dark:bg-zinc-900">
      <h1 className="text-4xl font-bold mb-8 text-zinc-900 dark:text-zinc-50">Edinburgh Finds</h1>

      {/* Filtered Query Example - Demonstrates Prisma Array Filters */}
      {filteredListings.length > 0 && (
        <div className="w-full max-w-2xl mb-8 p-4 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h2 className="text-lg font-semibold mb-2 text-blue-900 dark:text-blue-100">
            Prisma Array Filter Example
          </h2>
          <p className="text-sm text-blue-700 dark:text-blue-300 mb-3">
            Filtered query: entity_class = "place" (using buildFacetedWhere)
          </p>
          <ul className="space-y-2">
            {filteredListings.map((listing) => {
              const activities = parseDimensionArray(listing.canonical_activities);
              return (
                <li key={listing.id} className="text-sm text-blue-800 dark:text-blue-200">
                  <strong>{listing.entity_name}</strong> - {listing.entity_class}
                  {activities.length > 0 && (
                    <span className="ml-2 text-xs">
                      ({activities.join(", ")})
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="w-full max-w-2xl">
        <h2 className="text-2xl font-semibold mb-4 text-zinc-800 dark:text-zinc-200">All Listings</h2>
        {listings.length === 0 ? (
          <p className="text-zinc-500">No listings found in the database.</p>
        ) : (
          <ul className="space-y-4">
            {listings.map((listing) => {
              const attributes = parseAttributesJSON(listing.attributes);
              const discoveredAttributes = parseAttributesJSON(listing.discovered_attributes);
              const hasAttributes = Object.keys(attributes).length > 0;
              const hasDiscoveredAttributes = Object.keys(discoveredAttributes).length > 0;

              // Parse dimension arrays (SQLite JSON strings)
              const activities = parseDimensionArray(listing.canonical_activities);
              const roles = parseDimensionArray(listing.canonical_roles);
              const placeTypes = parseDimensionArray(listing.canonical_place_types);
              const access = parseDimensionArray(listing.canonical_access);
              const modules = parseModules(listing.modules);

              return (
                <li key={listing.id} className="p-6 border border-zinc-200 rounded-lg shadow-sm bg-white dark:bg-zinc-800 dark:border-zinc-700">
                  <div className="flex justify-between items-start">
                    <h3 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">{listing.entity_name}</h3>
                    <div className="flex gap-2">
                      {listing.entity_class && (
                        <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded-full dark:bg-blue-900 dark:text-blue-200">
                          {listing.entity_class}
                        </span>
                      )}
                      <span className="px-2 py-1 text-xs font-medium bg-zinc-100 text-zinc-600 rounded-full dark:bg-zinc-700 dark:text-zinc-300">
                        {listing.entityType}
                      </span>
                    </div>
                  </div>
                  {listing.summary && (
                    <p className="mt-2 text-zinc-600 dark:text-zinc-400">{listing.summary}</p>
                  )}

                  {/* Dimensions Section - New Entity Model */}
                  {(activities.length > 0 || roles.length > 0 || placeTypes.length > 0 || access.length > 0) ? (
                    <div className="mt-4 space-y-2">
                      <h4 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Dimensions</h4>
                      <div className="grid grid-cols-1 gap-2">
                        {activities.length > 0 && (
                          <div className="text-sm">
                            <span className="text-zinc-500 dark:text-zinc-400">Activities:</span>{' '}
                            <span className="text-zinc-700 dark:text-zinc-200">
                              {activities.join(', ')}
                            </span>
                          </div>
                        )}
                        {roles.length > 0 && (
                          <div className="text-sm">
                            <span className="text-zinc-500 dark:text-zinc-400">Roles:</span>{' '}
                            <span className="text-zinc-700 dark:text-zinc-200">
                              {roles.join(', ')}
                            </span>
                          </div>
                        )}
                        {placeTypes.length > 0 && (
                          <div className="text-sm">
                            <span className="text-zinc-500 dark:text-zinc-400">Place Types:</span>{' '}
                            <span className="text-zinc-700 dark:text-zinc-200">
                              {placeTypes.join(', ')}
                            </span>
                          </div>
                        )}
                        {access.length > 0 && (
                          <div className="text-sm">
                            <span className="text-zinc-500 dark:text-zinc-400">Access:</span>{' '}
                            <span className="text-zinc-700 dark:text-zinc-200">
                              {access.join(', ')}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : null}

                  {/* Modules Section - New Entity Model */}
                  {Object.keys(modules).length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300 mb-2">Modules</h4>
                      <div className="space-y-2">
                        {Object.entries(modules).map(([moduleName, moduleData]) => (
                          <div key={moduleName} className="text-sm">
                            <span className="text-zinc-500 dark:text-zinc-400 font-medium">{moduleName}:</span>{' '}
                            <span className="text-zinc-700 dark:text-zinc-200">
                              {JSON.stringify(moduleData, null, 2)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
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