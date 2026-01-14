import unittest
from engine.schema.listing import LISTING_FIELDS
from engine.schema.generator import create_pydantic_model
from pydantic import ValidationError

class TestEntityTypeEnum(unittest.TestCase):
    def test_entity_type_is_enum(self):
        """Test that entity_type only accepts specific Enum values."""
        ListingModel = create_pydantic_model("TestListing", LISTING_FIELDS)
        
        valid_types = [
            "VENUE", "RETAILER", "COACH", "INSTRUCTOR", 
            "CLUB", "LEAGUE", "EVENT", "TOURNAMENT"
        ]
        
        # Test valid types
        for t in valid_types:
            # We need to provide required fields. 
            # entity_name is required. 
            # entity_type is required.
            model = ListingModel(entity_name="Test", entity_type=t)
            self.assertEqual(model.entity_type, t)
            
        # Test invalid type - this should raise ValidationError when Enum is implemented
        invalid_type = "INVALID_TYPE"
        
        with self.assertRaises(ValidationError, msg="entity_type should restrict values to Enum"):
            ListingModel(entity_name="Test", entity_type=invalid_type)
