"""Build fiscal-year-aligned monetary-policy shocks from the Bauer-Swanson data.

Input (see data/raw/bauer_swanson/README.md):
    data/raw/bauer_swanson/monetary-policy-surprises-data.xlsx
        sheet "FOMC (update 2023)", columns Date, MPS, MPS_ORTH

Output:
    data/processed/mps_monthly.parquet      (monthly aggregation)
    data/processed/mps_fiscal_year.parquet  (12-month sums ending in each
                                             possible fiscal-year-end month;
                                             one column block per month)

Construction:
  1. Each FOMC-meeting surprise gets an Ottonello-Winberry timing weight,
     w = (days of its calendar month remaining on the announcement day) /
     (days in the month). A shock early in the month has more of the period
     left to act, so it gets a weight near one.
  2. Weighted surprises are summed within each calendar month. The positive
     (tightening) and negative (easing) parts are also accumulated separately
     BEFORE any aggregation, so the signed components decompose the within-
     period shock path rather than the period total.
  3. For each possible fiscal-year-end month M (Jan..Dec), the fiscal-year
     shock for year Y is the rolling 12-month sum ending in month M of year Y.
     A firm with fiscal year ending in month M is later matched to the
     mps_fy_<M> column (script 04).

Usage: python src/02_build_mps.py
"""

import calendar
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data/raw/bauer_swanson/monetary-policy-surprises-data.xlsx"
OUT_DIR = ROOT / "data/processed"

MONTH_NAMES = {1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'may', 6: 'jun',
               7: 'jul', 8: 'aug', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'}


def load_fomc():
    """Load the FOMC-meeting-level surprises."""
    df = pd.read_excel(RAW_FILE, sheet_name='FOMC (update 2023)')
    df['year'] = df['Date'].dt.year
    df['month'] = df['Date'].dt.month
    print(f"Loaded {len(df)} FOMC meetings ({df['year'].min()}-{df['year'].max()})")
    return df[['Date', 'year', 'month', 'MPS', 'MPS_ORTH']].copy()


def ow_weight_monthly(date, year, month):
    """Ottonello-Winberry weight: share of the month on/after the meeting."""
    days_in_month = calendar.monthrange(year, month)[1]
    days_remaining = days_in_month - date.day + 1
    return days_remaining / days_in_month


def aggregate_monthly(fomc):
    """Aggregate meeting surprises to calendar months (full year-month grid)."""
    print("\nAggregating to monthly level...")
    fomc = fomc.copy()

    fomc['ow_weight'] = fomc.apply(
        lambda row: ow_weight_monthly(row['Date'], row['year'], row['month']),
        axis=1)
    fomc['mps_orth_weighted'] = fomc['MPS_ORTH'] * fomc['ow_weight']

    # Signed components, split at the MEETING level before aggregation
    fomc['mps_orth_pos'] = fomc['ow_weight'] * fomc['MPS_ORTH'].clip(lower=0)
    fomc['mps_orth_neg'] = fomc['ow_weight'] * fomc['MPS_ORTH'].clip(upper=0)
    fomc['is_pos'] = (fomc['MPS_ORTH'] > 0).astype(int)
    fomc['is_neg'] = (fomc['MPS_ORTH'] < 0).astype(int)

    monthly = fomc.groupby(['year', 'month']).agg(
        mps_orth_sum=('MPS_ORTH', 'sum'),
        mps_orth_ow=('mps_orth_weighted', 'sum'),
        mps_orth_pos=('mps_orth_pos', 'sum'),
        mps_orth_neg=('mps_orth_neg', 'sum'),
        n_pos=('is_pos', 'sum'),
        n_neg=('is_neg', 'sum'),
        n_meetings=('Date', 'count'),
    ).reset_index()

    # Full year-month grid; months with no meeting carry a zero shock
    years = range(fomc['year'].min(), fomc['year'].max() + 1)
    full_grid = pd.DataFrame([{'year': y, 'month': m}
                              for y in years for m in range(1, 13)])
    monthly = full_grid.merge(monthly, on=['year', 'month'], how='left').fillna(0)
    for c in ['n_pos', 'n_neg', 'n_meetings']:
        monthly[c] = monthly[c].astype(int)

    print(f"  {len(monthly)} year-month observations")
    return monthly


def create_fiscal_year_mps(monthly):
    """Rolling 12-month sums ending in each possible fiscal-year-end month."""
    print("\nCreating fiscal-year aligned MPS...")
    monthly = monthly.sort_values(['year', 'month']).reset_index(drop=True)
    monthly['date'] = pd.to_datetime(monthly['year'].astype(str) + '-' +
                                     monthly['month'].astype(str).str.zfill(2) + '-01')
    monthly = monthly.set_index('date')

    roll = {
        'mps': monthly['mps_orth_ow'].rolling(12, min_periods=12).sum(),
        'mps_pos': monthly['mps_orth_pos'].rolling(12, min_periods=12).sum(),
        'mps_neg': monthly['mps_orth_neg'].rolling(12, min_periods=12).sum(),
        'n_pos': monthly['n_pos'].rolling(12, min_periods=12).sum(),
        'n_neg': monthly['n_neg'].rolling(12, min_periods=12).sum(),
    }

    results = []
    for fy_end_month in range(1, 13):
        m = MONTH_NAMES[fy_end_month]
        fy = monthly[monthly.index.month == fy_end_month].copy()
        fy[f'mps_fy_{m}'] = roll['mps'].loc[fy.index]
        fy[f'mps_pos_fy_{m}'] = roll['mps_pos'].loc[fy.index]
        fy[f'mps_neg_fy_{m}'] = roll['mps_neg'].loc[fy.index]
        fy[f'n_pos_fy_{m}'] = roll['n_pos'].loc[fy.index]
        fy[f'n_neg_fy_{m}'] = roll['n_neg'].loc[fy.index]
        fy['year'] = fy.index.year  # fiscal year label = calendar year of FY end
        keep = ['year', f'mps_fy_{m}', f'mps_pos_fy_{m}', f'mps_neg_fy_{m}',
                f'n_pos_fy_{m}', f'n_neg_fy_{m}']
        results.append(fy[keep].reset_index(drop=True))

    fiscal = results[0]
    for r in results[1:]:
        fiscal = fiscal.merge(r, on='year', how='outer')
    fiscal = fiscal.sort_values('year').reset_index(drop=True)

    print(f"  {len(fiscal)} fiscal years x 12 fiscal-year-end months")
    return fiscal


def main():
    print("=" * 60)
    print("Stage 1b: Bauer-Swanson MPS, fiscal-year aligned")
    print("=" * 60)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fomc = load_fomc()
    monthly = aggregate_monthly(fomc)
    fiscal = create_fiscal_year_mps(monthly)

    monthly.to_parquet(OUT_DIR / "mps_monthly.parquet", index=False)
    fiscal.to_parquet(OUT_DIR / "mps_fiscal_year.parquet", index=False)
    print(f"\nSaved: data/processed/mps_monthly.parquet")
    print(f"Saved: data/processed/mps_fiscal_year.parquet")

    sample = fiscal[(fiscal['year'] >= 2009) & (fiscal['year'] <= 2011)]
    print("\nSample (2009-2011, Dec / Jun fiscal-year ends):")
    print(sample[['year', 'mps_fy_dec', 'mps_fy_jun']].to_string(index=False))
    return 0


if __name__ == "__main__":
    exit(main())
