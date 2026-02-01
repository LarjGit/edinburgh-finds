"""
Tests for OpenChargeMap Extractor

Validates compliance with:
- system-vision.md Invariant 1 (Engine Purity)
- architecture.md Section 4.2 (Extraction Boundary Contract)
"""

import inspect
import pytest
from engine.extraction.extractors.open_charge_map_extractor import OpenChargeMapExtractor


class TestEnginePurity:
    """Validates system-vision.md Invariant 1: Engine Purity"""

    def test_extractor_contains_no_domain_literals(self):
        """
        Validates: system-vision.md Invariant 1 (Engine Purity)

        The engine must contain zero domain knowledge. No domain-specific
        terms may exist in engine code.

        Forbidden terms: tennis, padel, wine, restaurant (and variations)
        """
        source = inspect.getsource(OpenChargeMapExtractor)

        # Forbidden domain-specific terms
        forbidden = ["tennis", "padel", "wine", "restaurant"]

        violations = []
        for term in forbidden:
            if term.lower() in source.lower():
                violations.append(term)

        assert not violations, (
            f"Engine Purity violation (system-vision.md Invariant 1): "
            f"Found forbidden domain terms in extractor: {violations}. "
            f"Engine code must contain zero domain knowledge."
        )


class TestExtractionBoundary:
    """Validates architecture.md Section 4.2: Extraction Boundary Contract"""

    def test_extractor_outputs_only_primitives_and_raw_observations(self, mock_ctx):
        """
        Validates: architecture.md Section 4.2 (Extraction Boundary)

        Phase 1 extractors must output ONLY:
        - Schema primitives (entity_name, latitude, longitude, etc.)
        - Raw observations (discovered_attributes, connector-native fields)

        FORBIDDEN outputs:
        - canonical_* dimensions
        - modules or module fields
        - domain-specific interpreted fields
        """
        extractor = OpenChargeMapExtractor()

        # Mock OpenChargeMap API response
        raw_data = {
            "UUID": "test-uuid-12345",
            "AddressInfo": {
                "Title": "Test Charging Station",
                "AddressLine1": "123 Test Street",
                "Town": "Edinburgh",
                "Postcode": "EH1 1AA",
                "Latitude": 55.9533,
                "Longitude": -3.1883,
                "AccessComments": "Public access"
            },
            "OperatorInfo": {
                "Title": "Test Operator",
                "PhonePrimaryContact": "0131 234 5678"
            },
            "UsageType": {
                "Title": "Public"
            },
            "UsageCost": "Free",
            "StatusType": {
                "IsOperational": True
            },
            "NumberOfPoints": 4,
            "Connections": [
                {
                    "ConnectionType": {"Title": "Type 2"},
                    "PowerKW": 22,
                    "Quantity": 2
                }
            ]
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)

        # Forbidden: canonical_* dimensions
        canonical_fields = [
            "canonical_activities", "canonical_roles",
            "canonical_place_types", "canonical_access"
        ]

        violations = []
        for field in canonical_fields:
            if field in extracted:
                violations.append(field)

        assert not violations, (
            f"Extraction Boundary violation (architecture.md 4.2): "
            f"Extractor emitted forbidden canonical dimensions: {violations}. "
            f"Phase 1 extractors must output ONLY schema primitives + raw observations. "
            f"Canonical dimensions belong in Phase 2 (Lens Application)."
        )

        # Forbidden: modules field
        assert "modules" not in extracted, (
            "Extraction Boundary violation: 'modules' field belongs in Phase 2 "
            "(Lens Application), not Phase 1 extraction."
        )

        # Forbidden: Domain-specific interpreted fields
        forbidden_prefixes = ["tennis_", "padel_", "wine_", "restaurant_", "ev_charging_"]
        domain_violations = []

        for key in extracted.keys():
            for prefix in forbidden_prefixes:
                if key.startswith(prefix):
                    domain_violations.append(key)

        assert not domain_violations, (
            f"Extraction Boundary violation (architecture.md 4.2): "
            f"Extractor emitted forbidden domain-specific fields: {domain_violations}. "
            f"Phase 1 extractors must output ONLY schema primitives + raw observations. "
            f"Domain interpretation belongs in Phase 2 (Lens Application)."
        )

    def test_split_attributes_separates_schema_and_discovered(self, mock_ctx):
        """
        Validates split_attributes() correctly separates schema-defined fields
        from discovered attributes per architecture.md 4.2
        """
        extractor = OpenChargeMapExtractor()

        # Mock data with both schema fields and EV-specific fields
        raw_data = {
            "UUID": "test-uuid",
            "AddressInfo": {
                "Title": "Test Station",
                "AddressLine1": "123 Test St",
                "Latitude": 55.9533,
                "Longitude": -3.1883,
                "AccessComments": "Public access"
            },
            "OperatorInfo": {
                "Title": "Test Operator"
            },
            "NumberOfPoints": 2
        }

        extracted = extractor.extract(raw_data, ctx=mock_ctx)
        attributes, discovered = extractor.split_attributes(extracted)

        # Schema primitives should be in attributes
        schema_fields = ["entity_name", "street_address", "latitude", "longitude"]
        for field in schema_fields:
            if field in extracted:
                assert field in attributes, f"Schema field '{field}' should be in attributes"
                assert field not in discovered, f"Schema field '{field}' should NOT be in discovered"

        # EV-specific fields should be in discovered (including external_id)
        ev_fields = ["operator_name", "number_of_points", "access_comments", "external_id"]
        for field in ev_fields:
            if field in extracted:
                assert field in discovered, f"EV-specific field '{field}' should be in discovered"
                assert field not in attributes, f"EV-specific field '{field}' should NOT be in attributes"


