"""
TXT to CSV Converter for Lottery Data Files

Converts space-separated .txt lottery data files to comma-separated .csv format
with standardized headers (date,QS1,QS2,QS3,QS4).

Usage:
    python txt_to_csv_converter.py [--input-dir PATH] [--dry-run]
"""

import os
import sys
from pathlib import Path


def convert_txt_to_csv(txt_path: Path, output_path: Path) -> int:
    """
    Convert a space-separated txt file to CSV format.

    Args:
        txt_path: Path to input .txt file
        output_path: Path for output .csv file

    Returns:
        Number of data rows converted
    """
    rows_converted = 0

    with open(txt_path, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    with open(output_path, 'w', encoding='utf-8', newline='') as outfile:
        # Write header
        outfile.write("date,QS1,QS2,QS3,QS4\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Split by whitespace (handles both single and multiple spaces)
            parts = line.split()

            if len(parts) >= 5:
                # Format: date digit1 digit2 digit3 digit4
                date = parts[0]
                digits = parts[1:5]
                csv_line = f"{date},{','.join(digits)}\n"
                outfile.write(csv_line)
                rows_converted += 1
            elif len(parts) == 5:
                # Already in expected format
                csv_line = ','.join(parts) + '\n'
                outfile.write(csv_line)
                rows_converted += 1

    return rows_converted


def process_directory(input_dir: Path, dry_run: bool = False) -> dict:
    """
    Process all .txt files in a directory.

    Args:
        input_dir: Directory containing .txt files
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

    # Find all .txt files (case-insensitive)
    txt_files = list(input_dir.glob('*.txt')) + list(input_dir.glob('*.Txt')) + list(input_dir.glob('*.TXT'))
    # Remove duplicates (in case of case-insensitive filesystem)
    txt_files = list(set(txt_files))

    stats['files_found'] = len(txt_files)

    for txt_path in sorted(txt_files):
        # Generate output path with .csv extension
        csv_path = txt_path.with_suffix('.csv')

        # Skip if CSV already exists
        if csv_path.exists():
            print(f"SKIP: {txt_path.name} -> CSV already exists")
            stats['files_skipped'] += 1
            continue

        if dry_run:
            print(f"WOULD CONVERT: {txt_path.name} -> {csv_path.name}")
            stats['files_converted'] += 1
        else:
            try:
                rows = convert_txt_to_csv(txt_path, csv_path)
                print(f"CONVERTED: {txt_path.name} -> {csv_path.name} ({rows} rows)")
                stats['files_converted'] += 1
                stats['total_rows'] += rows
            except Exception as e:
                error_msg = f"ERROR: {txt_path.name} - {str(e)}"
                print(error_msg)
                stats['errors'].append(error_msg)

    return stats


def main():
    # Default input directory
    default_dir = Path(r"C:\Users\Minis\CascadeProjects\CA-4_\data\raw")

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
    print("-" * 60)

    # Process files
    stats = process_directory(input_dir, dry_run)

    # Print summary
    print("-" * 60)
    print(f"Summary:")
    print(f"  Files found:     {stats['files_found']}")
    print(f"  Files converted: {stats['files_converted']}")
    print(f"  Files skipped:   {stats['files_skipped']}")
    if not dry_run:
        print(f"  Total rows:      {stats['total_rows']}")
    if stats['errors']:
        print(f"  Errors:          {len(stats['errors'])}")
        for err in stats['errors']:
            print(f"    - {err}")


if __name__ == "__main__":
    main()
