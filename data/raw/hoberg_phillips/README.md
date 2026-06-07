# Hoberg-Phillips data

All three files are freely available (after registration) from the
Hoberg-Phillips Data Library:

> https://hobergphillips.tuck.dartmouth.edu

The thesis uses the versions retrieved in February 2026.

Reference papers:
- Fresard, L., Hoberg, G., & Phillips, G. (2020). Innovation activities and
  integration through vertical acquisitions. *Review of Financial Studies*,
  33(7), 2937-2976. (Vertical integration / vertical relatedness data)
- Hoberg, G., & Phillips, G. (2016). Text-based network industries and
  endogenous product differentiation. *Journal of Political Economy*, 124(5),
  1423-1465. (TNIC data)

## What to place here

| File | Library section | Role in the analysis |
|---|---|---|
| `VertInteg.txt` | Vertical Integration | `gvkey, year, vertinteg` -- the firm-level vertical-integration score. **The only HP score used in the regressions.** |
| `VertNetwork_10gran.txt` | Vertical Networks (10% granularity) | `year, gvkey1, gvkey2, vertscore` (~3 GB). Defines sample membership (see below); its scores are not used. |
| `tnic3_data.txt` | TNIC-3 Network | `year, gvkey1, gvkey2, score` (~650 MB). Defines sample membership; its scores are not used. |

Files are tab-separated with a header row. Keep the original file names
(some downloads arrive zipped or in a subdirectory; place the flat `.txt`
files directly in this folder).

## Why the two network files are needed

The firm-year universe of the analysis is the set of firms appearing in the
HP pair networks (vertical or TNIC-3) in a given year. Both matter: a
sizable share of sample firm-years appear only in the TNIC-3 network, and a
small number of firm-years exist in `VertInteg.txt` without any network pair
and are not part of the sample. `src/03_build_hp.py` makes one pass over
each network file to construct that universe and then attaches the
vertical-integration score.
