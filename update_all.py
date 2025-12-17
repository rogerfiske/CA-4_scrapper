"""
CA-4 Scraper - Master Update Script

Runs the complete data update pipeline:
1. Scrapes new lottery results from lotterypost.com
2. Regenerates binary CSV files
3. Regenerates aggregate CSV files (eve, mid, daily)
4. Updates c-4_RESULTS.txt reference file

Usage:
    python update_all.py [--dry-run] [--skip-scrape] [--skip-aggregates]

Options:
    --dry-run         Show what would be done without making changes
    --skip-scrape     Skip scraping, just regenerate aggregates
    --skip-aggregates Skip aggregate regeneration
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.absolute()
SRC_UTILITIES = PROJECT_ROOT / "src" / "utilities"
DATA_DIR = PROJECT_ROOT / "data"


def run_script(script_path, args=None, description=""):
    """Run a Python script and return success status."""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")

    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(f"WARNING: {description} returned exit code {result.returncode}")
        return False
    return True


def update_ca_results_file():
    """Update c-4_RESULTS.txt from CA_Daily_4_dat.csv."""
    print(f"\n{'='*60}")
    print("STEP: Updating c-4_RESULTS.txt")
    print(f"{'='*60}")

    ca_csv_path = DATA_DIR / "raw" / "CA_Daily_4_dat.csv"
    results_path = DATA_DIR / "c-4_RESULTS.txt"

    if not ca_csv_path.exists():
        print(f"ERROR: CA CSV not found: {ca_csv_path}")
        return False

    # Read CA CSV and extract results (newest first)
    results = []
    with open(ca_csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines[1:]:  # Skip header
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) >= 5:
            # Combine QS1-QS4 into a 4-digit string
            result = ''.join(parts[1:5])
            results.append(result)

    # Keep chronological order (oldest first) to match aggregate CSVs
    # Write to results file
    with open(results_path, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(f"{result}\n")

    print(f"Updated {results_path.name} with {len(results)} results (oldest first)")
    return True


def main():
    # Parse arguments
    dry_run = '--dry-run' in sys.argv
    skip_scrape = '--skip-scrape' in sys.argv
    skip_aggregates = '--skip-aggregates' in sys.argv

    print("="*70)
    print("CA-4 SCRAPER - MASTER UPDATE SCRIPT")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project root: {PROJECT_ROOT}")

    if dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***")

    success = True

    # Step 1: Run scraper
    if not skip_scrape:
        scraper_args = ['--dry-run'] if dry_run else []
        scraper_success = run_script(
            SRC_UTILITIES / "scraper_4digit.py",
            args=scraper_args,
            description="Scraping new lottery results"
        )
        if not scraper_success:
            print("WARNING: Scraper had issues, continuing anyway...")
    else:
        print("\n[SKIPPED] Scraping (--skip-scrape flag)")

    # Step 2: Regenerate binary files (scraper does this, but run explicitly if skipped)
    if skip_scrape and not dry_run:
        binary_success = run_script(
            SRC_UTILITIES / "csv_to_binary.py",
            description="Regenerating binary CSV files"
        )
        if not binary_success:
            success = False

    # Step 3: Regenerate aggregates
    if not skip_aggregates and not dry_run:
        aggregate_success = run_script(
            SRC_UTILITIES / "create_aggregates.py",
            description="Regenerating aggregate CSV files"
        )
        if not aggregate_success:
            success = False
    else:
        print("\n[SKIPPED] Aggregates (--skip-aggregates flag or dry-run)")

    # Step 4: Update c-4_RESULTS.txt
    if not dry_run:
        results_success = update_ca_results_file()
        if not results_success:
            success = False
    else:
        print("\n[SKIPPED] c-4_RESULTS.txt update (dry-run)")

    # Summary
    print("\n" + "="*70)
    print("UPDATE COMPLETE")
    print("="*70)
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if dry_run:
        print("\n*** DRY RUN - No changes were made ***")
    else:
        print("\nOutput files updated:")
        print(f"  - data/raw/*.csv (lottery results)")
        print(f"  - data/raw/*_binary.csv (one-hot encoded)")
        print(f"  - data/aggregates/CA_4_predict_eve_aggregate.csv")
        print(f"  - data/aggregates/CA_4_predict_mid_aggregate.csv")
        print(f"  - data/aggregates/CA_4_predict_daily_aggregate.csv")
        print(f"  - data/c-4_RESULTS.txt")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
