# Bauer-Swanson monetary-policy surprises

The monetary-policy shock series is the Bauer-Swanson high-frequency
monetary-policy surprise, orthogonalized with respect to pre-announcement
macroeconomic and financial data.

Reference paper:
- Bauer, M. D., & Swanson, E. T. (2023). A reassessment of monetary policy
  surprises and high-frequency identification. *NBER Macroeconomics Annual*,
  37, 87-155.

## What to place here

| File | Source |
|---|---|
| `monetary-policy-surprises-data.xlsx` | https://www.michaeldbauer.com/files/mps/ (also linked from the paper's replication page and the Federal Reserve Bank of San Francisco) |

The build (`src/02_build_mps.py`) reads the sheet **"FOMC (update 2023)"**
and uses the columns `Date`, `MPS`, and `MPS_ORTH`. The analysis uses
`MPS_ORTH` (the orthogonalized surprise); positive values are tightening
surprises.
