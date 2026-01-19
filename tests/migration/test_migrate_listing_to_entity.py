"""
Tests for migrate_listing_to_entity.py migration script
"""
import pytest
import sqlite3
import tempfile
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from migrate_listing_to_entity import (
    resolve_entity_class_and_roles,
    ENTITY_TYPE_MAPPING,
)


class TestEntityTypeMapping:
    """Test the entity type mapping rules."""

    def test_venue_mapping(self):
        """VENUE should map to place + provides_facility role."""
        entity_class, roles = resolve_entity_class_and_roles("VENUE", has_location=False)
        assert entity_class == "place"
        assert roles == ["provides_facility"]

    def test_retailer_mapping(self):
        """RETAILER should map to place + sells_goods role."""
        entity_class, roles = resolve_entity_class_and_roles("RETAILER", has_location=False)
        assert entity_class == "place"
        assert roles == ["sells_goods"]

    def test_coach_mapping(self):
        """COACH should map to person + provides_instruction role."""
        entity_class, roles = resolve_entity_class_and_roles("COACH", has_location=False)
        assert entity_class == "person"
        assert roles == ["provides_instruction"]

    def test_instructor_mapping(self):
        """INSTRUCTOR should map to person + provides_instruction role."""
        entity_class, roles = resolve_entity_class_and_roles("INSTRUCTOR", has_location=False)
        assert entity_class == "person"
        assert roles == ["provides_instruction"]

    def test_club_mapping_no_location(self):
        """CLUB without location should map to organization + membership_org role."""
        entity_class, roles = resolve_entity_class_and_roles("CLUB", has_location=False)
        assert entity_class == "organization"
        assert roles == ["membership_org"]

    def test_club_with_location_special_case(self):
        """CLUB with location should map to place + multiple roles (special case)."""
        entity_class, roles = resolve_entity_class_and_roles("CLUB", has_location=True)
        assert entity_class == "place"
        assert set(roles) == {"provides_facility", "membership_org"}

    def test_league_mapping(self):
        """LEAGUE should map to organization + membership_org role."""
        entity_class, roles = resolve_entity_class_and_roles("LEAGUE", has_location=False)
        assert entity_class == "organization"
        assert roles == ["membership_org"]

    def test_event_mapping(self):
        """EVENT should map to event + no roles."""
        entity_class, roles = resolve_entity_class_and_roles("EVENT", has_location=False)
        assert entity_class == "event"
        assert roles == []

    def test_tournament_mapping(self):
        """TOURNAMENT should map to event + no roles."""
        entity_class, roles = resolve_entity_class_and_roles("TOURNAMENT", has_location=False)
        assert entity_class == "event"
        assert roles == []

    def test_case_insensitive_mapping(self):
        """Entity type mapping should be case-insensitive."""
        entity_class_upper, roles_upper = resolve_entity_class_and_roles("VENUE", has_location=False)
        entity_class_lower, roles_lower = resolve_entity_class_and_roles("venue", has_location=False)
        entity_class_mixed, roles_mixed = resolve_entity_class_and_roles("Venue", has_location=False)

        assert entity_class_upper == entity_class_lower == entity_class_mixed == "place"
        assert roles_upper == roles_lower == roles_mixed == ["provides_facility"]

    def test_unknown_entity_type_defaults_to_thing(self):
        """Unknown entity types should default to 'thing' with no roles."""
        entity_class, roles = resolve_entity_class_and_roles("UNKNOWN_TYPE", has_location=False)
        assert entity_class == "thing"
        assert roles == []


