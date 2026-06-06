"""Build the fiscal-year Compustat panel from the raw WRDS quarterly extract.

Input (see data/raw/wrds/README.md for how to obtain it):
    data/raw/wrds/compustat_fundq_main.csv   (main quarterly extract)
    data/raw/wrds/compustat_fundq_debt.csv   (supplementary extract: dlcq, dlttq)

Output:
    data/processed/compustat_yearly.parquet  (one row per firm-fiscal-year)

Aggregation rules:
  - Flow variables are summed over the four FISCAL quarters of each fiscal year
    (group by fyearq), NOT over the calendar year of datadate -- summing by
    calendar year would mix two fiscal years for non-December firms.
  - Before summing, each fiscal year is deduplicated to one row per quarter:
    a fiscal-year-end change can tag the same fiscal quarter to two datadates,
    which a naive sum double-counts. We keep the latest datadate per
    (gvkey, fyearq, fqtr).
  - Stock (balance-sheet) and YTD variables are taken at the fiscal Q4
    snapshot, falling back to the last available quarter when there is no Q4.
  - The row's `year` label and `fy_end_month` come from the TRUE fiscal Q4
    datadate (`has_q4` flags fiscal years without a Q4; their year-end is
    undefined, so they cannot be matched to VI or a shock window and are
    dropped downstream). `year` = calendar year of the fiscal year-end, which
    is the key both the Hoberg-Phillips and the fiscal-year MPS merges use.

Usage: python src/01_build_compustat.py
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRDS_MAIN = ROOT / "data/raw/wrds/compustat_fundq_main.csv"
WRDS_DEBT = ROOT / "data/raw/wrds/compustat_fundq_debt.csv"
OUT_FILE = ROOT / "data/processed/compustat_yearly.parquet"

# Flow variables: SUM across the four fiscal quarters
FLOW_VARS = ['saleq', 'cogsq', 'xsgaq', 'oiadpq', 'xintq']

# Stock variables: fiscal Q4 snapshot
STOCK_VARS = ['rectq', 'invtq', 'dlcq', 'dlttq', 'cheq', 'ppentq', 'mkvaltq']

# Year-to-date variables: fiscal Q4 value (already cumulative)
YTD_VARS = ['capxy']

# Identifiers: fiscal Q4 snapshot
ID_COLS = ['sic']


def load_quarterly():
    """Load and merge the two WRDS quarterly extracts."""
    print("Loading WRDS quarterly extracts...")

    df_main = pd.read_csv(WRDS_MAIN, low_memory=False)
    print(f"  Main extract: {len(df_main):,} rows, {len(df_main.columns)} cols")

    df_debt = pd.read_csv(WRDS_DEBT, low_memory=False)
    print(f"  Debt extract: {len(df_debt):,} rows, {len(df_debt.columns)} cols")

    # Bring in the columns the main extract lacks (dlcq, dlttq)
    unique_cols = set(df_debt.columns) - set(df_main.columns)
    merge_keys = ['gvkey', 'datadate', 'fqtr']
    df = df_main.merge(df_debt[merge_keys + list(unique_cols)],
                       on=merge_keys, how='left')

    df['datadate_str'] = df['datadate'].astype(str)
    df['year'] = df['datadate_str'].str[:4].astype(int)
    df['fyear'] = df['fyearq']

    print(f"  Merged: {len(df):,} rows, {df['gvkey'].nunique():,} firms, "
          f"years {df['year'].min()}-{df['year'].max()}")
    return df


def aggregate_to_fiscal_year(df):
    """Aggregate quarterly rows to one row per firm-fiscal-year."""
    df = df.dropna(subset=['gvkey', 'fyear']).copy()

    # One row per (gvkey, fyear, fqtr): keep the latest datadate, i.e. the
    # quarter belonging to the 12 months ending at the fiscal year-end.
    df = df[df['fqtr'].isin([1, 2, 3, 4])].copy()
    df = df.sort_values('datadate').drop_duplicates(['gvkey', 'fyear', 'fqtr'],
                                                    keep='last')

    flow_cols = [c for c in FLOW_VARS if c in df.columns]
    snap_vars = [c for c in (STOCK_VARS + YTD_VARS + ID_COLS) if c in df.columns]

    # Flows: SUM over the (deduplicated) fiscal quarters
    df_flow = df.groupby(['gvkey', 'fyear'])[flow_cols].sum().reset_index()

    # Distinct fiscal quarters available per fiscal year
    n_quarters = (df.groupby(['gvkey', 'fyear'])['fqtr'].nunique()
                  .reset_index().rename(columns={'fqtr': 'n_quarters'}))

    # Stock / YTD / id + datadate: fiscal Q4 snapshot, fall back to last quarter
    q4 = df[df['fqtr'] == 4].copy()
    have_q4 = set(map(tuple, q4[['gvkey', 'fyear']].drop_duplicates().values))
    last = df.sort_values('datadate').drop_duplicates(['gvkey', 'fyear'], keep='last')
    last_no_q4 = last[~last.set_index(['gvkey', 'fyear']).index.isin(have_q4)]
    snap = (pd.concat([q4, last_no_q4], ignore_index=True)
            .sort_values('datadate').drop_duplicates(['gvkey', 'fyear'], keep='last'))
    snap = snap[['gvkey', 'fyear', 'datadate'] + snap_vars]

    # Merge keys from the TRUE fiscal year-end (the fqtr==4 datadate)
    fy_end = (q4.sort_values('datadate').drop_duplicates(['gvkey', 'fyear'], keep='last')
              [['gvkey', 'fyear', 'datadate']].rename(columns={'datadate': 'fy_end_date'}))

    annual = (df_flow.merge(snap, on=['gvkey', 'fyear'], how='inner')
              .merge(n_quarters, on=['gvkey', 'fyear'], how='left')
              .merge(fy_end, on=['gvkey', 'fyear'], how='left'))

    annual['has_q4'] = annual['fy_end_date'].notna()
    end = annual['fy_end_date'].where(annual['has_q4'], annual['datadate'])
    annual['year'] = (end.astype('int64').astype(str).str[:4]).astype(int)
    fyem = annual['fy_end_date'].astype('Int64').astype(str).str.zfill(8).str[4:6]
    annual['fy_end_month'] = pd.to_numeric(fyem, errors='coerce')

    keys = ['year', 'gvkey', 'fyear', 'n_quarters', 'has_q4', 'fy_end_month']
    cols = keys + [c for c in annual.columns if c not in keys]
    return annual[cols]


def main():
    print("=" * 60)
    print("Stage 1a: Compustat fiscal-year panel")
    print("=" * 60)

    df = load_quarterly()
    annual = aggregate_to_fiscal_year(df)

    print(f"\nFiscal-year panel: {len(annual):,} firm-fiscal-years, "
          f"{annual['gvkey'].nunique():,} firms")
    print(f"  Complete (4-quarter) fiscal years: {(annual['n_quarters'] == 4).sum():,}")
    print(f"  With a defined fiscal year-end (has_q4): {annual['has_q4'].sum():,}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    annual.to_parquet(OUT_FILE, index=False)
    print(f"\nSaved: {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    exit(main())
