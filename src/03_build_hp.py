"""Build the firm-year Hoberg-Phillips panel used in the analysis.

Inputs (see data/raw/hoberg_phillips/README.md for how to obtain them):
    data/raw/hoberg_phillips/VertInteg.txt           (gvkey, year, vertinteg)
    data/raw/hoberg_phillips/VertNetwork_10gran.txt  (year, gvkey1, gvkey2, vertscore)
    data/raw/hoberg_phillips/tnic3_data.txt          (year, gvkey1, gvkey2, score)

Output:
    data/processed/hp_firm_panel.parquet  (gvkey, year, vertinteg)

The only HP score used in the analysis is the firm-level vertical-integration
score (vertinteg). The two large network files contribute no score; they are
needed because they define the firm-year UNIVERSE: an observation is in the
sample only if the firm appears as gvkey1 in the HP vertical or horizontal
(TNIC3) pair network that year (self-pairs excluded). Both networks matter --
a sizable share of sample firm-years appear only in the TNIC3 network.
Firm-years present in VertInteg.txt without any network pair are NOT part of
the thesis sample, so reading VertInteg.txt alone would not reproduce the
reported observation counts.

Usage: python src/03_build_hp.py
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HP_DIR = ROOT / "data/raw/hoberg_phillips"
OUT_FILE = ROOT / "data/processed/hp_firm_panel.parquet"

HP_VERTINTEG = HP_DIR / "VertInteg.txt"
HP_VERT_NETWORK = HP_DIR / "VertNetwork_10gran.txt"
HP_HORIZ_NETWORK = HP_DIR / "tnic3_data.txt"

# Panel years used downstream (VI enters lagged, so 1988-2019 covers the
# 1990-2019 estimation window with room on both ends)
YEARS = set(range(1988, 2020))

CHUNKSIZE = 5_000_000


def network_firm_years(path, label):
    """One chunked pass over a pair-network file; returns the unique
    (year, gvkey) combinations appearing as gvkey1 (self-pairs excluded)."""
    print(f"Scanning {label} for firm-year universe...")
    seen = set()
    chunks = pd.read_csv(path, sep='\t', chunksize=CHUNKSIZE,
                         usecols=['year', 'gvkey1', 'gvkey2'],
                         dtype={'year': 'int16', 'gvkey1': 'int32',
                                'gvkey2': 'int32'})
    for chunk in chunks:
        chunk = chunk[chunk['year'].isin(YEARS)]
        chunk = chunk[chunk['gvkey1'] != chunk['gvkey2']]
        seen.update(map(tuple, chunk[['year', 'gvkey1']].drop_duplicates().values))
    print(f"  {label}: {len(seen):,} firm-years")
    return seen


def load_firm_measures():
    """Load the firm-level vertical-integration score."""
    print("Loading firm-level HP measures...")

    df_vi = pd.read_csv(HP_VERTINTEG, sep='\t')
    df_vi.columns = df_vi.columns.str.lower()
    df_vi = df_vi[['gvkey', 'year', 'vertinteg']]
    print(f"  VertInteg: {len(df_vi):,} rows")
    return df_vi


def main():
    print("=" * 60)
    print("Stage 1c: Hoberg-Phillips firm-year panel")
    print("=" * 60)

    universe = (network_firm_years(HP_VERT_NETWORK, "vertical network") |
                network_firm_years(HP_HORIZ_NETWORK, "TNIC3 network"))
    hp_universe = pd.DataFrame(sorted(universe), columns=['year', 'gvkey'])
    print(f"Combined firm-year universe: {len(hp_universe):,}")

    measures = load_firm_measures()
    hp = hp_universe.merge(measures, on=['gvkey', 'year'], how='left')
    hp = hp.drop_duplicates(subset=['gvkey', 'year'])

    print(f"\nHP firm panel: {len(hp):,} firm-years, "
          f"{hp['gvkey'].nunique():,} firms, "
          f"years {hp['year'].min()}-{hp['year'].max()}")
    print(f"  with vertinteg: {hp['vertinteg'].notna().sum():,}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    hp.to_parquet(OUT_FILE, index=False)
    print(f"\nSaved: {OUT_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    exit(main())
