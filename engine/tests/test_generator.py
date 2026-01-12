import unittest
from engine.schema.core import FieldSpec
from engine.schema.generator import create_pydantic_model
from pydantic import ValidationError

class TestGenerator(unittest.TestCase):
    def test_simple_model_generation(self):
        fields = [
            FieldSpec(name="name", type_annotation="str", description="Name", required=True, nullable=False),
            FieldSpec(name="age", type_annotation="Optional[int]", description="Age", required=False)
        ]
        
        PersonModel = create_pydantic_model("Person", fields)
        
        # Valid input
        p = PersonModel(name="Alice", age=30)
        self.assertEqual(p.name, "Alice")
        self.assertEqual(p.age, 30)
        
        # Valid input with missing optional
        p2 = PersonModel(name="Bob")
        self.assertEqual(p2.name, "Bob")
        self.assertIsNone(p2.age)
        
        # Invalid input (missing required)
        with self.assertRaises(ValidationError):
            PersonModel(age=25)
            
        # Invalid input (wrong type)
        with self.assertRaises(ValidationError):
            PersonModel(name="Charlie", age="not-an-int")

if __name__ == "__main__":
    unittest.main()
