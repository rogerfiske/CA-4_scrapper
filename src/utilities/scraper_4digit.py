"""
4-Digit Lottery Results Scraper

Scrapes lottery data from lotterypost.com and updates CSV files.
Uses Selenium with Chrome to bypass website restrictions.

After updating all CSV files, automatically runs csv_to_binary.py to
regenerate binary versions.

Usage:
    python scraper_4digit.py [--dry-run] [--limit N] [--file FILENAME]
"""

import csv
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# Paths
PROJECT_ROOT = Path(r"C:\Users\Minis\CascadeProjects\CA-4_scrapper")
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
LOOKUP_CSV = PROJECT_ROOT / "data" / "lotterypost_dat_lookup.csv"
BINARY_CONVERTER = PROJECT_ROOT / "src" / "utilities" / "csv_to_binary.py"


def load_lottery_config() -> list[dict]:
    """Load lottery configuration from the lookup CSV file."""
    configs = []

    with open(LOOKUP_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            file_name = row.get('file', '').strip()
            url = row.get('URL', '').strip()

            if not file_name or not url:
                continue

            # Parse TOD type and time slot from filename
            tod_class = None
            time_slot = None

            if '_TODmid_' in file_name:
                tod_class = 'TODmid'
                # Extract time slot (Morning, Midday, Day, 1PM, 4PM, 150pm, etc.)
                match = re.search(r'_TODmid_([^_]+)_dat', file_name)
                if match:
                    time_slot = match.group(1).lower()
            elif '_TODeve_' in file_name:
                tod_class = 'TODeve'
                match = re.search(r'_TODeve_([^_]+)_dat', file_name)
                if match:
                    time_slot = match.group(1).lower()
            # Single draw states (CA, LA, WV) have no TOD in filename

            configs.append({
                'name': file_name,
                'csv_path': DATA_RAW_DIR / f"{file_name}.csv",
                'url': url,
                'tod_class': tod_class,
                'time_slot': time_slot,
            })

    return configs


def get_last_date_from_csv(csv_path: Path) -> datetime | None:
    """Read the CSV file and return the last date entry."""
    if not csv_path.exists():
        print(f"    ERROR: CSV file not found: {csv_path}")
        return None

    last_date = None
    last_line = None

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.lower().startswith("date"):
                last_line = stripped

    if last_line:
        try:
            date_str = last_line.split(",")[0]
            last_date = datetime.strptime(date_str, "%m/%d/%Y")
        except (ValueError, IndexError) as e:
            print(f"    ERROR parsing last line '{last_line}': {e}")

    return last_date


def create_driver():
    """Create a Selenium WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def fetch_page_results(driver, url: str) -> list[dict]:
    """
    Fetch all lottery results from a page.

    Returns list of dicts with: date, tod_class, time_text, numbers
    """
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "time"))
        )
        time.sleep(2)
    except Exception as e:
        print(f"    ERROR loading URL {url}: {e}")
        return []

    soup = BeautifulSoup(driver.page_source, "html.parser")
    results = []

    # Find the main content area
    main_content = soup.find("main")
    if not main_content:
        print("    ERROR: Could not find main content area")
        return []

    # Strategy: Find all drawWrap elements and associate each with its date
    # The date comes from the preceding time element

    # First, find all elements in order to track which date each drawWrap belongs to
    all_draw_wraps = main_content.find_all("div", class_="drawWrap")

    if '--debug' in sys.argv:
        print(f"      DEBUG: Found {len(all_draw_wraps)} total drawWrap divs on page")

    if all_draw_wraps:
        # For each drawWrap, find its associated date by looking for preceding time element
        for draw_wrap in all_draw_wraps:
            try:
                tod_class = None
                time_text = None
                draw_date = None

                # Find the date - traverse up and look for time element in ancestors or siblings
                parent = draw_wrap.parent
                for _ in range(15):
                    if parent is None:
                        break

                    # Look for time element in this parent
                    time_elem = parent.find("time")
                    if time_elem:
                        datetime_attr = time_elem.get("datetime", "")
                        if datetime_attr:
                            date_str = datetime_attr.split("T")[0]
                            try:
                                draw_date = datetime.strptime(date_str, "%Y-%m-%d")
                                break
                            except ValueError:
                                pass

                    parent = parent.parent

                if not draw_date:
                    continue

                # Find TOD div within this drawWrap
                tod_div = draw_wrap.find("div", class_="TOD")
                if tod_div:
                    # Get TOD class (TODmid or TODeve)
                    tod_icon = tod_div.find("i")
                    if tod_icon:
                        classes = tod_icon.get("class", [])
                        for cls in classes:
                            if cls in ["TODmid", "TODeve"]:
                                tod_class = cls
                                break

                    # Get time text after <br> tag
                    br_tag = tod_div.find("br")
                    if br_tag and br_tag.next_sibling:
                        time_text = str(br_tag.next_sibling).strip().lower()
                    else:
                        tod_text = tod_div.get_text(strip=True).lower()
                        time_text = re.sub(r'[^a-z0-9:]', '', tod_text)

                # Find numbers in this drawWrap
                results_ul = draw_wrap.find("ul", class_="resultsnums")
                if results_ul:
                    li_elements = results_ul.find_all("li")
                    if len(li_elements) >= 4:
                        numbers = []
                        for li in li_elements[:4]:
                            num_text = li.get_text(strip=True)
                            num_text = "".join(c for c in num_text if c.isdigit())
                            if num_text:
                                numbers.append(int(num_text))

                        if len(numbers) == 4:
                            results.append({
                                "date": draw_date,
                                "tod_class": tod_class,
                                "time_text": time_text,
                                "numbers": numbers,
                            })

            except Exception as e:
                if '--debug' in sys.argv:
                    print(f"      DEBUG: Error parsing drawWrap: {e}")
                continue
    else:
        # Fallback for single-draw states (no drawWrap structure)
        time_elements = main_content.find_all("time")

        for time_elem in time_elements:
            try:
                datetime_attr = time_elem.get("datetime", "")
                if not datetime_attr:
                    continue

                date_str = datetime_attr.split("T")[0]
                try:
                    draw_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    continue

                # Look for results in parent hierarchy
                parent = time_elem.parent
                for _ in range(10):
                    if parent is None:
                        break

                    results_ul = parent.find("ul", class_="resultsnums")
                    if results_ul:
                        li_elements = results_ul.find_all("li")
                        if len(li_elements) >= 4:
                            numbers = []
                            for li in li_elements[:4]:
                                num_text = li.get_text(strip=True)
                                num_text = "".join(c for c in num_text if c.isdigit())
                                if num_text:
                                    numbers.append(int(num_text))

                            if len(numbers) == 4:
                                results.append({
                                    "date": draw_date,
                                    "tod_class": None,
                                    "time_text": None,
                                    "numbers": numbers,
                                })
                        break

                    parent = parent.parent

            except Exception as e:
                continue

    # Remove duplicates (same date + tod_class + numbers)
    seen = set()
    unique_results = []
    for r in results:
        key = (r["date"], r["tod_class"], tuple(r["numbers"]))
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    # Sort by date ascending
    unique_results.sort(key=lambda x: (x["date"], x["tod_class"] or ""))

    return unique_results


def match_time_slot(time_text: str | None, target_slot: str | None) -> bool:
    """Check if the scraped time_text matches the target time slot."""
    # If no target slot required, any result matches
    if not target_slot:
        return True

    # If we need a specific slot but have no time_text, don't match
    if not time_text:
        return False

    time_text = time_text.lower()
    target_slot = target_slot.lower()

    # Direct matches
    if target_slot in time_text or time_text in target_slot:
        return True

    # Time-based matches - map target slots to possible time_text values
    time_mappings = {
        '1pm': ['1pm', '1:00', '100pm', '1 pm'],
        '4pm': ['4pm', '4:00', '400pm', '4 pm'],
        '7pm': ['7pm', '7:00', '700pm', '7 pm'],
        '10pm': ['10pm', '10:00', '1000pm', '10 pm'],
        '150pm': ['1:50', '150pm', '150', '1:50pm'],
        '750pm': ['7:50', '750pm', '750', '7:50pm'],
        'morning': ['morning', 'morn'],
        'midday': ['midday', 'mid-day', 'noon'],
        'day': ['day', 'daytime'],
        'evening': ['evening', 'eve'],
        'night': ['night', 'nite'],
        'daytime': ['daytime', 'day'],
    }

    if target_slot in time_mappings:
        for variant in time_mappings[target_slot]:
            if variant in time_text:
                return True

    return False


def filter_results_for_lottery(all_results: list[dict], config: dict, debug: bool = False) -> list[dict]:
    """Filter scraped results to match a specific lottery's TOD and time slot."""
    filtered = []

    if debug:
        print(f"    DEBUG: Filtering for tod_class={config['tod_class']}, time_slot={config['time_slot']}")
        unique_combos = set()
        for r in all_results:
            unique_combos.add((r.get('tod_class'), r.get('time_text')))
        print(f"    DEBUG: Unique (tod_class, time_text) combos found: {sorted(unique_combos)}")

    for result in all_results:
        # If lottery has no TOD requirement (single draw states)
        if config['tod_class'] is None:
            filtered.append(result)
            continue

        # Check TOD class matches
        if result['tod_class'] != config['tod_class']:
            continue

        # Check time slot if specified
        if config['time_slot']:
            if not match_time_slot(result.get('time_text', ''), config['time_slot']):
                continue

        filtered.append(result)

    return filtered


def append_results_to_csv(csv_path: Path, results: list[dict]) -> int:
    """Append new results to the CSV file. Returns count of appended rows."""
    if not results:
        return 0

    with open(csv_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.rstrip()

    new_lines = []
    for result in results:
        date_str = result["date"].strftime("%m/%d/%Y")
        numbers_str = ",".join(str(n) for n in result["numbers"])
        new_lines.append(f"{date_str},{numbers_str}")

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
        for line in new_lines:
            f.write(f"\n{line}")

    return len(results)


def process_lottery(driver, config: dict, url_cache: dict, dry_run: bool = False) -> tuple[bool, int]:
    """
    Process a single lottery - fetch new results and update CSV.

    Returns (success, new_results_count)
    """
    print(f"\n  Processing: {config['name']}")
    print(f"    CSV: {config['csv_path'].name}")
    print(f"    TOD: {config['tod_class'] or 'None (single draw)'}, Slot: {config['time_slot'] or 'N/A'}")

    # Get last date from CSV
    last_date = get_last_date_from_csv(config["csv_path"])
    if last_date is None:
        print("    ERROR: Could not determine last date from CSV")
        return False, 0

    print(f"    Last date in CSV: {last_date.strftime('%m/%d/%Y')}")

    # Check cache for already-fetched URL results
    url = config['url']
    if url not in url_cache:
        print(f"    Fetching results from: {url}")
        url_cache[url] = fetch_page_results(driver, url)
        print(f"    Found {len(url_cache[url])} total results on page")
    else:
        print(f"    Using cached results ({len(url_cache[url])} entries)")

    all_results = url_cache[url]

    if not all_results:
        print("    ERROR: No results available from page")
        return False, 0

    # Filter results for this specific lottery
    debug_filter = '--debug' in sys.argv
    filtered_results = filter_results_for_lottery(all_results, config, debug=debug_filter)
    print(f"    Filtered to {len(filtered_results)} results matching TOD/slot")

    # Filter to only new results (after last_date)
    new_results = [r for r in filtered_results if r["date"] > last_date]

    if not new_results:
        print(f"    No new results found after {last_date.strftime('%m/%d/%Y')}")
        return True, 0

    print(f"    Found {len(new_results)} new result(s) to add:")
    for r in new_results[:5]:  # Show first 5
        print(f"      {r['date'].strftime('%m/%d/%Y')}: {r['numbers']}")
    if len(new_results) > 5:
        print(f"      ... and {len(new_results) - 5} more")

    if dry_run:
        print(f"    DRY RUN: Would append {len(new_results)} row(s)")
        return True, len(new_results)

    # Append to CSV
    count = append_results_to_csv(config["csv_path"], new_results)
    print(f"    Successfully appended {count} new row(s) to CSV")

    return True, count


def delete_binary_files():
    """Delete all existing binary CSV files to force regeneration."""
    binary_files = list(DATA_RAW_DIR.glob("*_binary.csv"))
    for f in binary_files:
        f.unlink()
    return len(binary_files)


def run_binary_converter():
    """Run the csv_to_binary.py script to regenerate binary files."""
    print("\n" + "=" * 60)
    print("Running binary converter...")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, str(BINARY_CONVERTER)],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def main():
    """Main entry point."""
    # Parse arguments
    dry_run = '--dry-run' in sys.argv
    limit = None
    target_file = None

    for i, arg in enumerate(sys.argv):
        if arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
        elif arg == '--file' and i + 1 < len(sys.argv):
            target_file = sys.argv[i + 1]

    print("4-Digit Lottery Results Scraper")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("MODE: DRY RUN (no files will be modified)")

    # Load configuration
    configs = load_lottery_config()
    print(f"\nLoaded {len(configs)} lottery configurations")

    # Filter if specific file requested
    if target_file:
        configs = [c for c in configs if target_file.lower() in c['name'].lower()]
        print(f"Filtered to {len(configs)} matching '{target_file}'")

    # Apply limit
    if limit:
        configs = configs[:limit]
        print(f"Limited to first {limit} lotteries")

    if not configs:
        print("No lotteries to process!")
        return 1

    # Group by URL to minimize page loads
    url_groups = {}
    for config in configs:
        url = config['url']
        if url not in url_groups:
            url_groups[url] = []
        url_groups[url].append(config)

    print(f"Grouped into {len(url_groups)} unique URLs")

    # Create browser driver
    print("\nInitializing browser...")
    driver = None
    try:
        driver = create_driver()
        print("Browser initialized successfully")

        url_cache = {}
        success_count = 0
        total_new_results = 0

        for url, url_configs in url_groups.items():
            print(f"\n{'='*60}")
            print(f"URL: {url}")
            print(f"Lotteries: {len(url_configs)}")
            print("=" * 60)

            for config in url_configs:
                try:
                    success, new_count = process_lottery(driver, config, url_cache, dry_run)
                    if success:
                        success_count += 1
                        total_new_results += new_count
                except Exception as e:
                    print(f"    ERROR processing {config['name']}: {e}")

        print(f"\n{'='*60}")
        print(f"Scraping Complete")
        print(f"{'='*60}")
        print(f"  Lotteries processed: {success_count}/{len(configs)}")
        print(f"  Total new results: {total_new_results}")
        print(f"  Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Run binary converter if not dry run and we have new results
        if not dry_run and total_new_results > 0:
            print("\nDeleting existing binary files for regeneration...")
            deleted = delete_binary_files()
            print(f"Deleted {deleted} binary files")

            if not run_binary_converter():
                print("WARNING: Binary converter returned errors")

        return 0 if success_count == len(configs) else 1

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if driver:
            driver.quit()
            print("\nBrowser closed")


if __name__ == "__main__":
    sys.exit(main())
