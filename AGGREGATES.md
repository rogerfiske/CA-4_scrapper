# Aggregate Files Documentation

## Overview

Three aggregate CSV files are generated from individual state lottery binary files, aligned to California's date range.

| File | States | Files | Expected Row Sum | Rows |
|------|--------|-------|------------------|------|
| `CA_4_predict_eve_aggregate.csv` | 20 | 21 | **84** | 6,421 |
| `CA_4_predict_mid_aggregate.csv` | 15 | 16 | **64** | 6,421 |
| `CA_4_predict_daily_aggregate.csv` | - | 37 | **148** | 6,421 |

---

## Column Structure (45 columns)

```
date, CA_QS1, CA_QS2, CA_QS3, CA_QS4, QS1_0, QS1_1, ..., QS1_9, QS2_0, ..., QS4_9
```

| Column(s) | Description |
|-----------|-------------|
| `date` | Draw date (M/D/YYYY format) |
| `CA_QS1` - `CA_QS4` | California target digits (0-9) - prediction target |
| `QS1_0` - `QS1_9` | Sum of states with digit 0-9 in position 1 |
| `QS2_0` - `QS2_9` | Sum of states with digit 0-9 in position 2 |
| `QS3_0` - `QS3_9` | Sum of states with digit 0-9 in position 3 |
| `QS4_0` - `QS4_9` | Sum of states with digit 0-9 in position 4 |

**Binary encoding:** Each state contributes exactly 4 "ones" per row (one per digit position).

---

## Row Sum Calculation

Each position's 10 columns should sum to the number of contributing states:
- `QS1_0 + QS1_1 + ... + QS1_9` = number of states with data for that date
- Total row sum = states × 4

---

## Data Quality

| Aggregate | Correct Rows | Accuracy | Notes |
|-----------|--------------|----------|-------|
| EVE | 6,369 / 6,421 | 99.2% | Minor gaps from holidays/start dates |
| MID | 6,339 / 6,421 | 98.7% | Minor gaps from holidays/start dates |

---

## State Start Date Issues

Not all states have data for the full CA date range (2008-05-19 to present). This causes row sums to be lower than expected on early dates.

### EVE Cohort (21 files)

| State | First Date | Days Before CA | Impact |
|-------|------------|----------------|--------|
| MA | 2002-01-01 | - | Full coverage |
| FL | 2002-01-01 | - | Full coverage |
| Most states | 2002-2003 | - | Full coverage |
| TN | 2005-04-18 | - | Full coverage |

**EVE has good coverage** - most states started before CA (2008-05-19).

### MID Cohort (16 files)

| State | First Date | Missing CA Dates | Impact |
|-------|------------|------------------|--------|
| MA | 2008-06-09 | 21 | Sum=60 for May 19 - Jun 8, 2008 |
| FL | 2008-05-19 | 0 | Full coverage |
| GA | varies | 47 | Sporadic early gaps |
| NJ | varies | 16 | Minor gaps |

**MID early dates affected** - MA started 3 weeks after CA, causing sum=60 instead of 64 for those dates.

### Dates with Reduced Sums

```
May 19 - Jun 8, 2008: MID sum = 60 (MA not yet started)
Various holidays: Both cohorts may have 1-2 states missing
```

---

## Standardization Options

To achieve 100% consistent row sums, consider:

1. **Truncate start date** - Start aggregates from 2008-06-09 (when MA started)
   - Loses 21 days of data
   - Guarantees consistent MID sums

2. **Flag incomplete rows** - Add column indicating contributing state count
   - Keeps all data
   - Allows filtering during analysis

3. **Impute missing values** - Fill gaps with expected distribution
   - Keeps all data
   - Introduces synthetic data

4. **Accept as-is** - Document known gaps
   - Current approach
   - 98.7%+ accuracy is sufficient for most analyses

---

## States by Cohort

### EVE (20 states, 21 files)
CT, DC, DE, FL, GA, IL, KY, MA, MD, ME_NH_VT, MI, MO, NJ, NY, OH, OR (×2), PA, SC, TN, VA

### MID (15 states, 16 files)
CT, DC, FL, GA, MA, MD, ME_NH_VT, MI, MO, NJ, NY, OH, OR (×2), PA, VA

### Excluded from MID (6-day lotteries)
DE, IL, KY, SC, TN — no/few Sunday midday draws

---

## Configuration Files

- `eve_sources.json` - EVE cohort file list and statistics
- `mid_sources.json` - MID cohort file list and statistics

---

*Generated: 2025-12-17*
