from typing import Optional, List, Dict, Any, Type
from pydantic import create_model, Field
from datetime import datetime
from .core import FieldSpec

def get_type_from_string(type_str: str) -> Type:
    """
    Safely evaluate string type annotation to actual type.
    """
    # Allowed types for evaluation
    allowed_globals = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "datetime": datetime,
        "Optional": Optional,
        "List": List,
        "Dict": Dict,
        "Any": Any,
    }
    
    try:
        return eval(type_str, allowed_globals)
    except Exception as e:
        raise ValueError(f"Could not parse type string '{type_str}': {e}")

def create_pydantic_model(model_name: str, field_specs: List[FieldSpec]):
    """
    Dynamically creates a Pydantic model from a list of FieldSpecs.
    """
    pydantic_fields = {}
    
    for spec in field_specs:
        field_type = get_type_from_string(spec.type_annotation)
        
        # Determine default value
        default_val = ... # Ellipsis means required in Pydantic
        
        if spec.default != "None":
            # Handle defaults like "default_factory=dict"
            if "default_factory=dict" in spec.default:
                default_val = Field(default_factory=dict)
            elif "default_factory=list" in spec.default:
                default_val = Field(default_factory=list)
            else:
                 # Attempt to use the default value string directly if it looks like a literal
                 # This is a simplification. 
                 pass
        elif not spec.required:
             # If not required, it implies optional/nullable with default None
             default_val = None
        
        # Override for explicit nullable=False and required=True without default
        if spec.required and default_val is None:
             default_val = ...

        pydantic_fields[spec.name] = (field_type, default_val)

    return create_model(model_name, **pydantic_fields)
