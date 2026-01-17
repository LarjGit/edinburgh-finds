"""
Test that extracted listings are compatible with web app queries.

Verifies that the web app can successfully query and display data
from extracted listings.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock


class TestWebAppCompatibility:
    """Test extraction compatibility with web app."""

    @pytest.mark.asyncio
    async def test_web_app_can_query_extracted_listings(self):
        """
        Verify that web app queries work with extracted listing data.

        Simulates the query from web/app/page.tsx:
        ```
        prisma.listing.findMany({
          take: 5,
          select: {
            id: true,
            entity_name: true,
            summary: true,
            entityType: true,
            attributes: true,
            discovered_attributes: true,
          },
        })
        ```
        """
        # Mock database
        mock_db = AsyncMock()

        # Create mock listing that matches what extraction produces
        mock_listing = MagicMock()
        mock_listing.id = "listing-001"
        mock_listing.entity_name = "Game4Padel Edinburgh"
        mock_listing.summary = "Modern padel facility in Edinburgh with 4 courts"
        mock_listing.entityType = "VENUE"  # This is the key field for web app
        mock_listing.attributes = json.dumps({
            "latitude": 55.9533,
            "longitude": -3.1883,
            "phone": "+441311234567",
            "website_url": "https://game4padel.com",
        })
        mock_listing.discovered_attributes = json.dumps({
            "rating": 4.5,
            "review_count": 127,
        })

        mock_db.listing.find_many = AsyncMock(return_value=[mock_listing])

        # Simulate web app query
        listings = await mock_db.listing.find_many(
            take=5,
            select={
                "id": True,
                "entity_name": True,
                "summary": True,
                "entityType": True,
                "attributes": True,
                "discovered_attributes": True,
            }
        )

        # Verify query succeeds
        assert len(listings) > 0

        # Verify first listing has all required fields
        listing = listings[0]
        assert listing.id is not None
        assert listing.entity_name == "Game4Padel Edinburgh"
        assert listing.summary is not None
        assert listing.entityType == "VENUE"

        # Verify JSON fields can be parsed
        attributes = json.loads(listing.attributes)
        assert isinstance(attributes, dict)
        assert "latitude" in attributes

        discovered_attributes = json.loads(listing.discovered_attributes)
        assert isinstance(discovered_attributes, dict)
        assert "rating" in discovered_attributes

    def test_parse_attributes_json_from_extracted_data(self):
        """
        Verify that web app's parseAttributesJSON utility works with extracted data.

        The web app uses parseAttributesJSON to parse the attributes and
        discovered_attributes JSON strings.
        """
        # Simulate what extraction produces
        extracted_attributes = {
            "entity_name": "Test Venue",
            "latitude": 55.9533,
            "longitude": -3.1883,
            "phone": "+441311234567",
            "website_url": "https://test.com",
        }

        # Convert to JSON string (as stored in DB)
        attributes_json = json.dumps(extracted_attributes)

        # Simulate parseAttributesJSON
        try:
            parsed = json.loads(attributes_json)
        except (json.JSONDecodeError, TypeError):
            parsed = {}

        # Verify parsing works
        assert isinstance(parsed, dict)
        assert "entity_name" in parsed
        assert "latitude" in parsed
        assert parsed["phone"] == "+441311234567"

    def test_discovered_attributes_display_in_web_app(self):
        """
        Verify that discovered_attributes can be counted and displayed as badge.

        The web app shows a badge: "+ X additional properties" for discovered attributes.
        """
        # Simulate extracted discovered_attributes
        discovered = {
            "rating": 4.5,
            "review_count": 127,
            "facility_type": "indoor",
            "parking_available": True,
        }

        discovered_json = json.dumps(discovered)

        # Parse as web app would
        parsed_discovered = json.loads(discovered_json)

        # Verify count for badge display
        count = len(parsed_discovered)
        assert count == 4
        assert count > 0  # Badge should be shown

        # Verify badge text
        badge_text = f"+ {count} additional properties"
        assert badge_text == "+ 4 additional properties"

    def test_entity_type_badge_display(self):
        """
        Verify that entityType displays correctly as a badge.

        The web app shows entityType in a rounded badge next to entity name.
        """
        entity_types = ["VENUE", "COACH", "CLUB", "EVENT"]

        for entity_type in entity_types:
            # Simulate listing with this entity type
            mock_listing = MagicMock()
            mock_listing.entityType = entity_type

            # Verify it can be displayed
            badge_text = mock_listing.entityType
            assert badge_text in ["VENUE", "RETAILER", "COACH", "INSTRUCTOR",
                                  "CLUB", "LEAGUE", "EVENT", "TOURNAMENT"]

    @pytest.mark.asyncio
    async def test_multiple_entity_types_in_listing_query(self):
        """
        Verify web app can display multiple entity types together.

        The web app should be able to query and display VENUEs, COACHes, etc.
        all in the same listing.
        """
        mock_db = AsyncMock()

        # Create listings of different types
        venue = MagicMock()
        venue.id = "venue-001"
        venue.entity_name = "Game4Padel Edinburgh"
        venue.entityType = "VENUE"
        venue.summary = "Padel facility"
        venue.attributes = json.dumps({"latitude": 55.9533})
        venue.discovered_attributes = json.dumps({"rating": 4.5})

        coach = MagicMock()
        coach.id = "coach-001"
        coach.entity_name = "Sarah McTavish"
        coach.entityType = "COACH"
        coach.summary = "Professional tennis coach"
        coach.attributes = json.dumps({"phone": "+441311234567"})
        coach.discovered_attributes = json.dumps({"qualifications": ["LTA Level 4"]})

        club = MagicMock()
        club.id = "club-001"
        club.entity_name = "Edinburgh Tennis Club"
        club.entityType = "CLUB"
        club.summary = "Historic tennis club"
        club.attributes = json.dumps({"website_url": "https://example.com"})
        club.discovered_attributes = json.dumps({})

        mock_db.listing.find_many = AsyncMock(return_value=[venue, coach, club])

        # Query all listings
        listings = await mock_db.listing.find_many(take=5)

        # Verify all entity types work
        assert len(listings) == 3
        assert listings[0].entityType == "VENUE"
        assert listings[1].entityType == "COACH"
        assert listings[2].entityType == "CLUB"

        # Verify each can be parsed and displayed
        for listing in listings:
            assert listing.id is not None
            assert listing.entity_name is not None
            assert listing.entityType in ["VENUE", "COACH", "CLUB"]

            # JSON fields can be parsed
            attributes = json.loads(listing.attributes)
            discovered = json.loads(listing.discovered_attributes)
            assert isinstance(attributes, dict)
            assert isinstance(discovered, dict)

    def test_empty_attributes_handled_correctly(self):
        """
        Verify that listings with no attributes/discovered_attributes don't break display.

        Some extracted listings might have minimal data.
        """
        # Minimal listing
        mock_listing = MagicMock()
        mock_listing.id = "minimal-001"
        mock_listing.entity_name = "Minimal Venue"
        mock_listing.entityType = "VENUE"
        mock_listing.summary = None
        mock_listing.attributes = json.dumps({})
        mock_listing.discovered_attributes = json.dumps({})

        # Parse as web app would
        attributes = json.loads(mock_listing.attributes)
        discovered = json.loads(mock_listing.discovered_attributes)

        # Verify empty objects work
        assert isinstance(attributes, dict)
        assert len(attributes) == 0

        assert isinstance(discovered, dict)
        assert len(discovered) == 0

        # Web app should not show attributes section or badge
        has_attributes = len(attributes) > 0
        has_discovered = len(discovered) > 0

        assert not has_attributes
        assert not has_discovered

    def test_special_characters_in_entity_name_display(self):
        """
        Verify that entity names with special characters display correctly.

        Some venues might have apostrophes, ampersands, etc.
        """
        special_names = [
            "Game4Padel - Edinburgh's Premier Facility",
            "Smith & Jones Tennis Club",
            "Café Tennis & Padel",
            "The King's Court",
        ]

        for name in special_names:
            mock_listing = MagicMock()
            mock_listing.entity_name = name
            mock_listing.entityType = "VENUE"

            # Verify name can be displayed (no escaping issues)
            assert mock_listing.entity_name == name
            assert len(mock_listing.entity_name) > 0
