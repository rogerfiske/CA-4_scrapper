"""
CSV to Binary (One-Hot Encoded) Converter for Lottery Data

Converts lottery CSV files with QS1-QS4 columns to binary one-hot encoded format.
Each QSx value (0-9) is expanded into 10 binary columns (QSx_0 through QSx_9).

Example:
    Input:  date,QS1,QS2,QS3,QS4
            5/19/2008,7,6,3,1

    Output: date,QS1_0,QS1_1,...,QS1_9,QS2_0,...,QS4_9
            5/19/2008,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,0,0,0,...

Usage:
    python csv_to_binary.py [--input-dir PATH] [--dry-run]
"""

import os
import sys
from pathlib import Path


def generate_binary_header() -> str:
    """Generate the header row with all binary columns."""
    columns = ["date"]
    for qs in range(1, 5):  # QS1 through QS4
        for digit in range(10):  # 0 through 9
            columns.append(f"QS{qs}_{digit}")
    return ",".join(columns)


def convert_row_to_binary(date: str, qs_values: list) -> str:
    """
    Convert a single row to binary format.

    Args:
        date: The date string
        qs_values: List of 4 digit values [QS1, QS2, QS3, QS4]

    Returns:
        CSV row string with binary encoding
    """
    row_parts = [date]

    for qs_idx, value in enumerate(qs_values):
        # Create 10 binary columns for this QS position
        digit = int(value)
        for d in range(10):
            row_parts.append("1" if d == digit else "0")

    return ",".join(row_parts)


def convert_csv_to_binary(input_path: Path, output_path: Path) -> int:
    """
    Convert a CSV file to binary one-hot encoded format.

    Args:
        input_path: Path to input CSV file
        output_path: Path for output binary CSV file

    Returns:
        Number of data rows converted
    """
    rows_converted = 0

    with open(input_path, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    with open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        # Write binary header
        outfile.write(generate_binary_header() + "\n")

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Skip header row
            if i == 0 and line.lower().startswith("date"):
                continue

            parts = line.split(",")
            if len(parts) >= 5:
                date = parts[0]
                qs_values = parts[1:5]

                try:
                    binary_row = convert_row_to_binary(date, qs_values)
                    outfile.write(binary_row + "\n")
                    rows_converted += 1
                except ValueError as e:
                    print(f"  Warning: Skipping invalid row {i+1}: {line} ({e})")

    return rows_converted


def process_directory(input_dir: Path, dry_run: bool = False) -> dict:
    """
    Process all CSV files in a directory (excluding *_binary.csv files).

    Args:
        input_dir: Directory containing CSV files
        dry_run: If True, only report what would be done

    Returns:
        Dictionary with conversion statistics
    """
    stats = {
        'files_found': 0,
        'files_converted': 0,
        'files_skipped': 0,
        'total_rows': 0,
        'errors': []
    }

    # Find all .csv files (excluding already converted _binary.csv files)
    csv_files = [f for f in input_dir.glob('*.csv') if not f.stem.endswith('_binary')]

    stats['files_found'] = len(csv_files)

    for csv_path in sorted(csv_files):
        # Generate output path with _binary suffix
        output_path = csv_path.with_name(f"{csv_path.stem}_binary.csv")

        # Skip if binary file already exists
        if output_path.exists():
            print(f"SKIP: {csv_path.name} -> binary file already exists")
            stats['files_skipped'] += 1
            continue

        if dry_run:
            print(f"WOULD CONVERT: {csv_path.name} -> {output_path.name}")
            stats['files_converted'] += 1
        else:
            try:
                rows = convert_csv_to_binary(csv_path, output_path)
                print(f"CONVERTED: {csv_path.name} -> {output_path.name} ({rows} rows)")
                stats['files_converted'] += 1
                stats['total_rows'] += rows
            except Exception as e:
                error_msg = f"ERROR: {csv_path.name} - {str(e)}"
                print(error_msg)
                stats['errors'].append(error_msg)

    return stats


def main():
    # Default input directory
    default_dir = Path(r"C:\Users\Minis\CascadeProjects\CA-4_scrapper\data\raw")

    # Parse arguments
    input_dir = default_dir
    dry_run = False

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--input-dir' and i + 1 < len(args):
            input_dir = Path(args[i + 1])
            i += 2
        elif args[i] == '--dry-run':
            dry_run = True
            i += 1
        elif args[i] in ['-h', '--help']:
            print(__doc__)
            sys.exit(0)
        else:
            print(f"Unknown argument: {args[i]}")
            print(__doc__)
            sys.exit(1)

    # Validate directory
    if not input_dir.exists():
        print(f"Error: Directory not found: {input_dir}")
        sys.exit(1)

    if not input_dir.is_dir():
        print(f"Error: Not a directory: {input_dir}")
        sys.exit(1)

    print(f"{'DRY RUN - ' if dry_run else ''}Processing directory: {input_dir}")
    print(f"Output format: date + 40 binary columns (QS1_0-9, QS2_0-9, QS3_0-9, QS4_0-9)")
    print("-" * 70)

    # Process files
    stats = process_directory(input_dir, dry_run)

    # Print summary
    print("-" * 70)
    print(f"Summary:")
    print(f"  CSV files found:    {stats['files_found']}")
    print(f"  Files converted:    {stats['files_converted']}")
    print(f"  Files skipped:      {stats['files_skipped']}")
    if not dry_run:
        print(f"  Total rows:         {stats['total_rows']}")
    if stats['errors']:
        print(f"  Errors:             {len(stats['errors'])}")
        for err in stats['errors']:
            print(f"    - {err}")


if __name__ == "__main__":
    main()
