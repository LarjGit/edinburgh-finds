"""
Schema Generation CLI Tool

Command-line interface for generating schemas from YAML definitions.
Part of Phase 5 of the YAML Schema track.

Usage:
    python -m engine.schema.generate [options]
    python -m engine.schema.generate --validate
    python -m engine.schema.generate --schema listing --force
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from engine.schema.parser import SchemaParser, SchemaValidationError, SchemaDefinition
from engine.schema.generators.python_fieldspec import PythonFieldSpecGenerator
from engine.schema.generators.prisma import PrismaGenerator
from engine.schema.generators.pydantic_extraction import PydanticExtractionGenerator
from engine.schema.generators.typescript import TypeScriptGenerator


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

    @staticmethod
    def disable():
        """Disable colors (for non-TTY output)"""
        Colors.GREEN = ''
        Colors.RED = ''
        Colors.YELLOW = ''
        Colors.BLUE = ''
        Colors.BOLD = ''
        Colors.RESET = ''


def colorize(text: str, color: str) -> str:
    """Colorize text if colors are enabled"""
    return f"{color}{text}{Colors.RESET}"


def print_success(message: str):
    """Print success message in green"""
    print(colorize(f"✓ {message}", Colors.GREEN))


def print_error(message: str):
    """Print error message in red"""
    print(colorize(f"✗ {message}", Colors.RED), file=sys.stderr)


def print_warning(message: str):
    """Print warning message in yellow"""
    print(colorize(f"⚠ {message}", Colors.YELLOW))


def print_info(message: str):
    """Print info message in blue"""
    print(colorize(f"ℹ {message}", Colors.BLUE))


def find_schema_files(schema_dir: Path, schema_name: Optional[str] = None) -> List[Path]:
    """
    Find YAML schema files to process.

    Args:
        schema_dir: Directory containing schema files
        schema_name: Optional specific schema to generate (e.g., 'listing', 'venue')

    Returns:
        List of YAML file paths
    """
    if schema_name:
        # Generate specific schema
        schema_file = schema_dir / f"{schema_name}.yaml"
        if not schema_file.exists():
            print_error(f"Schema file not found: {schema_file}")
            sys.exit(1)
        return [schema_file]
    else:
        # Generate all schemas
        yaml_files = list(schema_dir.glob("*.yaml"))
        if not yaml_files:
            print_error(f"No YAML schema files found in {schema_dir}")
            sys.exit(1)
        return sorted(yaml_files)


def generate_python_schema(
    yaml_file: Path,
    output_dir: Path,
    dry_run: bool = False,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Generate Python FieldSpec file from YAML schema.

    Args:
        yaml_file: Path to YAML schema file
        output_dir: Directory to write generated file
        dry_run: If True, don't write file
        force: If True, overwrite without prompt

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Parse YAML
        parser = SchemaParser()
        schema = parser.parse(yaml_file)

        # Generate Python code
        generator = PythonFieldSpecGenerator()
        generated_code = generator.generate(schema, source_file=yaml_file.name)

        # Determine output file name
        output_file = output_dir / f"{yaml_file.stem}.py"

        if dry_run:
            return True, f"Would generate: {output_file}"

        # Check if file exists and prompt if not force
        if output_file.exists() and not force:
            response = input(f"File {output_file} exists. Overwrite? [y/N] ")
            if response.lower() != 'y':
                return False, f"Skipped: {output_file}"

        # Write file
        output_file.write_text(generated_code, encoding='utf-8')
        return True, f"Generated: {output_file}"

    except SchemaValidationError as e:
        return False, f"Validation error in {yaml_file.name}: {e}"
    except Exception as e:
        return False, f"Error generating from {yaml_file.name}: {e}"


def generate_typescript_schema(
    yaml_file: Path,
    output_dir: Path,
    include_zod: bool = False,
    dry_run: bool = False,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Generate TypeScript interface file from YAML schema.

    Args:
        yaml_file: Path to YAML schema file
        output_dir: Directory to write generated file
        include_zod: If True, generate Zod schemas
        dry_run: If True, don't write file
        force: If True, overwrite without prompt

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Parse YAML
        parser = SchemaParser()
        schema = parser.parse(yaml_file)

        # Generate TypeScript code
        generator = TypeScriptGenerator(include_zod=include_zod)
        generated_code = generator.generate_file(schema)

        # Determine output file name
        output_file = output_dir / f"{yaml_file.stem}.ts"

        if dry_run:
            return True, f"Would generate: {output_file}"

        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Check if file exists and prompt if not force
        if output_file.exists() and not force:
            response = input(f"File {output_file} exists. Overwrite? [y/N] ")
            if response.lower() != 'y':
                return False, f"Skipped: {output_file}"

        # Write file
        output_file.write_text(generated_code, encoding='utf-8')
        return True, f"Generated: {output_file}"

    except SchemaValidationError as e:
        return False, f"Validation error in {yaml_file.name}: {e}"
    except Exception as e:
        return False, f"Error generating from {yaml_file.name}: {e}"


def generate_pydantic_extraction_model(
    yaml_file: Path,
    output_file: Path,
    dry_run: bool = False,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Generate Pydantic extraction model from YAML schema.

    Args:
        yaml_file: Path to YAML schema file
        output_file: Full path to output file
        dry_run: If True, don't write file
        force: If True, overwrite without prompt

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        generator = PydanticExtractionGenerator()
        generated_code = generator.generate_from_yaml(yaml_file)

        if dry_run:
            return True, f"Would generate: {output_file}"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_file.exists() and not force:
            response = input(f"File {output_file} exists. Overwrite? [y/N] ")
            if response.lower() != 'y':
                return False, f"Skipped: {output_file}"

        output_file.write_text(generated_code, encoding='utf-8')
        return True, f"Generated: {output_file}"

    except SchemaValidationError as e:
        return False, f"Validation error in {yaml_file.name}: {e}"
    except Exception as e:
        return False, f"Error generating from {yaml_file.name}: {e}"


def load_prisma_schemas(yaml_files: List[Path]) -> Tuple[List[SchemaDefinition], List[str]]:
    """
    Load base schemas for Prisma generation (schemas without inheritance).

    Args:
        yaml_files: List of YAML schema files to parse

    Returns:
        Tuple of (base_schemas, skipped_schema_names)
    """
    parser = SchemaParser()
    base_schemas: List[SchemaDefinition] = []
    skipped: List[str] = []

    for yaml_file in yaml_files:
        schema = parser.parse(yaml_file)
        if schema.extends:
            skipped.append(schema.name)
            continue
        base_schemas.append(schema)

    return base_schemas, skipped


def generate_prisma_schema(
    generator: PrismaGenerator,
    schemas: List[SchemaDefinition],
    output_file: Path,
    target: str,
    dry_run: bool = False,
    force: bool = False
) -> Tuple[bool, str]:
    """
    Generate Prisma schema file for a target (engine/web).

    Args:
        generator: PrismaGenerator instance
        schemas: List of base SchemaDefinition objects
        output_file: Full path to output schema.prisma file
        target: "engine" or "web"
        dry_run: If True, don't write file
        force: If True, overwrite without prompt

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        generated_schema = generator.generate_full_schema(schemas, target=target)

        if dry_run:
            return True, f"Would generate: {output_file}"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        if output_file.exists() and not force:
            response = input(f"File {output_file} exists. Overwrite? [y/N] ")
            if response.lower() != 'y':
                return False, f"Skipped: {output_file}"

        output_file.write_text(generated_schema, encoding='utf-8')
        return True, f"Generated: {output_file}"

    except Exception as e:
        return False, f"Error generating Prisma schema ({target}): {e}"


