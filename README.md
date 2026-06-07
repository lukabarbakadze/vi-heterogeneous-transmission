# Replication: Vertical Integration and the Heterogeneous Transmission of Monetary Policy

Code for the Master's thesis *"Vertical Integration and the Heterogeneous
Transmission of Monetary Policy"* (Luka Barbakadze, ISET, 2026).

The thesis asks whether vertical integration shapes how firms respond to
monetary-policy shocks. Using the Hoberg-Phillips text-based vertical-
integration score and Bauer-Swanson high-frequency monetary-policy surprises
for U.S. public firms (1990-2019), it finds that more vertically integrated
firms respond *less* to a given surprise -- symmetrically across tightening
and easing -- with the differential concentrated in real activity (sales,
COGS) rather than financing outcomes.

## Data availability

No data is included in this repository. Two of the three inputs are freely
downloadable:

| Source | Access | Where | Accessed | Instructions |
|---|---|---|---|---|
| Hoberg-Phillips Data Library (VI score, networks) | Free, registration | [hobergphillips.tuck.dartmouth.edu](https://hobergphillips.tuck.dartmouth.edu) | Feb 2026 | [`data/raw/hoberg_phillips/`](data/raw/hoberg_phillips/README.md) |
| Bauer-Swanson monetary-policy surprises | Free | [SF Fed data page](https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/) | Feb 2026 | [`data/raw/bauer_swanson/`](data/raw/bauer_swanson/README.md) |

The firm-level accounting data come from Compustat quarterly (`comp.fundq`),
accessed through a WRDS subscription;
[`data/raw/wrds/README.md`](data/raw/wrds/README.md) gives the exact extract
specification. Access dates matter for exact replication: the data providers
revise their series over time, so a later vintage can shift observation
counts slightly. Place the files as described in the three READMEs, then run
the pipeline.

## Setup

Python >= 3.10 and R >= 4.2.

```bash
pip install -r requirements.txt
Rscript -e 'install.packages(c("fixest", "data.table", "quantreg"))'
```

Versions used for the thesis runs: Python 3.13 (pandas 2.3.3, numpy 2.4.0,
pyarrow 22.0.0), R 4.5.2 (fixest 0.14.0, data.table 1.18.2.1, quantreg 6.1).

## Running

```bash
make all          # everything: data -> panels -> tables -> figures
```

or stage by stage:

```bash
make data         # 01 Compustat, 02 MPS, 03 Hoberg-Phillips   (~10 min)
make panels       # 04 merge into the two analysis panels      (~2 min)
make tables       # 05-08 all regressions                      (~10 min)
make figures      # 09 paper figures                           (<1 min)
```

Logs land in `output/logs/`, tidy coefficient tables in `output/tables/`,
figures in `output/figures/`.

## Pipeline

| Script | What it does | Paper artifact |
|---|---|---|
| `src/01_build_compustat.py` | Raw quarterly Compustat -> fiscal-year firm panel (flows summed over fiscal quarters, stocks at fiscal Q4, fiscal-year-end keys) | -- |
| `src/02_build_mps.py` | FOMC surprises -> timing-weighted monthly sums -> 12-month sums for every fiscal-year-end month, with signed (tightening/easing) components | -- |
| `src/03_build_hp.py` | HP network + firm-level files -> firm-year VI panel | -- |
| `src/04_build_panels.py` | Merge with lagged VI and fiscal-year-aligned shocks; sample filters; clean one-fiscal-year growth windows | Table 1, Appendix A |
| `src/05_baseline.R` | Baseline under four FE structures; within-firm, leverage, pre/post-2008, lead placebo | Table 2; Table 3 cols 1-5 |
| `src/06_alt_outcomes.R` | Same specification across ten outcomes; lead placebos | Figure 1; Appendix B1, C.4 |
| `src/07_asymmetric.R` | Signed-shock interactions, asymmetry tests | Table 3 col 6; Appendix B2 |
| `src/08_quantile.R` | Quantile regressions with Mundlak correction | Figure 2; Appendix B3 |
| `src/09_figures.py` | All figures (reads the exported coefficient CSVs) | Figures 1-2, A1-A3 |

## Verification

A successful replication reproduces these headline numbers (two-way
clustered SEs by firm and year; firm + sector-by-year fixed effects):

| Quantity | Value |
|---|---|
| Baseline panel | N = 96,569 firm-years, 10,660 firms |
| Baseline gamma (MPS x VI, sales growth) | 7.377 (SE 1.362, t = 5.42), N = 95,284 |
| COGS growth gamma | 6.556 (SE 1.228, t = 5.34) |
| Within-firm VI gamma | 0.768 (t = 0.37) |
| With MPS x Leverage | 7.477 (t = 5.22) |
| Pre-2008 / post-2008 gamma | 7.027 (t = 3.51) / 16.754 (t = 3.57) |
| Lead-MPS placebo gamma | 0.872 (t = 0.78) |
| Asymmetric (sales): tightening / easing | 6.64 / 7.85, equality p = 0.607 |

Exact reproduction requires the same input vintages (see the access dates
in the Data availability table; the Compustat extract is from January
2026). Small deviations in N with a newer extract are expected; the
qualitative results are not sensitive to this.

## Citation

If you use this code, please cite the thesis (see `CITATION.cff`, or the
"Cite this repository" button on GitHub):

> Barbakadze, L. (2026). *Vertical Integration and the Heterogeneous
> Transmission of Monetary Policy* (Master's thesis). International School
> of Economics at TSU (ISET).

and the underlying data sources:

- Hoberg, G., & Phillips, G. (2016). Text-based network industries and
  endogenous product differentiation. *JPE*, 124(5), 1423-1465.
- Fresard, L., Hoberg, G., & Phillips, G. (2020). Innovation activities and
  integration through vertical acquisitions. *RFS*, 33(7), 2937-2976.
- Bauer, M. D., & Swanson, E. T. (2023). A reassessment of monetary policy
  surprises and high-frequency identification. *NBER Macro Annual*, 37, 87-155.
- Ottonello, P., & Winberry, T. (2020). Financial heterogeneity and the
  investment channel of monetary policy. *Econometrica*, 88(6), 2473-2502.
  (empirical design)

The code is MIT-licensed (see `LICENSE`). The license covers the code in
this repository only; it does not extend to the input data, which is not
redistributed here and remains subject to the terms of its providers
(Hoberg-Phillips Data Library, Federal Reserve Bank of San Francisco, and
WRDS / S&P Global Compustat).

## Acknowledgment

Wharton Research Data Services (WRDS) was used in preparing this work. This
service and the data available thereon constitute valuable intellectual
property and trade secrets of WRDS and/or its third-party suppliers.
