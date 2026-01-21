import asyncio
import json
import uuid
from typing import Dict, Any, List
from prisma import Prisma
from pydantic import ValidationError

from engine.schema.venue import VENUE_FIELDS
from engine.schema.entity import ENTITY_FIELDS
from engine.schema.generator import create_pydantic_model

# 1. Generate Validators
VenueModel = create_pydantic_model("VenueModel", VENUE_FIELDS)

# 2. Define Core Columns (Mapping to Prisma Schema)
# These are fields that exist as physical columns on the Listing table.
CORE_COLUMNS = {
    "entity_name", "slug", "summary", 
    "street_address", "city", "postcode", "country", "latitude", "longitude",
    "phone", "email", "website_url",
    "instagram_url", "facebook_url", "twitter_url", "linkedin_url", "mainImage",
    "opening_hours", "source_info", "field_confidence", "external_ids",
    "discovered_attributes"
}

async def ingest_venue(data: Dict[str, Any]):
    """
    Ingests a single Venue entity.
    data: Flat dictionary containing all fields.
    """
    db = Prisma()
    await db.connect()

    try:
        # A. Validation
        known_keys = {f.name for f in VENUE_FIELDS}
        # Add common fields if not in venue (they are inherited so should be there)
        
        validation_payload = {k: v for k, v in data.items() if k in known_keys}
        
        validated_obj = VenueModel(**validation_payload)
        validated_data = validated_obj.model_dump()
        
        # B. Separation
        core_data = {}
        attributes_data = {}
        
        # Extras that were NOT in known_keys
        extras = {k: v for k, v in data.items() if k not in known_keys}

        for key, value in validated_data.items():
            if key in CORE_COLUMNS:
                core_data[key] = value
            elif key == "entity_id":
                continue
            elif key == "entity_type":
                # Store EntityType Enum value for Prisma
                # Convert Enum to its value (e.g., EntityType.VENUE -> "VENUE")
                core_data["entityType"] = value.value if hasattr(value, 'value') else value
            elif key in ["categories", "canonical_categories"]:
                continue # Handled via relations
            else:
                # It's a schema-defined attribute (e.g. tennis_courts)
                if value is not None:
                    attributes_data[key] = value

        # C. Serialization
        core_data["attributes"] = json.dumps(attributes_data)
        
        # Handle discovered_attributes
        # Merge explicit discovered_attributes with any extras found
        disc_attrs = core_data.get("discovered_attributes") or {}
        if extras:
            if not isinstance(disc_attrs, dict):
                disc_attrs = {}
            disc_attrs.update(extras)
            core_data["discovered_attributes"] = disc_attrs
        
        # Handle other JSON core columns
        for col in ["opening_hours", "source_info", "field_confidence", "external_ids", "discovered_attributes"]:
            if col in core_data and core_data[col] is not None:
                if not isinstance(core_data[col], str):
                    core_data[col] = json.dumps(core_data[col])

        # D. Database Upsert
        slug = core_data.get("slug")
        if not slug:
             slug = core_data.get("entity_name", "").lower().replace(" ", "-")
             core_data["slug"] = slug

        # Categories Relation
        # Input 'canonical_categories' is List[str] e.g. ["Padel", "Football"]
        category_connect = []
        cats = data.get("canonical_categories", [])
        if cats:
            for cat_name in cats:
                cat_slug = cat_name.lower().replace(" ", "-")
                # Find or create category
                # Prisma atomic upsert for relation is tricky inside nested create, 
                # best to resolve IDs first or use connect_or_create
                category_connect.append({
                    "where": {"slug": cat_slug},
                    "create": {"name": cat_name, "slug": cat_slug}
                })

        # Upsert Listing
        # Note: 'categories': {'connect_or_create': [...]}
        upsert_data = {
            **core_data,
            "categories": {
                "connectOrCreate": category_connect
            }
        }

        listing = await db.listing.upsert(
            where={"slug": slug},
            data={
                "create": upsert_data,
                "update": upsert_data
            }
        )
        
        print(f"Successfully ingested: {listing.entity_name}")
        return listing

    except ValidationError as e:
        print(f"Validation Error for {data.get('entity_name')}: {e}")
        raise
    except Exception as e:
        print(f"Database Error: {e}")
        raise
    finally:
        await db.disconnect()

if __name__ == "__main__":
    pass