def validate_schema_sync(schema_dir: Path, python_dir: Path) -> Tuple[bool, List[str]]:
    """
    Validate that YAML schemas match generated Python schemas.

    Args:
        schema_dir: Directory containing YAML schemas
        python_dir: Directory containing Python schemas

    Returns:
        Tuple of (all_valid: bool, messages: List[str])
    """
    messages = []
    all_valid = True

    yaml_files = find_schema_files(schema_dir)

    for yaml_file in yaml_files:
        try:
            # Parse YAML
            parser = SchemaParser()
            schema = parser.parse(yaml_file)

            # Generate expected Python code
            generator = PythonFieldSpecGenerator()
            expected_code = generator.generate(schema, source_file=yaml_file.name)

            # Read actual Python file
            python_file = python_dir / f"{yaml_file.stem}.py"
            if not python_file.exists():
                messages.append(f"✗ {yaml_file.stem}.py: File not found")
                all_valid = False
                continue

            actual_code = python_file.read_text(encoding='utf-8')

            # Compare (ignoring timestamp in header)
            expected_lines = [line for line in expected_code.split('\n')
                            if not line.startswith('# Generated at:')]
            actual_lines = [line for line in actual_code.split('\n')
                          if not line.startswith('# Generated at:')]

            if expected_lines == actual_lines:
                messages.append(f"✓ {yaml_file.stem}.py: In sync")
            else:
                messages.append(f"✗ {yaml_file.stem}.py: OUT OF SYNC - regenerate needed")
                all_valid = False

        except Exception as e:
            messages.append(f"✗ {yaml_file.stem}: Error - {e}")
            all_valid = False

    return all_valid, messages