class TestExtractionCorrectness:
    """Validates extractor correctly extracts primitives and raw observations"""

    @pytest.fixture
    def sample_opencharge_response(self):
        """Sample OpenChargeMap API response for testing"""
        return {
            "ID": 12345,
            "UUID": "abc-def-123",
            "AddressInfo": {
                "ID": 67890,
                "Title": "Edinburgh Charging Hub",
                "AddressLine1": "45 Holyrood Road",
                "AddressLine2": "Suite 100",
                "Town": "Edinburgh",
                "StateOrProvince": "Scotland",
                "Postcode": "EH8 8AS",
                "Country": {
                    "Title": "United Kingdom"
                },
                "Latitude": 55.9521,
                "Longitude": -3.1725,
                "AccessComments": "24/7 public access in parking lot"
            },
            "OperatorInfo": {
                "Title": "ChargePoint Network",
                "PhonePrimaryContact": "0131 555 0123"
            },
            "UsageType": {
                "Title": "Public"
            },
            "UsageCost": "£0.30/kWh",
            "StatusType": {
                "IsOperational": True
            },
            "NumberOfPoints": 6,
            "Connections": [
                {
                    "ID": 1,
                    "ConnectionType": {
                        "Title": "Type 2 (Socket Only)"
                    },
                    "PowerKW": 22,
                    "Quantity": 4,
                    "Level": {
                        "Title": "Level 2"
                    },
                    "CurrentType": {
                        "Title": "AC"
                    },
                    "Voltage": 230,
                    "Amps": 32
                },
                {
                    "ID": 2,
                    "ConnectionType": {
                        "Title": "CCS (Type 2)"
                    },
                    "PowerKW": 50,
                    "Quantity": 2,
                    "Level": {
                        "Title": "DC Fast"
                    },
                    "CurrentType": {
                        "Title": "DC"
                    }
                }
            ],
            "GeneralComments": "Modern charging facility with amenities"
        }

    def test_extract_schema_primitives(self, sample_opencharge_response, mock_ctx):
        """
        Validates extractor outputs schema primitives correctly

        Schema primitives: entity_name, street_address, latitude, longitude,
        postcode, phone, external_id
        """
        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(sample_opencharge_response, ctx=mock_ctx)

        # Verify schema primitives extracted
        assert extracted["entity_name"] == "Edinburgh Charging Hub"
        assert extracted["street_address"] == "45 Holyrood Road, Suite 100, Edinburgh, Scotland"
        assert extracted["latitude"] == 55.9521
        assert extracted["longitude"] == -3.1725
        assert extracted["postcode"] == "EH8 8AS"
        assert extracted["phone"] == "+441315550123"  # Formatted to E.164
        assert extracted["external_id"] == "abc-def-123"

    def test_extract_ev_specific_fields_to_discovered(self, sample_opencharge_response, mock_ctx):
        """
        Validates EV-specific fields are extracted as discovered attributes
        (raw observations for Phase 2 interpretation)
        """
        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(sample_opencharge_response, ctx=mock_ctx)

        # EV-specific fields (will be in discovered_attributes after split)
        assert extracted["operator_name"] == "ChargePoint Network"
        assert extracted["usage_type"] == "Public"
        assert extracted["usage_cost"] == "£0.30/kWh"
        assert extracted["is_operational"] is True
        assert extracted["number_of_points"] == 6
        assert extracted["access_comments"] == "24/7 public access in parking lot"
        assert extracted["general_comments"] == "Modern charging facility with amenities"

    def test_extract_connections_details(self, sample_opencharge_response, mock_ctx):
        """
        Validates _extract_connections() helper correctly extracts
        charging connection details
        """
        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(sample_opencharge_response, ctx=mock_ctx)

        # Verify connections extracted
        assert "connections" in extracted
        connections = extracted["connections"]
        assert len(connections) == 2

        # First connection (Type 2, 22kW)
        conn1 = connections[0]
        assert conn1["type"] == "Type 2 (Socket Only)"
        assert conn1["power_kw"] == 22
        assert conn1["quantity"] == 4
        assert conn1["level"] == "Level 2"
        assert conn1["current_type"] == "AC"
        assert conn1["voltage"] == 230
        assert conn1["amps"] == 32

        # Second connection (CCS, 50kW DC Fast)
        conn2 = connections[1]
        assert conn2["type"] == "CCS (Type 2)"
        assert conn2["power_kw"] == 50
        assert conn2["quantity"] == 2
        assert conn2["level"] == "DC Fast"
        assert conn2["current_type"] == "DC"
        # Voltage/Amps not present in this connection (should not be in output)
        assert "voltage" not in conn2
        assert "amps" not in conn2

    def test_extract_handles_missing_fields_gracefully(self, mock_ctx):
        """
        Validates extractor handles incomplete data without crashing
        (real-world API responses may have missing fields)
        """
        extractor = OpenChargeMapExtractor()

        # Minimal data (only required fields)
        minimal_data = {
            "AddressInfo": {
                "Title": "Minimal Station"
            }
        }

        extracted = extractor.extract(minimal_data, ctx=mock_ctx)

        # Should extract entity_name, no crash
        assert extracted["entity_name"] == "Minimal Station"

        # Optional fields should be absent (not None or empty string)
        assert "street_address" not in extracted or extracted["street_address"] == ""
        assert "latitude" not in extracted
        assert "longitude" not in extracted
        assert "phone" not in extracted

    def test_validate_requires_entity_name(self, mock_ctx):
        """
        Validates validate() enforces required fields (entity_name)
        per schema contract
        """
        extractor = OpenChargeMapExtractor()

        # Missing entity_name
        invalid_extracted = {
            "latitude": 55.9533,
            "longitude": -3.1883
        }

        with pytest.raises(ValueError, match="Missing required field: entity_name"):
            extractor.validate(invalid_extracted)

    def test_validate_formats_phone_to_e164(self, mock_ctx):
        """
        Validates validate() ensures phone numbers are in E.164 format
        """
        extractor = OpenChargeMapExtractor()

        # Phone without + prefix (should be reformatted)
        extracted = {
            "entity_name": "Test Station",
            "phone": "0131 234 5678"  # Not E.164
        }

        validated = extractor.validate(extracted)

        # Should be reformatted to E.164
        assert validated["phone"] == "+441312345678"

    def test_validate_removes_invalid_coordinates(self, mock_ctx):
        """
        Validates validate() removes out-of-range coordinates
        """
        extractor = OpenChargeMapExtractor()

        # Invalid latitude (>90)
        extracted = {
            "entity_name": "Test Station",
            "latitude": 95.0,  # Invalid
            "longitude": -3.1883
        }

        validated = extractor.validate(extracted)

        # Invalid latitude should be removed
        assert "latitude" not in validated
        assert "longitude" in validated  # Valid longitude kept

    def test_format_postcode_uk(self, sample_opencharge_response, mock_ctx):
        """
        Validates UK postcode formatting (uses format_postcode_uk helper)
        """
        extractor = OpenChargeMapExtractor()
        extracted = extractor.extract(sample_opencharge_response, ctx=mock_ctx)

        # Postcode should be formatted correctly
        assert extracted["postcode"] == "EH8 8AS"

    def test_connections_empty_list_handled(self, mock_ctx):
        """
        Validates extractor handles empty Connections array
        """
        extractor = OpenChargeMapExtractor()

        data = {
            "AddressInfo": {
                "Title": "Station with No Connections"
            },
            "Connections": []  # Empty list
        }

        extracted = extractor.extract(data, ctx=mock_ctx)

        # Should include connections field even if empty
        assert "connections" in extracted
        assert extracted["connections"] == []
