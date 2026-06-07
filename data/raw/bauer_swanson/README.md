# Bauer-Swanson monetary-policy surprises

The monetary-policy shock series is the Bauer-Swanson high-frequency
monetary-policy surprise, orthogonalized with respect to pre-announcement
macroeconomic and financial data.

Reference paper:
- Bauer, M. D., & Swanson, E. T. (2023). A reassessment of monetary policy
  surprises and high-frequency identification. *NBER Macroeconomics Annual*,
  37, 87-155. https://doi.org/10.1086/723574
  (working-paper version: https://www.nber.org/papers/w29939)

## What to place here

| File | Source |
|---|---|
| `monetary-policy-surprises-data.xlsx` | Federal Reserve Bank of San Francisco: https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/ (direct file link on that page) |

The thesis uses the version retrieved in February 2026. The SF Fed updates
the series periodically; the build (`src/02_build_mps.py`) reads the sheet
**"FOMC (update 2023)"** and uses the columns `Date`, `MPS`, and
`MPS_ORTH`. The analysis uses `MPS_ORTH` (the orthogonalized surprise);
positive values are tightening surprises.