class TestMigrationLogic:
    """Test the migration logic with a test database."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary test database."""
        # Create temporary database
        db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = db_file.name
        db_file.close()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create Listing table with minimal schema
        cursor.execute("""
            CREATE TABLE Listing (
                id TEXT PRIMARY KEY,
                entity_name TEXT NOT NULL,
                entityType TEXT,
                slug TEXT UNIQUE,
                latitude REAL,
                longitude REAL,
                street_address TEXT,
                canonical_activities TEXT DEFAULT '[]',
                canonical_roles TEXT DEFAULT '[]',
                canonical_place_types TEXT DEFAULT '[]',
                canonical_access TEXT DEFAULT '[]',
                summary TEXT,
                attributes TEXT,
                discovered_attributes TEXT,
                city TEXT,
                postcode TEXT,
                country TEXT,
                phone TEXT,
                email TEXT,
                website_url TEXT,
                instagram_url TEXT,
                facebook_url TEXT,
                twitter_url TEXT,
                linkedin_url TEXT,
                mainImage TEXT,
                opening_hours TEXT,
                source_info TEXT,
                field_confidence TEXT,
                createdAt TEXT,
                updatedAt TEXT,
                external_ids TEXT
            )
        """)

        conn.commit()
        yield conn, db_path
        conn.close()

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

    def test_venue_migration(self, test_db):
        """Test migration of VENUE entity."""
        conn, _ = test_db
        cursor = conn.cursor()

        # Insert test data
        cursor.execute("""
            INSERT INTO Listing (id, entity_name, entityType, slug)
            VALUES ('test1', 'Test Venue', 'VENUE', 'test-venue')
        """)
        conn.commit()

        # Apply migration logic
        from migrate_listing_to_entity import apply_schema_migration, migrate_data

        apply_schema_migration(conn)
        migrate_data(conn, dry_run=False)

        # Verify results
        cursor.execute("SELECT entity_class, canonical_roles FROM Listing WHERE id = 'test1'")
        result = cursor.fetchone()

        assert result[0] == "place"
        import json
        roles = json.loads(result[1])
        assert "provides_facility" in roles

    def test_club_without_location_migration(self, test_db):
        """Test migration of CLUB without location."""
        conn, _ = test_db
        cursor = conn.cursor()

        # Insert test data
        cursor.execute("""
            INSERT INTO Listing (id, entity_name, entityType, slug)
            VALUES ('test2', 'Test Club', 'CLUB', 'test-club')
        """)
        conn.commit()

        # Apply migration
        from migrate_listing_to_entity import apply_schema_migration, migrate_data

        apply_schema_migration(conn)
        migrate_data(conn, dry_run=False)

        # Verify results
        cursor.execute("SELECT entity_class, canonical_roles FROM Listing WHERE id = 'test2'")
        result = cursor.fetchone()

        assert result[0] == "organization"
        import json
        roles = json.loads(result[1])
        assert "membership_org" in roles

    def test_club_with_location_migration(self, test_db):
        """Test migration of CLUB with location (special case)."""
        conn, _ = test_db
        cursor = conn.cursor()

        # Insert test data with location
        cursor.execute("""
            INSERT INTO Listing (
                id, entity_name, entityType, slug,
                latitude, longitude, street_address
            )
            VALUES (
                'test3', 'Tennis Club with Courts', 'CLUB', 'tennis-club',
                55.9533, -3.1883, '123 Tennis Road'
            )
        """)
        conn.commit()

        # Apply migration
        from migrate_listing_to_entity import apply_schema_migration, migrate_data

        apply_schema_migration(conn)
        migrate_data(conn, dry_run=False)

        # Verify results
        cursor.execute("SELECT entity_class, canonical_roles FROM Listing WHERE id = 'test3'")
        result = cursor.fetchone()

        assert result[0] == "place"
        import json
        roles = json.loads(result[1])
        assert "provides_facility" in roles
        assert "membership_org" in roles

    def test_coach_migration(self, test_db):
        """Test migration of COACH entity."""
        conn, _ = test_db
        cursor = conn.cursor()

        # Insert test data
        cursor.execute("""
            INSERT INTO Listing (id, entity_name, entityType, slug)
            VALUES ('test4', 'John Coach', 'COACH', 'john-coach')
        """)
        conn.commit()

        # Apply migration
        from migrate_listing_to_entity import apply_schema_migration, migrate_data

        apply_schema_migration(conn)
        migrate_data(conn, dry_run=False)

        # Verify results
        cursor.execute("SELECT entity_class, canonical_roles FROM Listing WHERE id = 'test4'")
        result = cursor.fetchone()

        assert result[0] == "person"
        import json
        roles = json.loads(result[1])
        assert "provides_instruction" in roles

    def test_event_migration(self, test_db):
        """Test migration of EVENT entity."""
        conn, _ = test_db
        cursor = conn.cursor()

        # Insert test data
        cursor.execute("""
            INSERT INTO Listing (id, entity_name, entityType, slug)
            VALUES ('test5', 'Tournament Event', 'EVENT', 'tournament-event')
        """)
        conn.commit()

        # Apply migration
        from migrate_listing_to_entity import apply_schema_migration, migrate_data

        apply_schema_migration(conn)
        migrate_data(conn, dry_run=False)

        # Verify results
        cursor.execute("SELECT entity_class, canonical_roles FROM Listing WHERE id = 'test5'")
        result = cursor.fetchone()

        assert result[0] == "event"
        import json
        roles = json.loads(result[1])
        assert roles == []


class TestValidEntityClasses:
    """Test that all entity_class values are valid."""

    def test_all_mapped_classes_are_valid(self):
        """All entity_class values in mapping should be valid."""
        valid_classes = {"place", "person", "organization", "event", "thing"}

        for entity_type, mapping in ENTITY_TYPE_MAPPING.items():
            entity_class = mapping["entity_class"]
            assert entity_class in valid_classes, (
                f"Invalid entity_class '{entity_class}' for {entity_type}"
            )
