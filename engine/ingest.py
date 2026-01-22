import asyncio
import json
import uuid
from typing import Dict, Any, List
from prisma import Prisma
from pydantic import ValidationError

from engine.schema.entity import ENTITY_FIELDS
from engine.schema.generator import create_pydantic_model

# 1. Generate Validators
EntityModel = create_pydantic_model("EntityModel", ENTITY_FIELDS)

# 2. Define Core Columns (Mapping to Prisma Schema)
# These are fields that exist as physical columns on the Entity table.
CORE_COLUMNS = {
    "entity_name", "entity_class", "slug", "summary",
    "raw_categories", "canonical_activities", "canonical_roles",
    "canonical_place_types", "canonical_access",
    "modules", "discovered_attributes",
    "street_address", "city", "postcode", "country", "latitude", "longitude",
    "phone", "email", "website_url",
    "instagram_url", "facebook_url", "twitter_url", "linkedin_url", "mainImage",
    "opening_hours", "source_info", "field_confidence", "external_ids"
}

async def ingest_entity(data: Dict[str, Any]):
    """
    Ingests a single Entity.
    data: Flat dictionary containing all fields.
    """
    db = Prisma()
    await db.connect()

    try:
        # A. Preprocessing: Handle legacy entity_type field
        preprocessed_data = data.copy()
        if "entity_type" in preprocessed_data and "entity_class" not in preprocessed_data:
            entity_type_mapping = {
                "VENUE": "place",
                "venue": "place",
                "COACH": "person",
                "coach": "person",
                "CLUB": "organization",
                "club": "organization",
                "RETAIL": "place",
                "retail": "place",
                "EVENT": "event",
                "event": "event",
            }
            entity_type_value = preprocessed_data["entity_type"]
            preprocessed_data["entity_class"] = entity_type_mapping.get(entity_type_value, "thing")

            # Also set canonical_roles based on legacy type if not already set
            if "canonical_roles" not in preprocessed_data:
                if entity_type_value in ["VENUE", "venue"]:
                    preprocessed_data["canonical_roles"] = ["provides_facility"]
                elif entity_type_value in ["COACH", "coach"]:
                    preprocessed_data["canonical_roles"] = ["teaches", "coaches"]
                elif entity_type_value in ["CLUB", "club"]:
                    preprocessed_data["canonical_roles"] = ["organizes_activities"]
                elif entity_type_value in ["RETAIL", "retail"]:
                    preprocessed_data["canonical_roles"] = ["sells_equipment"]
                elif entity_type_value in ["EVENT", "event"]:
                    preprocessed_data["canonical_roles"] = ["hosts_event"]

        # B. Validation
        known_keys = {f.name for f in ENTITY_FIELDS}

        validation_payload = {k: v for k, v in preprocessed_data.items() if k in known_keys}

        validated_obj = EntityModel(**validation_payload)
        validated_data = validated_obj.model_dump()

        # B. Separation
        core_data = {}
        modules_data = {}

        # Extras that were NOT in known_keys
        extras = {k: v for k, v in data.items() if k not in known_keys}

        for key, value in validated_data.items():
            if key in CORE_COLUMNS:
                core_data[key] = value
            elif key == "entity_id":
                continue
            elif key in ["categories", "canonical_categories"]:
                # Map to canonical_activities
                if "canonical_activities" not in core_data and value:
                    # Assume categories are activities for now
                    core_data["canonical_activities"] = value if isinstance(value, list) else [value]
            else:
                # It's a schema-defined module field
                if value is not None:
                    modules_data[key] = value

        # C. Build modules JSON
        # Modules should be organized by domain (tennis, padel, amenities, etc.)
        # For now, put all module data in a generic "attributes" module
        if modules_data:
            core_data["modules"] = modules_data
        elif "modules" not in core_data:
            # modules is required, provide empty dict if not present
            core_data["modules"] = {}

        # Handle discovered_attributes
        # Merge explicit discovered_attributes with any extras found
        disc_attrs = core_data.get("discovered_attributes")
        if disc_attrs is None:
            disc_attrs = {}
        elif not isinstance(disc_attrs, dict):
            disc_attrs = {}

        if extras:
            disc_attrs.update(extras)

        # Only set if we have data, otherwise omit the field
        if disc_attrs:
            # Filter out None values to avoid Prisma JSON issues
            filtered_disc_attrs = {k: v for k, v in disc_attrs.items() if v is not None}
            if filtered_disc_attrs:
                # Serialize and deserialize to ensure valid JSON
                try:
                    json_str = json.dumps(filtered_disc_attrs)
                    core_data["discovered_attributes"] = json.loads(json_str)
                except (TypeError, ValueError):
                    # If serialization fails, omit the field
                    if "discovered_attributes" in core_data:
                        del core_data["discovered_attributes"]
            elif "discovered_attributes" in core_data:
                del core_data["discovered_attributes"]
        elif "discovered_attributes" in core_data:
            # Remove the field if it's None
            del core_data["discovered_attributes"]

        # Handle other JSON core columns
        for col in ["raw_categories", "canonical_activities", "canonical_roles",
                    "canonical_place_types", "canonical_access"]:
            if col in core_data and core_data[col] is not None:
                # These are arrays in PostgreSQL, keep as lists
                if not isinstance(core_data[col], list):
                    core_data[col] = [core_data[col]]

        for col in ["modules", "opening_hours", "source_info", "field_confidence",
                    "external_ids", "discovered_attributes"]:
            if col in core_data and core_data[col] is not None:
                # Keep as dict/object for JSON fields, Prisma will handle serialization
                pass

        # D. Database Upsert
        slug = core_data.get("slug")
        if not slug:
            slug = core_data.get("entity_name", "").lower().replace(" ", "-")
            core_data["slug"] = slug

        # Ensure required fields have defaults
        if "entity_class" not in core_data:
            core_data["entity_class"] = "thing"

        if "raw_categories" not in core_data:
            core_data["raw_categories"] = []

        if "canonical_activities" not in core_data:
            core_data["canonical_activities"] = []

        if "canonical_roles" not in core_data:
            core_data["canonical_roles"] = []

        if "canonical_place_types" not in core_data:
            core_data["canonical_place_types"] = []

        if "canonical_access" not in core_data:
            core_data["canonical_access"] = []

        # TEMP FIX: Skip problematic JSON fields for testing
        if "discovered_attributes" in core_data:
            del core_data["discovered_attributes"]
        if "external_ids" in core_data:
            del core_data["external_ids"]

        # Ensure required JSON fields have defaults
        if "modules" not in core_data or core_data["modules"] is None:
            core_data["modules"] = {}

        # Note: external_ids is optional, only set if present
        # Other optional JSON fields: opening_hours, source_info, field_confidence

        # Serialize JSON fields to strings for Prisma
        for json_field in ["modules", "opening_hours", "source_info", "field_confidence", "external_ids"]:
            if json_field in core_data and core_data[json_field] is not None:
                if isinstance(core_data[json_field], dict) or isinstance(core_data[json_field], list):
                    core_data[json_field] = json.dumps(core_data[json_field], separators=(',', ':'))

        # TEMP: Use create for testing
        # TODO: Switch back to upsert after testing
        try:
            entity = await db.entity.create(
                data=core_data
            )
        except Exception as e:
            # If entity exists, update it
            entity = await db.entity.update(
                where={"slug": slug},
                data=core_data
            )

        print(f"Successfully ingested: {entity.entity_name}")
        return entity

    except ValidationError as e:
        print(f"Validation Error for {data.get('entity_name')}: {e}")
        raise
    except Exception as e:
        print(f"Database Error: {e}")
        raise
    finally:
        await db.disconnect()

# Legacy function name for backward compatibility
async def ingest_venue(data: Dict[str, Any]):
    """
    DEPRECATED: Use ingest_entity instead.
    Wrapper for backward compatibility.
    """
    return await ingest_entity(data)

if __name__ == "__main__":
    pass
