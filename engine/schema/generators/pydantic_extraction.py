"""
Pydantic Extraction Generator.

Generates Pydantic extraction models from YAML schema definitions.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from engine.schema.parser import FieldDefinition, SchemaDefinition, SchemaParser


@dataclass(frozen=True)
class ExtractionField:
    """Definition for extraction-only fields."""
    name: str
    type: str
    description: str
    nullable: bool = True
    required: bool = False
    python: Optional[Dict[str, Any]] = None


class PydanticExtractionGenerator:
    """
    Generates Pydantic extraction models from YAML SchemaDefinition.

    Fields are optional by default to support null semantics for LLMs.
    Use python.extraction_required in YAML to enforce required extraction fields.
    """

    TYPE_MAP = {
        "string": "str",
        "integer": "int",
        "float": "float",
        "boolean": "bool",
        "datetime": "datetime",
        "json": "Dict[str, Any]",
        "list[string]": "List[str]",
        "list[integer]": "List[int]",
        "list[float]": "List[float]",
        "list[boolean]": "List[bool]",
    }

    def generate_from_yaml(self, yaml_file: Path) -> str:
        """
        Generate extraction model from a YAML schema file.

        Args:
            yaml_file: Path to YAML schema file.

        Returns:
            Generated Python code as a string.
        """
        yaml_data = self._load_yaml(yaml_file)
        parser = SchemaParser()
        schema = parser.parse(yaml_file)
        extraction_fields = self._parse_extraction_fields(yaml_data)
        return self.generate(schema, yaml_file.name, extraction_fields)

    def generate(
        self,
        schema: SchemaDefinition,
        source_file: str,
        extraction_fields: Optional[List[ExtractionField]] = None,
    ) -> str:
        """
        Generate extraction model code from schema.

        Args:
            schema: Parsed SchemaDefinition.
            source_file: Source YAML filename.
            extraction_fields: Optional list of extraction-only fields.

        Returns:
            Generated Python module as a string.
        """
        from datetime import datetime

        extraction_fields = extraction_fields or []
        fields = self._collect_fields(schema, extraction_fields)
        type_annotations = [self._get_type_annotation(field) for field in fields]
        validator_specs = self._collect_validator_specs(fields)

        lines: List[str] = []
        lines.append("# " + "=" * 60)
        lines.append("# GENERATED FILE - DO NOT EDIT")
        lines.append("# " + "=" * 60)
        lines.append("#")
        lines.append(f"# Generated from: engine/config/schemas/{source_file}")
        lines.append(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("#")
        lines.append("# To make changes:")
        lines.append(f"# 1. Edit engine/config/schemas/{source_file}")
        lines.append("# 2. Run: python -m engine.schema.generate")
        lines.append("#")
        lines.append("# " + "=" * 60)
        lines.append("")

        lines.extend(self._generate_imports(type_annotations, validator_specs))
        lines.append("")

        lines.append("class EntityExtraction(BaseModel):")
        lines.append(self._build_class_docstring(schema.description))
        lines.append("")

        for field in fields:
            lines.append(self._generate_field(field))
            lines.append("")

        if validator_specs:
            lines.extend(self._generate_validators(validator_specs))
            lines.append("")

        lines.append(self._build_config_block(fields))
        lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _collect_fields(
        self,
        schema: SchemaDefinition,
        extraction_fields: List[ExtractionField],
    ) -> List[FieldDefinition]:
        """
        Collect base and extraction-only fields, applying overrides.

        Args:
            schema: Parsed schema definition.
            extraction_fields: Additional extraction-only fields.

        Returns:
            Ordered list of FieldDefinition objects.
        """
        collected: Dict[str, FieldDefinition] = {}

        for field in schema.fields:
            if field.exclude:
                continue
            extraction_name = self._get_extraction_name(field)
            if extraction_name in collected:
                continue
            collected[extraction_name] = FieldDefinition(
                name=extraction_name,
                type=field.type,
                description=field.description,
                nullable=field.nullable,
                required=field.required,
                index=field.index,
                unique=field.unique,
                default=field.default,
                exclude=field.exclude,
                primary_key=field.primary_key,
                foreign_key=field.foreign_key,
                search_category=field.search_category,
                search_keywords=field.search_keywords,
                python=field.python,
                prisma=field.prisma,
            )

        for field in extraction_fields:
            collected[field.name] = FieldDefinition(
                name=field.name,
                type=field.type,
                description=field.description,
                nullable=field.nullable,
                required=field.required,
                python=field.python,
            )

        return list(collected.values())

    def _generate_imports(
        self,
        type_annotations: List[str],
        validator_specs: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Generate import statements based on type annotations.

        Args:
            type_annotations: List of type annotation strings.

        Returns:
            List of import lines.
        """
        typing_imports = {"Optional"}
        needs_datetime = False

        for annotation in type_annotations:
            if "List[" in annotation:
                typing_imports.add("List")
            if "Dict[" in annotation:
                typing_imports.add("Dict")
            if "Any" in annotation:
                typing_imports.add("Any")
            if "datetime" in annotation:
                needs_datetime = True

        lines = ["from typing import " + ", ".join(sorted(typing_imports))]
        if needs_datetime:
            lines.append("from datetime import datetime")
        if validator_specs:
            lines.append("from pydantic import BaseModel, Field, field_validator")
        else:
            lines.append("from pydantic import BaseModel, Field")

        return lines

    def _get_type_annotation(self, field: FieldDefinition) -> str:
        """
        Get Pydantic type annotation for a field.

        Args:
            field: Field definition.

        Returns:
            Type annotation string.
        """
        override = None
        if field.python:
            override = field.python.get("extraction_type_annotation")

        base_type = override or self._map_type(field)

        if self._is_extraction_required(field):
            return self._strip_optional(base_type)

        if base_type.startswith("Optional["):
            return base_type
        return f"Optional[{base_type}]"

    def _map_type(self, field: FieldDefinition) -> str:
        """
        Map YAML type to base Python type.

        Args:
            field: Field definition.

        Returns:
            Base type annotation string.

        Raises:
            ValueError: If field type is unsupported.
        """
        if field.type not in self.TYPE_MAP:
            raise ValueError(
                f"Unsupported type '{field.type}'. "
                f"Supported types: {', '.join(sorted(self.TYPE_MAP.keys()))}"
            )
        return self.TYPE_MAP[field.type]

    def _generate_field(self, field: FieldDefinition) -> str:
        """
        Generate a single field line for the Pydantic model.

        Args:
            field: Field definition.

        Returns:
            Field definition line as a string.
        """
        field_type = self._get_type_annotation(field)
        description = self._build_description(field)
        escaped_description = self._escape_description(description)
        if self._is_extraction_required(field):
            return (
                f"    {field.name}: {field_type} = "
                f'Field(description="{escaped_description}")'
            )
        return (
            f"    {field.name}: {field_type} = "
            f'Field(default=None, description="{escaped_description}")'
        )

    def _build_description(self, field: FieldDefinition) -> str:
        """
        Build field description with null semantics guidance.

        Args:
            field: Field definition.

        Returns:
            Description string.
        """
        description = (field.description or "").strip()
        description = description.replace("\n", " ").strip()
        lower = description.lower()

        if self._is_extraction_required(field) and "required" not in lower:
            if description:
                description = f"{description} REQUIRED."
            else:
                description = "REQUIRED."

        if self._is_extraction_required(field):
            return description

        if "null" not in description.lower():
            if field.type == "boolean":
                description = f"{description} Null means unknown.".strip()
            else:
                description = f"{description} Null if not found.".strip()

        return description

    def _is_extraction_required(self, field: FieldDefinition) -> bool:
        """
        Determine if a field is required in extraction output.

        Defaults to optional unless explicitly marked in YAML metadata.
        """
        if not field.python:
            return False
        if "extraction_required" not in field.python:
            return False
        return bool(field.python["extraction_required"])

    def _strip_optional(self, annotation: str) -> str:
        """
        Strip Optional[...] wrapper from a type annotation if present.
        """
        if annotation.startswith("Optional[") and annotation.endswith("]"):
            return annotation[len("Optional["):-1]
        return annotation

    def _escape_description(self, description: str) -> str:
        """Escape description for use in a double-quoted string."""
        return description.replace("\\", "\\\\").replace('"', '\\"')

    def _get_extraction_name(self, field: FieldDefinition) -> str:
        """
        Resolve extraction field name override.

        Args:
            field: Field definition.

        Returns:
            Extraction field name.
        """
        if field.python and "extraction_name" in field.python:
            return field.python["extraction_name"]
        return field.name

    def _build_class_docstring(self, schema_description: str) -> str:
        """
        Build class docstring for extraction model.

        Args:
            schema_description: Schema description string.

        Returns:
            Formatted docstring line.
        """
        description = schema_description.strip()
        return f'    """Extraction model for {description}."""'

    def _build_config_block(self, fields: List[FieldDefinition]) -> str:
        """
        Build a Config block with a minimal example.

        Args:
            fields: List of fields in the model.

        Returns:
            Config block as a string.
        """
        example_field = next(
            (field for field in fields if field.name == "entity_name"), None
        )
        if example_field is None and fields:
            example_field = fields[0]

        example_name = example_field.name if example_field else "entity_name"

        lines = [
            "    class Config:",
            '        """Pydantic model configuration"""',
            "        json_schema_extra = {",
            '            "example": {',
            f'                "{example_name}": "Example"',
            "            }",
            "        }",
        ]

        return "\n".join(lines)

    def _collect_validator_specs(
        self, fields: List[FieldDefinition]
    ) -> List[Dict[str, Any]]:
        """
        Collect validator specifications from field metadata.

        Args:
            fields: List of fields in the model.

        Returns:
            List of validator spec dictionaries.
        """
        specs: List[Dict[str, Any]] = []
        for field in fields:
            validators = self._get_field_validators(field)
            for validator in validators:
                specs.append({"field": field, "validator": validator})
        return specs

    def _get_field_validators(self, field: FieldDefinition) -> List[str]:
        """
        Read validators list from field metadata.

        Args:
            field: Field definition.

        Returns:
            List of validator names.
        """
        if not field.python or "validators" not in field.python:
            return []
        validators = field.python["validators"]
        if isinstance(validators, str):
            return [validators]
        if isinstance(validators, list):
            return [str(v) for v in validators]
        return []

    def _generate_validators(self, specs: List[Dict[str, Any]]) -> List[str]:
        """
        Generate validator methods from specs.

        Args:
            specs: List of validator spec dictionaries.

        Returns:
            List of validator lines.
        """
        lines: List[str] = []
        for spec in specs:
            field = spec["field"]
            validator_name = spec["validator"]
            lines.extend(self._render_validator(field, validator_name))
            lines.append("")
        if lines:
            lines.pop()
        return lines

    def _render_validator(
        self, field: FieldDefinition, validator_name: str
    ) -> List[str]:
        """
        Render a validator method for a field.

        Args:
            field: Field definition.
            validator_name: Validator identifier.

        Returns:
            List of validator method lines.
        """
        if validator_name == "non_empty":
            return self._render_non_empty_validator(field)
        if validator_name == "e164_phone":
            return self._render_e164_phone_validator(field)
        if validator_name == "url_http":
            return self._render_url_http_validator(field)
        if validator_name == "postcode_uk":
            return self._render_postcode_validator(field)

        raise ValueError(f"Unsupported validator '{validator_name}'")

    def _render_non_empty_validator(self, field: FieldDefinition) -> List[str]:
        method_name = f"validate_{field.name}_not_empty"
        value_type = "str" if self._is_extraction_required(field) else "Optional[str]"
        return [
            f'    @field_validator("{field.name}")',
            "    @classmethod",
            f"    def {method_name}(cls, v: {value_type}) -> {value_type}:",
            f'        """Ensure {field.name} is not empty or just whitespace"""',
            *([] if self._is_extraction_required(field) else [
                "        if v is None:",
                "            return None",
            ]),
            "        if not v.strip():",
            f'            raise ValueError("{field.name} cannot be empty")',
            "        return v.strip()",
        ]

    def _render_e164_phone_validator(self, field: FieldDefinition) -> List[str]:
        method_name = f"validate_{field.name}_e164_format"
        return [
            f'    @field_validator("{field.name}")',
            "    @classmethod",
            f"    def {method_name}(cls, v: Optional[str]) -> Optional[str]:",
            '        """Ensure phone is in E.164 format if provided"""',
            "        if v is None:",
            "            return None",
            "        if not v.startswith('+'):",
            '            raise ValueError("Phone number must be in E.164 format (starting with +)")',
            "        if ' ' in v or '-' in v:",
            '            raise ValueError("Phone number must not contain spaces or dashes in E.164 format")',
            "        return v",
        ]

    def _render_url_http_validator(self, field: FieldDefinition) -> List[str]:
        method_name = f"validate_{field.name}_url"
        label = field.name.replace("_", " ").title()
        return [
            f'    @field_validator("{field.name}")',
            "    @classmethod",
            f"    def {method_name}(cls, v: Optional[str]) -> Optional[str]:",
            f'        """Ensure {field.name} is a valid URL if provided"""',
            "        if v is None:",
            "            return None",
            "        if not v.startswith(('http://', 'https://')):",
            f'            raise ValueError("{label} must be a valid URL starting with http:// or https://")',
            "        return v",
        ]

    def _render_postcode_validator(self, field: FieldDefinition) -> List[str]:
        method_name = f"validate_{field.name}_format"
        return [
            f'    @field_validator("{field.name}")',
            "    @classmethod",
            f"    def {method_name}(cls, v: Optional[str]) -> Optional[str]:",
            '        """Ensure postcode follows UK format if provided"""',
            "        if v is None:",
            "            return None",
            "        if ' ' not in v:",
            "            raise ValueError(\"UK postcode should contain a space (e.g., 'EH12 9GR')\")",
            "        if v != v.upper():",
            '            raise ValueError("Postcode should be uppercase")',
            "        return v",
        ]

    def _load_yaml(self, yaml_file: Path) -> Dict[str, Any]:
        """
        Load YAML content from file.

        Args:
            yaml_file: Path to YAML file.

        Returns:
            Parsed YAML dictionary.
        """
        content = yaml_file.read_text(encoding="utf-8")
        yaml_data = yaml.safe_load(content)
        if yaml_data is None:
            raise ValueError(f"Empty YAML file: {yaml_file}")
        return yaml_data

    def _parse_extraction_fields(
        self, yaml_data: Dict[str, Any]
    ) -> List[ExtractionField]:
        """
        Parse extraction-only fields from YAML data.

        Args:
            yaml_data: Parsed YAML dictionary.

        Returns:
            List of ExtractionField definitions.
        """
        raw_fields = yaml_data.get("extraction_fields", [])
        if not raw_fields:
            return []
        if not isinstance(raw_fields, list):
            raise ValueError("'extraction_fields' must be a list")

        fields: List[ExtractionField] = []
        for field_data in raw_fields:
            name = field_data.get("name")
            field_type = field_data.get("type")
            if not name or not field_type:
                raise ValueError("Extraction field missing name or type")

            if field_type not in SchemaParser.SUPPORTED_TYPES:
                raise ValueError(
                    f"Invalid type '{field_type}' for extraction field '{name}'. "
                    f"Supported types: {', '.join(sorted(SchemaParser.SUPPORTED_TYPES))}"
                )

            fields.append(
                ExtractionField(
                    name=name,
                    type=field_type,
                    description=field_data.get("description", ""),
                    nullable=field_data.get("nullable", True),
                    required=field_data.get("required", False),
                    python=field_data.get("python"),
                )
            )

        return fields
