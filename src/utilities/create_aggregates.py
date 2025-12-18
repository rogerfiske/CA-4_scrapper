"""
Phase 4: Binary File Alignment and Aggregation

Creates aligned binary files and aggregate CSVs for TODeve and TODmid cohorts.
- Aligns all files to CA's date range (6,414 draws: 2008-05-19 to 2025-12-10)
- Uses ONLY the 20 common states present in BOTH cohorts
- Excludes CA from aggregation (it's the prediction target)
- Excludes IA and IN (consortium data integrity issue - shared draws with IL)
- Excludes NC from TODeve cohort (short history)
- Excludes LA, RI, WI (only in TODeve, not in TODmid)
- Aggregates binary columns by summing across states for each date
- Includes CA actual results in columns B-E (CA_QS1, CA_QS2, CA_QS3, CA_QS4)

Data Integrity Note:
  - IA/IL shared identical draws 2009-2014
  - IA/IN shared identical draws 2017-2022
  - Keeping IL only, removing IA and IN to ensure independent samples

Output format (45 columns):
  date, CA_QS1, CA_QS2, CA_QS3, CA_QS4, QS1_0, QS1_1, ..., QS4_9
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Paths
PROJECT_ROOT = Path(r"C:\Users\Minis\CascadeProjects\CA-4_scrapper")
RAW_DIR = PROJECT_ROOT / "data" / "raw"
AGGREGATES_DIR = PROJECT_ROOT / "data" / "aggregates"

# MID cohort start date (MA Midday started 2008-06-09)
# All dates before this have incomplete MID data
MID_START_DATE = '2008-06-09'

# Binary column names
BINARY_COLS = ['date'] + [f'QS{pos}_{digit}' for pos in range(1, 5) for digit in range(10)]

# ============================================================================
# STATE CONFIGURATION FOR EVE AND MID COHORTS
# ============================================================================
# EVE cohort: All 20 common states (all draw 7 days/week in evening)
# MID cohort: 15 states only (excludes 6-day states with no Sunday midday draws)
#
# Excluded from both:
#   - CA: Prediction target (not used in aggregation)
#   - IA: Consortium hub (shared draws with IL 2009-2014, with IN 2017-2022)
#   - IN: Consortium member (shared draws with IA 2017-2022)
#   - NC: Short history
#   - LA, RI, WI: Only in TODeve, not in TODmid
#
# Additionally excluded from MID only (6-day lotteries - no Sunday midday):
#   - SC: 0% Sunday midday draws
#   - TN: 0% Sunday midday draws
#   - DE: 1.5% Sunday midday draws
#   - KY: 6.4% Sunday midday draws
#   - IL: 10% Sunday midday draws
# ============================================================================

# 6-day states to exclude from MID cohort (no/few Sunday midday draws)
SIX_DAY_STATES_MID = {'SC', 'TN', 'DE', 'KY', 'IL'}

# EVE cohort: 20 states, 21 files (OR has 2 draws) -> expected sum = 84
COMMON_STATES_EVE = {
    'CT', 'DC', 'DE', 'FL', 'GA', 'IL', 'KY', 'MA', 'MD', 'ME_NH_VT',
    'MI', 'MO', 'NJ', 'NY', 'OH', 'OR', 'PA', 'SC', 'TN', 'VA'
}

# MID cohort: 15 states, 16 files (OR has 2 draws) -> expected sum = 64
COMMON_STATES_MID = COMMON_STATES_EVE - SIX_DAY_STATES_MID

# Keep COMMON_STATES for backward compatibility (used by manifest updates)
COMMON_STATES = COMMON_STATES_EVE

# States to exclude (for documentation and verification)
EXCLUDED_STATES = {
    'CA',       # Prediction target
    'IA',       # Consortium hub (IL/IA 2009-2014, IA/IN 2017-2022)
    'IN',       # Consortium member (IA/IN 2017-2022)
    'NC',       # Short history
    'LA',       # TODeve only
    'RI',       # TODeve only
    'WI',       # TODeve only
    'WV',       # 6 days/week (excluded at cohort creation)
}


def load_ca_dates():
    """Load CA binary file and extract date range, plus CA original for actuals."""
    ca_binary_path = RAW_DIR / "CA_Daily_4_dat_binary.csv"
    ca_original_path = RAW_DIR / "CA_Daily_4_dat.csv"

    # Load binary for date reference
    ca_binary_df = pd.read_csv(ca_binary_path)
    ca_binary_df['date'] = pd.to_datetime(ca_binary_df['date'])

    # Load original for actual digit values
    ca_original_df = pd.read_csv(ca_original_path)
    ca_original_df['date'] = pd.to_datetime(ca_original_df['date'])

    # Rename columns to CA_QS1, CA_QS2, etc.
    ca_original_df = ca_original_df.rename(columns={
        'QS1': 'CA_QS1',
        'QS2': 'CA_QS2',
        'QS3': 'CA_QS3',
        'QS4': 'CA_QS4'
    })

    print(f"CA date range: {ca_binary_df['date'].min()} to {ca_binary_df['date'].max()}")
    print(f"CA total draws: {len(ca_binary_df)}")

    return set(ca_binary_df['date']), ca_binary_df, ca_original_df


def get_binary_filename(original_filename):
    """Convert original filename to binary filename."""
    # e.g., "DC-4_TODeve_750pm_dat" -> "DC-4_TODeve_750pm_dat_binary.csv"
    return f"{original_filename}_binary.csv"


def align_binary_file(filename, ca_dates):
    """
    Load a binary file from raw and filter to CA dates.
    Returns the aligned dataframe (no file saved - intermediate data only).
    """
    binary_filename = get_binary_filename(filename)
    input_path = RAW_DIR / binary_filename

    if not input_path.exists():
        print(f"  WARNING: {binary_filename} not found, skipping")
        return None

    df = pd.read_csv(input_path)
    df['date'] = pd.to_datetime(df['date'])

    original_count = len(df)

    # Filter to CA dates only
    df_aligned = df[df['date'].isin(ca_dates)].copy()
    df_aligned = df_aligned.sort_values('date').reset_index(drop=True)

    aligned_count = len(df_aligned)

    print(f"  {filename}: {original_count} -> {aligned_count} ({aligned_count/original_count*100:.1f}%)")

    return df_aligned


def aggregate_binary_files(dataframes, ca_dates, ca_original_df):
    """
    Aggregate binary columns across all dataframes.
    Only includes dates that exist in CA's dataset.
    Includes CA actual results in columns B-E (CA_QS1, CA_QS2, CA_QS3, CA_QS4).
    Returns a dataframe with CA dates, CA actuals, and summed binary columns.
    """
    binary_cols = [f'QS{pos}_{digit}' for pos in range(1, 5) for digit in range(10)]

    # Create base dataframe with CA dates only, indexed by date for efficient summing
    ca_dates_sorted = sorted(list(ca_dates))
    result = pd.DataFrame({'date': ca_dates_sorted})
    result = result.set_index('date')

    # Initialize binary columns to zero
    for col in binary_cols:
        result[col] = 0.0

    # Sum across all state dataframes
    for state_df in dataframes:
        if state_df is None:
            continue

        # Filter state_df to only CA dates and dedupe (in case state has duplicates)
        state_filtered = state_df[state_df['date'].isin(ca_dates)].copy()
        state_filtered = state_filtered.drop_duplicates(subset=['date'], keep='first')
        state_filtered = state_filtered.set_index('date')

        # Add values where dates match
        for col in binary_cols:
            if col in state_filtered.columns:
                # Reindex to match result and fill missing with 0
                state_col = state_filtered[col].reindex(result.index, fill_value=0)
                result[col] = result[col] + state_col

    # Reset index to make date a column again
    result = result.reset_index()

    # Merge CA actuals (CA_QS1, CA_QS2, CA_QS3, CA_QS4) into columns B-E
    ca_actuals = ca_original_df[['date', 'CA_QS1', 'CA_QS2', 'CA_QS3', 'CA_QS4']].copy()
    ca_actuals = ca_actuals.drop_duplicates(subset=['date'], keep='first')

    result = result.merge(ca_actuals, on='date', how='left')

    # Reorder columns: date, CA_QS1-4, then binary columns
    col_order = ['date', 'CA_QS1', 'CA_QS2', 'CA_QS3', 'CA_QS4'] + binary_cols
    result = result[col_order]

    return result


def process_cohort(cohort_name, manifest, ca_dates, ca_binary_df, ca_original_df):
    """
    Process a cohort: align binary files to CA dates and aggregate.
    EVE uses all 20 states (21 files) -> expected sum = 84
    MID uses 15 states (16 files, excludes 6-day states) -> expected sum = 64
    Includes CA actuals in columns B-E of output.
    """
    # Select appropriate state set for this cohort
    if cohort_name == 'todeve':
        allowed_states = COMMON_STATES_EVE
        expected_sum = 84  # 21 files × 4
    else:  # todmid
        allowed_states = COMMON_STATES_MID
        expected_sum = 64  # 16 files × 4

    print(f"\n{'='*60}")
    print(f"Processing {cohort_name.upper()} Cohort")
    print(f"{'='*60}")
    print(f"Using state filter: {len(allowed_states)} states")
    print(f"States: {sorted(allowed_states)}")
    print(f"Expected row sum: {expected_sum}")

    dataframes = []
    processed_files = []
    skipped_files = []

    for file_info in manifest['files']:
        filename = file_info['file']
        state = file_info['state']

        # Only include files from allowed states
        if state not in allowed_states:
            reason = "6-day state (no Sunday midday)" if state in SIX_DAY_STATES_MID else "not in allowed states"
            skipped_files.append((filename, state, reason))
            print(f"  SKIPPING: {filename} (state={state}, {reason})")
            continue

        df_aligned = align_binary_file(filename, ca_dates)
        if df_aligned is not None:
            dataframes.append(df_aligned)
            processed_files.append({'file': filename, 'state': state})

    print(f"\nProcessed {len(dataframes)} files for aggregation")
    print(f"Skipped {len(skipped_files)} files")

    # Aggregate (includes CA actuals in columns B-E)
    print("\nAggregating binary columns with CA actuals...")
    aggregate_df = aggregate_binary_files(dataframes, ca_dates, ca_original_df)

    # Truncate MID to June 9, 2008 (when MA Midday started)
    if cohort_name == 'todmid':
        aggregate_df['date'] = pd.to_datetime(aggregate_df['date'])
        before_count = len(aggregate_df)
        aggregate_df = aggregate_df[aggregate_df['date'] >= MID_START_DATE].copy()
        after_count = len(aggregate_df)
        print(f"\nTruncated MID to {MID_START_DATE}: {before_count} -> {after_count} rows")

    # Save aggregate file
    if cohort_name == 'todeve':
        output_filename = "CA_4_predict_eve_aggregate.csv"
    else:
        output_filename = "CA_4_predict_mid_aggregate.csv"

    output_path = AGGREGATES_DIR / output_filename
    # Format dates as M/D/YYYY before saving (cross-platform)
    aggregate_df['date'] = pd.to_datetime(aggregate_df['date']).apply(
        lambda x: f"{x.month}/{x.day}/{x.year}"
    )
    aggregate_df.to_csv(output_path, index=False)

    print(f"\nAggregate saved to: {output_path}")
    print(f"Aggregate shape: {aggregate_df.shape}")
    print(f"Date range: {aggregate_df['date'].min()} to {aggregate_df['date'].max()}")

    # Show sample of aggregated values
    sample_cols = ['QS1_0', 'QS1_5', 'QS2_3', 'QS3_7', 'QS4_9']
    print(f"\nSample aggregate sums (row 0):")
    for col in sample_cols:
        print(f"  {col}: {aggregate_df[col].iloc[0]}")

    return aggregate_df, processed_files


def create_daily_aggregate(eve_aggregate, mid_aggregate):
    """
    Combine EVE and MID aggregates by summing their binary columns.
    CA actuals remain unchanged (same in both).
    Truncates to MID_START_DATE since MID data is incomplete before then.
    """
    binary_cols = [f'QS{pos}_{digit}' for pos in range(1, 5) for digit in range(10)]

    # Convert dates for filtering
    eve_aggregate = eve_aggregate.copy()
    eve_aggregate['date'] = pd.to_datetime(eve_aggregate['date'])

    # Truncate EVE to MID start date for alignment
    eve_truncated = eve_aggregate[eve_aggregate['date'] >= MID_START_DATE].copy()

    # Start with truncated EVE aggregate as base
    daily = eve_truncated.copy()

    # Add MID aggregate values to binary columns (MID already truncated)
    mid_aggregate = mid_aggregate.copy()
    mid_aggregate['date'] = pd.to_datetime(mid_aggregate['date'])

    # Merge on date to align properly
    for col in binary_cols:
        mid_vals = mid_aggregate.set_index('date')[col]
        daily[col] = daily['date'].map(lambda d: mid_vals.get(d, 0)) + daily[col]

    # Format dates back to M/D/YYYY
    daily['date'] = daily['date'].apply(lambda x: f"{x.month}/{x.day}/{x.year}")

    return daily


def update_manifest_common_states(cohort_name, processed_files):
    """Update manifest to include only allowed states for this cohort."""
    # Map cohort names to source files and state sets
    source_files = {'todeve': 'eve_sources.json', 'todmid': 'mid_sources.json'}
    manifest_path = AGGREGATES_DIR / source_files[cohort_name]

    # Select appropriate state set
    if cohort_name == 'todeve':
        allowed_states = COMMON_STATES_EVE
        expected_sum = 84
    else:
        allowed_states = COMMON_STATES_MID
        expected_sum = 64

    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    original_count = len(manifest['files'])

    # Filter to only files in allowed states
    manifest['files'] = [f for f in manifest['files'] if f['state'] in allowed_states]
    new_count = len(manifest['files'])

    # Get unique states
    included_states = sorted(set(f['state'] for f in manifest['files']))

    # Update statistics
    manifest['statistics']['num_files'] = new_count
    manifest['statistics']['expected_row_sum'] = expected_sum
    manifest['modified'] = datetime.now().isoformat()

    if cohort_name == 'todeve':
        manifest['notes'] = (
            f"EVE cohort: {len(allowed_states)} states, {new_count} files, expected_sum={expected_sum}. "
            f"Excluded: CA (target), IA/IN (consortium), NC (short), LA/RI/WI (EVE-only). "
            f"States: {included_states}"
        )
    else:
        manifest['notes'] = (
            f"MID cohort: {len(allowed_states)} states, {new_count} files, expected_sum={expected_sum}. "
            f"Excluded: CA (target), IA/IN (consortium), NC (short), LA/RI/WI (EVE-only), "
            f"plus 6-day states (SC/TN/DE/KY/IL - no Sunday midday). "
            f"States: {included_states}"
        )

    # Save updated manifest (no backup needed)
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nUpdated {cohort_name} manifest: {original_count} -> {new_count} files")
    print(f"States included ({len(included_states)}): {included_states}")
    print(f"Expected row sum: {expected_sum}")
    return manifest


def main():
    print("="*70)
    print("Phase 4: Binary File Alignment and Aggregation (v3 - 7-Day States)")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nEVE cohort: {len(COMMON_STATES_EVE)} states -> expected sum = 84")
    print(f"  States: {sorted(COMMON_STATES_EVE)}")
    print(f"\nMID cohort: {len(COMMON_STATES_MID)} states -> expected sum = 64")
    print(f"  States: {sorted(COMMON_STATES_MID)}")
    print(f"\n6-day states excluded from MID: {sorted(SIX_DAY_STATES_MID)}")
    print(f"EXCLUDED_STATES: {sorted(EXCLUDED_STATES)}")

    # Load CA dates as reference and CA original for actuals
    print("\n--- Loading CA Reference Dates and Actuals ---")
    ca_dates, ca_binary_df, ca_original_df = load_ca_dates()

    # Load manifests
    with open(AGGREGATES_DIR / "eve_sources.json", 'r') as f:
        todeve_manifest = json.load(f)

    with open(AGGREGATES_DIR / "mid_sources.json", 'r') as f:
        todmid_manifest = json.load(f)

    # Process TODeve (filtered to COMMON_STATES only)
    eve_aggregate, eve_files = process_cohort('todeve', todeve_manifest, ca_dates, ca_binary_df, ca_original_df)

    # Process TODmid (filtered to COMMON_STATES only)
    mid_aggregate, mid_files = process_cohort('todmid', todmid_manifest, ca_dates, ca_binary_df, ca_original_df)

    # Update manifests to reflect COMMON_STATES only
    print("\n--- Updating manifests ---")
    update_manifest_common_states('todeve', eve_files)
    update_manifest_common_states('todmid', mid_files)

    # Count unique states
    eve_states = set(f['state'] for f in eve_files)
    mid_states = set(f['state'] for f in mid_files)

    # Create combined daily aggregate (EVE + MID)
    print("\n--- Creating Combined Daily Aggregate (EVE + MID) ---")
    daily_aggregate = create_daily_aggregate(eve_aggregate, mid_aggregate)
    daily_output_path = AGGREGATES_DIR / "CA_4_predict_daily_aggregate.csv"
    # Dates already formatted from EVE aggregate
    daily_aggregate.to_csv(daily_output_path, index=False)
    print(f"Daily aggregate saved to: {daily_output_path}")
    print(f"Daily aggregate shape: {daily_aggregate.shape}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"TODeve aggregate: {len(eve_files)} files from {len(eve_states)} states, {len(eve_aggregate)} rows, {eve_aggregate.shape[1]} columns")
    print(f"TODmid aggregate: {len(mid_files)} files from {len(mid_states)} states, {len(mid_aggregate)} rows, {mid_aggregate.shape[1]} columns")
    print(f"Daily aggregate: Combined (EVE + MID), {len(daily_aggregate)} rows, {daily_aggregate.shape[1]} columns")
    print(f"\nStates in EVE: {sorted(eve_states)}")
    print(f"States in MID: {sorted(mid_states)}")
    print(f"\nColumn format: date, CA_QS1, CA_QS2, CA_QS3, CA_QS4, QS1_0, ..., QS4_9")
    print(f"\nOutput files:")
    print(f"  - {AGGREGATES_DIR / 'CA_4_predict_eve_aggregate.csv'}")
    print(f"  - {AGGREGATES_DIR / 'CA_4_predict_mid_aggregate.csv'}")
    print(f"  - {AGGREGATES_DIR / 'CA_4_predict_daily_aggregate.csv'}")
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
