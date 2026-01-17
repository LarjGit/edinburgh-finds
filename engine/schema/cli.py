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
from engine.schema.parser import SchemaParser, SchemaValidationError
from engine.schema.generators.python_fieldspec import PythonFieldSpecGenerator
from engine.schema.generators.prisma import PrismaGenerator


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
  # Generate all schemas
  python -m engine.schema.generate

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

    args = parser.parse_args()

    # Disable colors if requested or not a TTY
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Set default paths
    project_root = Path(__file__).parent.parent.parent
    schema_dir = args.schema_dir or (project_root / "engine" / "config" / "schemas")
    output_dir = args.output_dir or (project_root / "engine" / "schema")

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

    # Generate each schema
    generated_files = []
    success_count = 0
    error_count = 0

    for yaml_file in yaml_files:
        print(f"\n{colorize('Processing:', Colors.BOLD)} {yaml_file.name}")

        success, message = generate_python_schema(
            yaml_file,
            output_dir,
            dry_run=args.dry_run,
            force=args.force
        )

        if success:
            print_success(message)
            success_count += 1
            if not args.dry_run:
                generated_files.append(output_dir / f"{yaml_file.stem}.py")
        else:
            print_error(message)
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
