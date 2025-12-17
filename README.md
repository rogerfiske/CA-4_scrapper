# CA-4 Lottery Data Scraper

A data scraping and aggregation utility for Pick-4/Daily-4 lottery results from 20 US states.

---

## Quick Start Commands

Open a terminal in this project directory and run:

### Full Update (Recommended)
```bash
python update_all.py
```
This runs the complete pipeline:
1. Scrapes new results from lotterypost.com
2. Regenerates binary CSV files
3. Regenerates aggregate CSV files
4. Updates c-4_RESULTS.txt

### Dry Run (Preview Only)
```bash
python update_all.py --dry-run
```
Shows what would be updated without making any changes.

### Skip Scraping (Regenerate Aggregates Only)
```bash
python update_all.py --skip-scrape
```
Useful if you manually updated CSV files and just need to regenerate aggregates.

### Individual Scripts
```bash
# Run scraper only
python src/utilities/scraper_4digit.py

# Run scraper in dry-run mode
python src/utilities/scraper_4digit.py --dry-run

# Regenerate binary files only
python src/utilities/csv_to_binary.py

# Regenerate aggregates only
python src/utilities/create_aggregates.py
```

---

## Data Structure

### Source Files (Updated by Scraper)
```
data/raw/
├── CA_Daily_4_dat.csv          # California (reference)
├── CT_play_4_TODmid_Day_dat.csv
├── CT_play_4_TODeve_Night_dat.csv
├── ... (43 state lottery files total)
└── *_binary.csv                # One-hot encoded versions
```

### Output Files (Generated)
```
data/aggregates/
├── CA_4_predict_eve_aggregate.csv    # Evening draws (21 files)
├── CA_4_predict_mid_aggregate.csv    # Midday draws (21 files)
├── CA_4_predict_daily_aggregate.csv  # Combined (42 files)
├── eve_sources.json                  # Evening cohort configuration
└── mid_sources.json                  # Midday cohort configuration

data/
└── c-4_RESULTS.txt                   # CA results (oldest first)
```

---

## States Included (20)

| State | Abbreviation | EVE | MID |
|-------|--------------|-----|-----|
| Connecticut | CT | Yes | Yes |
| Washington DC | DC | Yes | Yes |
| Delaware | DE | Yes | Yes |
| Florida | FL | Yes | Yes |
| Georgia | GA | Yes | Yes |
| Illinois | IL | Yes | Yes |
| Kentucky | KY | Yes | Yes |
| Massachusetts | MA | Yes | Yes |
| Maryland | MD | Yes | Yes |
| Maine/NH/Vermont | ME_NH_VT | Yes | Yes |
| Michigan | MI | Yes | Yes |
| Missouri | MO | Yes | Yes |
| New Jersey | NJ | Yes | Yes |
| New York | NY | Yes | Yes |
| Ohio | OH | Yes | Yes |
| Oregon | OR | Yes (2) | Yes (2) |
| Pennsylvania | PA | Yes | Yes |
| South Carolina | SC | Yes | Yes |
| Tennessee | TN | Yes | Yes |
| Virginia | VA | Yes | Yes |

**Excluded:** CA (target), IA/IN (consortium data), NC (short history), LA/RI/WI (EVE-only)

---

## Aggregate File Format

Each aggregate CSV has 45 columns:
```
date, CA_QS1, CA_QS2, CA_QS3, CA_QS4, QS1_0, QS1_1, ..., QS4_9
```

- **date**: Draw date (YYYY-MM-DD)
- **CA_QS1-4**: California's actual results (target)
- **QS1_0 to QS4_9**: Count of states that drew each digit (0-9) for each position (1-4)

---

## Requirements

- Python 3.10+
- Chrome browser (for Selenium)
- Required packages: `selenium`, `beautifulsoup4`, `pandas`, `numpy`

Install dependencies:
```bash
pip install selenium beautifulsoup4 pandas numpy
```

---

## Troubleshooting

### Chrome Issues
Make sure Chrome is installed and chromedriver is in your PATH or matches your Chrome version.

### Scraper Fails
The website may have changed structure. Check `src/utilities/scraper_4digit.py` for updates needed.

### Missing Data
If a state's data is missing, check `data/lotterypost_dat_lookup.csv` for the URL mapping.

---

## Project History

This project began as the "California Daily 4 Divination Project" - a research effort to find predictive patterns in lottery data. After extensive analysis (classical ML + quantum VQC), the research concluded definitively that the lottery is cryptographically random with no exploitable patterns.

The project has been converted to a data maintenance utility for anyone interested in maintaining historical Pick-4 lottery data.

---

## License

For educational and research purposes only.
