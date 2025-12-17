# Claude Code Project Memory — CA-4 Lottery Scraper

## Project Identity
- **Name:** CA-4 Lottery Data Scraper
- **Type:** Data scraping and maintenance utility
- **User:** Roger
- **Primary Agent:** DataBot (Data Curator)

## Project Status
- **Type:** Data maintenance utility
- **Function:** Scrape and aggregate Pick-4 lottery data from US states
- **EVE Cohort:** 20 states (21 files) - all 7-day lotteries
- **MID Cohort:** 15 states (16 files) - 7-day lotteries only (6-day states excluded)
- **Data Quality:** 99%+ row integrity after 2025-12-17 fixes

## Quick Start Commands

### Full Update (Recommended)
```bash
python update_all.py
```

### Dry Run (Preview Only)
```bash
python update_all.py --dry-run
```

### Skip Scraping
```bash
python update_all.py --skip-scrape
```

## Data Structure

### States by Cohort

**EVE Cohort (20 states, 21 files):** All states draw 7 days/week in evening
- CT, DC, DE, FL, GA, IL, KY, MA, MD, ME_NH_VT, MI, MO, NJ, NY, OH, OR (x2), PA, SC, TN, VA

**MID Cohort (15 states, 16 files):** Only 7-day states (excludes 6-day lotteries)
- CT, DC, FL, GA, MA, MD, ME_NH_VT, MI, MO, NJ, NY, OH, OR (x2), PA, VA

**Excluded from MID (6-day states - no Sunday midday draws):**
- DE (1.5% Sunday), IL (10% Sunday), KY (6.4% Sunday), SC (0% Sunday), TN (0% Sunday)

**Excluded from both cohorts:**
- CA (target), IA/IN (consortium data), NC (short history), LA/RI/WI (EVE-only), WV (6 days/week)

### File Formats
- **Original:** `date,QS1,QS2,QS3,QS4` (digit values 0-9)
- **Binary:** `date,QS1_0,...,QS1_9,QS2_0,...,QS4_9` (one-hot encoded, 41 columns)
- **Aggregate:** `date,CA_QS1,CA_QS2,CA_QS3,CA_QS4,QS1_0,...,QS4_9` (45 columns, summed across states)

### Output Files
| File | Files | Expected Row Sum | Description |
|------|-------|------------------|-------------|
| `CA_4_predict_eve_aggregate.csv` | 21 | 84 | Evening draws (20 states, OR has 2 draws) |
| `CA_4_predict_mid_aggregate.csv` | 16 | 64 | Midday draws (15 states, OR has 2 draws) |
| `CA_4_predict_daily_aggregate.csv` | 37 | 148 | Combined EVE + MID |
| `c-4_RESULTS.txt` | - | - | CA results (oldest first) |

### Data Integrity
Each state contributes 4 binary "1"s per row (one per digit position). Row sums should equal:
- **EVE:** 21 files × 4 = **84** (99.2% of rows)
- **MID:** 16 files × 4 = **64** (98.7% of rows)
- **DAILY:** 37 files × 4 = **148**

Remaining ~1% gaps are due to state start dates (e.g., MA started 2008-06-09) and minor holidays.

## Project Structure
```
CA-4_scrapper/
├── data/
│   ├── raw/                              # Source + binary CSV files
│   │   ├── CA_Daily_4_dat.csv            # California reference (target)
│   │   ├── *_TODmid_*.csv                # Midday draws (21 files, 20 states)
│   │   ├── *_TODeve_*.csv                # Evening draws (21 files, 20 states)
│   │   └── *_binary.csv                  # One-hot encoded versions
│   ├── aggregates/                       # Output directory
│   │   ├── CA_4_predict_eve_aggregate.csv   # Evening aggregate (21 files, sum=84)
│   │   ├── CA_4_predict_mid_aggregate.csv   # Midday aggregate (16 files, sum=64)
│   │   ├── CA_4_predict_daily_aggregate.csv # Combined aggregate (37 files, sum=148)
│   │   ├── eve_sources.json                 # Evening cohort configuration
│   │   └── mid_sources.json                 # Midday cohort configuration
│   ├── c-4_RESULTS.txt                   # CA results reference
│   └── lotterypost_dat_lookup.csv        # URL mappings
├── src/utilities/
│   ├── scraper_4digit.py                 # Web scraper
│   ├── csv_to_binary.py                  # Binary converter
│   └── create_aggregates.py              # Aggregate generator (v3 - 7-day states)
├── update_all.py                         # Master update script
├── fix_scraping_errors.py                # One-time fix for missing draws
├── README.md                             # User documentation
└── CLAUDE.md                             # This file
```

## Data Flow
```
data/raw/*_dat.csv          → scraper_4digit.py updates from lotterypost.com
       ↓
data/raw/*_binary.csv       → csv_to_binary.py converts to one-hot encoding
       ↓
data/aggregates/*.csv       → create_aggregates.py aligns to CA dates & aggregates
```

## Scripts

### update_all.py
Master script that runs the complete pipeline:
1. Scrapes new results from lotterypost.com
2. Regenerates binary CSV files
3. Regenerates aggregate CSV files
4. Updates c-4_RESULTS.txt

### scraper_4digit.py
Scrapes lottery results from lotterypost.com using Selenium.
- Reads URLs from `data/lotterypost_dat_lookup.csv`
- Updates CSV files with new draws
- Automatically triggers binary regeneration

### csv_to_binary.py
Converts original CSV files to one-hot encoded binary format.

### create_aggregates.py
Creates aggregate files from individual state binary files (v3 - 7-day states).
- Aligns all files to CA's date range (2008-05-19 to present)
- Excludes CA from aggregation (it's the target)
- **EVE:** Uses all 20 states (21 files) - expected row sum = 84
- **MID:** Uses 15 states (16 files) - excludes 6-day states for consistent Sunday data
- **DAILY:** Combines EVE + MID - expected row sum = 148

## BMAD Agent
- **DataBot** — Data Curator (`/bmad:custom:agents:data-curator`)

## Important Paths
- **Project root:** `C:\Users\Minis\CascadeProjects\CA-4_scrapper`
- **Source data:** `data/raw/` (43 source CSVs + 43 binary CSVs)
- **Aggregates:** `data/aggregates/` (3 output CSVs + 2 config JSONs)
- **Scraper:** `src/utilities/scraper_4digit.py`

## Requirements
- Python 3.10+
- Chrome browser (for Selenium)
- Packages: `selenium`, `beautifulsoup4`, `pandas`, `numpy`

## Data Quality Fixes (2025-12-17)

### Scraping Errors Fixed
12 missing draws were identified and added to source files:
- DC 2008-09-15, VA 2008-11-20, VA 2011-06-08, DE 2010-02-12
- NJ 2012-10-30, NJ 2012-10-31 (Hurricane Sandy - draws still occurred)
- OR 1PM 2017-11-27, OR 4PM 2017-11-27, OR 1PM 2021-07-13, OR 4PM 2021-07-13
- MI 2018-01-17, CT 2018-05-03

### 6-Day States Removed from MID
Five states with no/few Sunday midday draws were excluded from MID aggregation:
- SC (0% Sunday), TN (0% Sunday), DE (1.5%), KY (6.4%), IL (10%)

This ensures consistent row sums across all days including Sundays.

## Project History
This project began as the "California Daily 4 Divination Project" - a research effort to find predictive patterns in lottery data. After extensive analysis (classical ML + quantum VQC), the research concluded that CA Daily 4 is cryptographically random with no exploitable patterns.

The project has been converted to a data maintenance utility for maintaining historical Pick-4 lottery data.