def format_generated_files(python_files: List[Path]) -> None:
    """
    Format generated Python files with black.

    Args:
        python_files: List of Python files to format
    """
    try:
        import subprocess
        for py_file in python_files:
            result = subprocess.run(
                ['black', str(py_file), '--quiet'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print_success(f"Formatted: {py_file.name}")
            else:
                print_warning(f"Could not format {py_file.name}: {result.stderr}")
    except FileNotFoundError:
        print_warning("Black not found - skipping formatting")
    except Exception as e:
        print_warning(f"Formatting failed: {e}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Generate schemas from YAML definitions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all schemas (Python + Prisma)
  python -m engine.schema.generate

  # Generate Python and TypeScript schemas
  python -m engine.schema.generate --typescript

  # Generate TypeScript with Zod validation schemas
  python -m engine.schema.generate --typescript --zod

  # Generate Prisma schemas only
  python -m engine.schema.generate --prisma

  # Generate without Prisma
  python -m engine.schema.generate --no-prisma

  # Generate Pydantic extraction model (entity_extraction.py)
  python -m engine.schema.generate --pydantic-extraction

  # Validate schemas are in sync
  python -m engine.schema.generate --validate

  # Generate specific schema
  python -m engine.schema.generate --schema listing

  # Force overwrite without prompts
  python -m engine.schema.generate --force

  # Dry run (show what would be generated)
  python -m engine.schema.generate --dry-run

  # Generate and format
  python -m engine.schema.generate --format
        """
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Check if schemas match YAML (exit 1 if drift detected)'
    )

    parser.add_argument(
        '--schema',
        type=str,
        help='Generate specific schema (e.g., listing, venue)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        help='Output directory for generated files (default: engine/schema)'
    )

    parser.add_argument(
        '--schema-dir',
        type=Path,
        help='Directory containing YAML schemas (default: engine/config/schemas)'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files without prompt'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without writing files'
    )

    parser.add_argument(
        '--format',
        action='store_true',
        help='Format generated files with black'
    )

    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )

    parser.add_argument(
        '--typescript',
        action='store_true',
        help='Generate TypeScript interfaces'
    )

    parser.add_argument(
        '--pydantic-extraction',
        action='store_true',
        help='Generate Pydantic extraction model from listing.yaml'
    )

    prisma_group = parser.add_mutually_exclusive_group()
    prisma_group.add_argument(
        '--prisma',
        action='store_true',
        help='Generate Prisma schemas only (skip other outputs)'
    )
    prisma_group.add_argument(
        '--no-prisma',
        action='store_true',
        help='Skip Prisma schema generation'
    )

    parser.add_argument(
        '--zod',
        action='store_true',
        help='Include Zod schemas (requires --typescript)'
    )

    parser.add_argument(
        '--typescript-output-dir',
        type=Path,
        help='Output directory for TypeScript files (default: web/types)'
    )

    args = parser.parse_args()

    # Disable colors if requested or not a TTY
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Set default paths
    project_root = Path(__file__).parent.parent.parent
    schema_dir = args.schema_dir or (project_root / "engine" / "config" / "schemas")
    output_dir = args.output_dir or (project_root / "engine" / "schema")
    typescript_output_dir = args.typescript_output_dir or (project_root / "web" / "types")

    # Determine which generators to run
    generate_python = True
    generate_typescript = args.typescript
    generate_pydantic_extraction = args.pydantic_extraction
    generate_prisma = not args.no_prisma

    if args.prisma:
        generate_python = False
        generate_typescript = False
        generate_pydantic_extraction = False
        generate_prisma = True

        if args.typescript or args.pydantic_extraction or args.zod:
            print_warning("--prisma ignores --typescript/--zod/--pydantic-extraction")

    # Validate Zod flag
    if args.zod and not generate_typescript:
        if args.prisma:
            print_warning("--zod ignored because --prisma was set")
        else:
            print_error("--zod requires --typescript flag")
            sys.exit(1)

    if generate_pydantic_extraction and args.schema and args.schema != "listing":
        print_error("--pydantic-extraction only supports --schema listing")
        sys.exit(1)

    # Validate mode
    if args.validate:
        print_info("Validating schema synchronization...")
        all_valid, messages = validate_schema_sync(schema_dir, output_dir)

        for msg in messages:
            if msg.startswith('✓'):
                print_success(msg[2:])
            else:
                print_error(msg[2:])

        if all_valid:
            print_success("\nAll schemas are in sync!")
            sys.exit(0)
        else:
            print_error("\nSchema drift detected! Run without --validate to regenerate.")
            sys.exit(1)

    # Generate mode
    print_info(f"Schema directory: {schema_dir}")
    print_info(f"Output directory: {output_dir}")

    if args.dry_run:
        print_warning("DRY RUN MODE - No files will be written")

    # Find schema files
    yaml_files = find_schema_files(schema_dir, args.schema)
    print_info(f"Found {len(yaml_files)} schema(s) to generate")

    # Generate each schema (per-file outputs)
    generated_files = []
    success_count = 0
    error_count = 0
    extraction_output = (
        project_root / "engine" / "extraction" / "models" / "entity_extraction.py"
    )

    if generate_python or generate_pydantic_extraction or generate_typescript:
        for yaml_file in yaml_files:
            print(f"\n{colorize('Processing:', Colors.BOLD)} {yaml_file.name}")

            # Generate Python schema
            if generate_python:
                success, message = generate_python_schema(
                    yaml_file,
                    output_dir,
                    dry_run=args.dry_run,
                    force=args.force
                )

                if success:
                    print_success(f"Python: {message}")
                    success_count += 1
                    if not args.dry_run:
                        generated_files.append(output_dir / f"{yaml_file.stem}.py")
                else:
                    print_error(f"Python: {message}")
                    error_count += 1

            # Generate Pydantic extraction model (listing.yaml only)
            if generate_pydantic_extraction and yaml_file.stem == "listing":
                extraction_success, extraction_message = generate_pydantic_extraction_model(
                    yaml_file,
                    extraction_output,
                    dry_run=args.dry_run,
                    force=args.force
                )

                if extraction_success:
                    print_success(f"Pydantic: {extraction_message}")
                    success_count += 1
                    if not args.dry_run:
                        generated_files.append(extraction_output)
                else:
                    print_error(f"Pydantic: {extraction_message}")
                    error_count += 1

            # Generate TypeScript schema if requested
            if generate_typescript:
                ts_success, ts_message = generate_typescript_schema(
                    yaml_file,
                    typescript_output_dir,
                    include_zod=args.zod,
                    dry_run=args.dry_run,
                    force=args.force
                )

                if ts_success:
                    print_success(f"TypeScript: {ts_message}")
                    success_count += 1
                else:
                    print_error(f"TypeScript: {ts_message}")
                    error_count += 1

    # Generate Prisma schemas (engine + web)
    if generate_prisma:
        prisma_schemas, skipped_schemas = load_prisma_schemas(yaml_files)

        if not prisma_schemas:
            print_warning("Prisma: No base schemas found; skipping Prisma generation")
        else:
            if skipped_schemas:
                print_info(f"Prisma: Skipping inherited schemas: {', '.join(skipped_schemas)}")

            prisma_generator = PrismaGenerator(database="sqlite")
            prisma_targets = {
                "engine": project_root / "engine" / "schema.prisma",
                "web": project_root / "web" / "prisma" / "schema.prisma",
            }

            for target, output_path in prisma_targets.items():
                success, message = generate_prisma_schema(
                    prisma_generator,
                    prisma_schemas,
                    output_path,
                    target=target,
                    dry_run=args.dry_run,
                    force=args.force
                )

                if success:
                    print_success(f"Prisma ({target}): {message}")
                    success_count += 1
                else:
                    print_error(f"Prisma ({target}): {message}")
                    error_count += 1

    # Format files if requested
    if args.format and generated_files and not args.dry_run:
        print(f"\n{colorize('Formatting generated files...', Colors.BOLD)}")
        format_generated_files(generated_files)

    # Summary
    print(f"\n{colorize('Summary:', Colors.BOLD)}")
    print_success(f"{success_count} schema(s) generated successfully")
    if error_count > 0:
        print_error(f"{error_count} schema(s) failed")
        sys.exit(1)

    if args.dry_run:
        print_info("Dry run complete - no files were written")


if __name__ == '__main__':
    main()
