# Compustat quarterly data (WRDS)

Compustat is proprietary and cannot be redistributed. You need a WRDS
subscription (https://wrds-www.wharton.upenn.edu) with access to
**Compustat North America -- Fundamentals Quarterly** (`comp.fundq`).

## What to place here

Two CSV extracts from `comp.fundq` (or one file containing all the columns,
saved twice under both names):

| File | Required columns |
|---|---|
| `compustat_fundq_main.csv` | `gvkey`, `datadate`, `fyearq`, `fqtr`, `sic`, `saleq`, `cogsq`, `xsgaq`, `oiadpq`, `xintq`, `rectq`, `invtq`, `cheq`, `ppentq`, `mkvaltq`, `capxy` |
| `compustat_fundq_debt.csv` | `gvkey`, `datadate`, `fyearq`, `fqtr`, `dlcq`, `dlttq` |

The two-file split only mirrors how the original data pull happened; the
build script (`src/01_build_compustat.py`) merges them on
(`gvkey`, `datadate`, `fqtr`). Extra columns are ignored.

## Query settings

- Library/table: `comp.fundq`
- Date range: at least 1987-01 through 2020-12 (the panel uses fiscal years
  ending 1988-2019, and growth rates need the prior fiscal year)
- Company universe: the entire database (no company screens)
- Standard WRDS screens: `indfmt = 'INDL'`, `datafmt = 'STD'`,
  `popsrc = 'D'`, `consol = 'C'`
- `datadate` formatted as `YYYYMMDD` (the WRDS web query's "YYMMDDn8."
  date format; the build parses the first four characters as the year)

## Sanity check

After running `make data panels`, the build log should report a baseline
panel of **96,569** firm-year observations and **10,660** firms
(`data/processed/panel_baseline.parquet`). If your counts differ slightly,
the likely cause is a Compustat vintage difference (S&P restates data over
time); the thesis extract was pulled in January 2025.
