"""Build the two analysis panels by merging Compustat, Hoberg-Phillips and MPS.

Inputs (produced by scripts 01-03):
    data/processed/compustat_yearly.parquet
    data/processed/hp_firm_panel.parquet
    data/processed/mps_fiscal_year.parquet

Outputs:
    data/processed/panel_baseline.parquet / .csv
        Baseline sample (N = 96,569). Used by 05_baseline.R (Table 2,
        Table 3 columns 1-5) and the descriptive figures.
    data/processed/panel_outcomes.parquet / .csv
        Multi-outcome sample with the signed shock components
        (N = 96,564). Used by 06_alt_outcomes.R (Figure 1, Appendix B1),
        07_asymmetric.R (Table 3 column 6, Appendix B2) and
        08_quantile.R (Figure 2, Appendix B3).

The two samples differ only in that the baseline panel does not require
lagged log cash to be nonmissing at the sample-construction step (five
firm-years); the regressions include log cash as a control, so every
estimation sample is identical across the two panels.

Construction (mirrors the thesis exactly):
  - MPS alignment: each firm-year gets the fiscal-year shock matching its
    fiscal-year-end month (a June-FY firm's fiscal 2010 gets the Jul 2009 -
    Jun 2010 shock sum). Firm-years with no fiscal Q4 have an undefined
    year-end and drop out.
  - VI timing: Hoberg-Phillips measures are merged from year t-1
    (predetermined relative to the outcome year).
  - Sample filters: drop SIC 60-67 (finance/insurance/real estate),
    91-97 (public administration), 49 (utilities); require positive sales.
  - Growth windows: every change is a one-FISCAL-year log difference, kept
    only when the prior row is the immediately preceding fiscal year AND its
    year-end is 350-380 days earlier. This excludes gaps (firm exits and
    re-enters) and fiscal-year-end transitions (two "fiscal years" inside one
    calendar year).
  - Complete years: both the current and the prior fiscal year must have all
    four quarters, so each annual flow is a full-year sum and each growth
    rate a true twelve-month change.

Usage: python src/04_build_panels.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPUSTAT = ROOT / "data/processed/compustat_yearly.parquet"
HP_PANEL = ROOT / "data/processed/hp_firm_panel.parquet"
MPS_FISCAL = ROOT / "data/processed/mps_fiscal_year.parquet"
OUT_DIR = ROOT / "data/processed"

MONTH_MAP = {1: 'jan', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'may', 6: 'jun',
             7: 'jul', 8: 'aug', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'}

YEARS = range(1988, 2020)

WRDS_COLS = ['year', 'gvkey', 'fyear', 'n_quarters', 'has_q4', 'fy_end_month',
             'fy_end_date', 'sic', 'saleq', 'capxy', 'ppentq', 'mkvaltq',
             'dlcq', 'dlttq', 'cheq', 'oiadpq', 'xintq', 'cogsq', 'invtq',
             'rectq', 'xsgaq']


def load_inputs():
    print("Loading processed inputs...")
    wrds = pd.read_parquet(COMPUSTAT)
    wrds = wrds[wrds['year'].isin(YEARS)]
    wrds = wrds[[c for c in WRDS_COLS if c in wrds.columns]].copy()
    print(f"  Compustat: {len(wrds):,} firm-years, {wrds.gvkey.nunique():,} firms")

    hp = pd.read_parquet(HP_PANEL)
    print(f"  HP: {len(hp):,} firm-years, {hp.gvkey.nunique():,} firms")

    mps = pd.read_parquet(MPS_FISCAL)
    print(f"  MPS: {len(mps)} years ({mps.year.min()}-{mps.year.max()})")
    return hp, wrds, mps


def merge_datasets(hp, wrds, mps):
    """Merge HP (lagged) + Compustat + fiscal-year-aligned MPS."""
    print("\nMerging datasets...")

    df = wrds.copy()
    assert df.duplicated(['gvkey', 'fyear']).sum() == 0, \
        "Compustat yearly not unique on (gvkey, fyear)"
    print(f"  Compustat rows: {len(df):,}; with a defined FY-end (has_q4): "
          f"{int(df['has_q4'].sum()):,}")

    df = df.merge(mps, on='year', how='left')

    # Select the MPS column matching each firm's fiscal-year-end month
    for var in ['mps_orth', 'mps_pos', 'mps_neg', 'n_pos', 'n_neg']:
        df[var] = np.nan
    for fy_month in df['fy_end_month'].dropna().unique():
        fy_month = int(fy_month)
        m = MONTH_MAP[fy_month]
        mask = df['fy_end_month'] == fy_month
        for var, col in [('mps_orth', f"mps_fy_{m}"),
                         ('mps_pos', f"mps_pos_fy_{m}"),
                         ('mps_neg', f"mps_neg_fy_{m}"),
                         ('n_pos', f"n_pos_fy_{m}"),
                         ('n_neg', f"n_neg_fy_{m}")]:
            if col in df.columns:
                df.loc[mask, var] = df.loc[mask, col]
    n_mps = df['mps_orth'].notna().sum()
    print(f"  MPS assigned (fiscal-year aligned): {n_mps:,} obs "
          f"({100 * n_mps / len(df):.1f}%)")

    # VI (and the other HP measures) from year t-1: predetermined
    df['hp_merge_year'] = df['year'] - 1
    df = df.merge(hp, left_on=['gvkey', 'hp_merge_year'],
                  right_on=['gvkey', 'year'], how='inner',
                  suffixes=('', '_hp'))
    print(f"  After HP merge (VI from year t-1): {len(df):,} obs")

    drop_cols = ['year_hp', 'hp_merge_year']
    drop_cols += [c for c in df.columns if c.startswith(
        ('mps_fy_', 'mps_pos_fy_', 'mps_neg_fy_', 'n_pos_fy_', 'n_neg_fy_'))]
    return df.drop(columns=drop_cols, errors='ignore')


def apply_sample_filters(df):
    """Sample selection following Ottonello-Winberry (2020), Appendix A.1."""
    print("\nApplying sample filters...")
    n_start = len(df)
    df['sic_str'] = df['sic'].astype(str).str.zfill(4)
    df['sic2'] = df['sic_str'].str[:2]
    df = df[~df['sic2'].isin(['60', '61', '62', '63', '64', '65', '66', '67'])]
    df = df[~df['sic2'].isin(['91', '92', '93', '94', '95', '96', '97'])]
    df = df[df['sic2'] != '49']
    df = df[df['saleq'] > 0]
    print(f"  After filters: {len(df):,} obs (dropped {n_start - len(df):,})")
    return df


def create_variables(df):
    """Levels, one-fiscal-year changes, lagged controls, interactions."""
    print("\nCreating variables...")
    df = df.sort_values(['gvkey', 'fyear'])

    # Log levels
    df['log_sale'] = np.log(df['saleq'].clip(lower=1))
    df['log_ppent'] = np.log(df['ppentq'].clip(lower=1))
    df['log_capex'] = np.log(df['capxy'].clip(lower=0.1))
    df['log_cash'] = np.log(df['cheq'].clip(lower=1))
    df['log_size'] = df['log_sale']
    df['total_debt'] = df['dlttq'].fillna(0) + df['dlcq'].fillna(0)
    df['leverage'] = (df['total_debt'] / df['saleq'].clip(lower=1)).clip(upper=10)
    df['log_debt'] = np.log(df['total_debt'] + 1)
    df['log_cogs'] = np.log(df['cogsq'].clip(lower=1))
    df['log_invt'] = np.log(df['invtq'].clip(lower=1))
    df['log_oi'] = np.log(df['oiadpq'].clip(lower=0.1))
    df['log_xint'] = np.log(df['xintq'].clip(lower=0.01))
    df['log_rect'] = np.log(df['rectq'].clip(lower=1))

    # Clean ~12-month fiscal-year window
    df['fyear_prev'] = df.groupby('gvkey')['fyear'].shift(1)
    df['_fyend_dt'] = pd.to_datetime(df['fy_end_date'].astype('Int64').astype(str),
                                     format='%Y%m%d', errors='coerce')
    df['gap_days'] = (df['_fyend_dt'] - df.groupby('gvkey')['_fyend_dt'].shift(1)).dt.days
    df['annual_change'] = ((df['fyear'] - df['fyear_prev'] == 1) &
                           df['gap_days'].between(350, 380))

    # Outcome changes (diff to the prior fiscal-year row)
    df['sale_growth'] = df.groupby('gvkey')['log_sale'].diff()
    df['d_log_debt'] = df.groupby('gvkey')['log_debt'].diff()
    df['d_leverage'] = df.groupby('gvkey')['leverage'].diff()
    df['d_log_cogs'] = df.groupby('gvkey')['log_cogs'].diff()
    df['d_log_invt'] = df.groupby('gvkey')['log_invt'].diff()
    df['d_log_capex'] = df.groupby('gvkey')['log_capex'].diff()
    df['d_log_ppent'] = df.groupby('gvkey')['log_ppent'].diff()
    df['d_log_oi'] = df.groupby('gvkey')['log_oi'].diff()
    df['d_log_xint'] = df.groupby('gvkey')['log_xint'].diff()
    df['d_log_rect'] = df.groupby('gvkey')['log_rect'].diff()

    # Lagged controls + prior-year quarter count
    for var in ['log_size', 'leverage', 'log_ppent', 'log_cash']:
        df[f'{var}_lag'] = df.groupby('gvkey')[var].shift(1)
    df['nq_lag'] = df.groupby('gvkey')['n_quarters'].shift(1)

    # Null every change/lag whose window is not a clean ~12-month fiscal year
    outcomes = ['sale_growth', 'd_log_debt', 'd_leverage', 'd_log_cogs',
                'd_log_invt', 'd_log_capex', 'd_log_ppent', 'd_log_oi',
                'd_log_xint', 'd_log_rect']
    lags = ['nq_lag', 'log_size_lag', 'leverage_lag', 'log_ppent_lag',
            'log_cash_lag']
    bad = ~df['annual_change']
    for c in outcomes + lags:
        df.loc[bad, c] = np.nan
    df = df.drop(columns=['_fyend_dt'])

    # VI already merged from year t-1
    df['vi_lag'] = df['vertinteg']
    df['mps_x_vi'] = df['mps_orth'] * df['vi_lag']
    df['mps_pos_x_vi'] = df['mps_pos'] * df['vi_lag']
    df['mps_neg_x_vi'] = df['mps_neg'] * df['vi_lag']
    return df


def finalize(df, required, label):
    """Drop missing required vars; require complete current + prior FY."""
    out = df.dropna(subset=required)
    out = out[(out['n_quarters'] == 4) & (out['nq_lag'] == 4)]
    print(f"  {label}: {len(out):,} obs, {out.gvkey.nunique():,} firms, "
          f"years {out.year.min()}-{out.year.max()}")
    return out


def main():
    print("=" * 60)
    print("Stage 1d: Analysis panels")
    print("=" * 60)

    hp, wrds, mps = load_inputs()
    df = merge_datasets(hp, wrds, mps)
    df = apply_sample_filters(df)
    df = create_variables(df)

    print("\nFinalizing samples...")
    # Baseline sample: the log-cash control is in the regressions but is not
    # required at the construction step (matches the thesis exactly)
    panel_baseline = finalize(
        df,
        required=['mps_orth', 'vi_lag', 'mps_x_vi', 'sic2', 'sale_growth',
                  'log_size_lag', 'leverage_lag', 'log_ppent_lag'],
        label="panel_baseline")

    # Multi-outcome sample: all controls and the signed shock components
    panel_outcomes = finalize(
        df,
        required=['mps_orth', 'mps_x_vi', 'mps_pos', 'mps_neg', 'vi_lag',
                  'mps_pos_x_vi', 'mps_neg_x_vi', 'sic2', 'log_size_lag',
                  'leverage_lag', 'log_ppent_lag', 'log_cash_lag'],
        label="panel_outcomes")

    outcome_cols = ['sale_growth', 'd_log_debt', 'd_leverage', 'd_log_cogs',
                    'd_log_invt', 'd_log_capex', 'd_log_ppent', 'd_log_oi',
                    'd_log_xint', 'd_log_rect']
    print("\n  panel_outcomes outcome coverage:")
    for out in outcome_cols:
        n = panel_outcomes[out].notna().sum()
        print(f"    {out:13s}: {n:>6,} obs ({100 * n / len(panel_outcomes):5.1f}%)")

    for name, panel in [("panel_baseline", panel_baseline),
                        ("panel_outcomes", panel_outcomes)]:
        panel.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
        panel.to_csv(OUT_DIR / f"{name}.csv", index=False)
        print(f"\nSaved: data/processed/{name}.parquet / .csv")
    return 0


if __name__ == "__main__":
    exit(main())
