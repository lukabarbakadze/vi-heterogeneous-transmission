"""Generate the figures used in the thesis.

Inputs:
    data/processed/panel_baseline.parquet      (scripts 04)
    data/processed/panel_outcomes.parquet
    output/tables/alt_outcomes_coefs.csv       (script 06)
    output/tables/quantile_all_outcomes.csv    (script 08)

Outputs (output/figures/):
    fig_vi_distribution.png   (Appendix A, Figure A1)
    fig_mps_timeseries.png    (Appendix A, Figure A2)
    fig_mps_components.png    (Appendix A, Figure A3)
    fig_coef_outcomes.png     (Figure 1: heterogeneous responses)
    fig_quantile_shapes.png   (Figure 2: quantile profiles)

Usage: python src/09_figures.py
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

mpl.rcParams.update({
    "font.family": "serif",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "figure.dpi": 150,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data/processed/panel_baseline.parquet"
OUTCOME_PANEL = ROOT / "data/processed/panel_outcomes.parquet"
ALT_COEFS = ROOT / "output/tables/alt_outcomes_coefs.csv"
QUANTILES = ROOT / "output/tables/quantile_all_outcomes.csv"
OUT = ROOT / "output/figures"

# Two-digit SIC major-group names (concise, for axis labels).
SIC2_NAMES = {
    "10": "Metal mining", "12": "Coal mining", "13": "Oil & gas extraction",
    "14": "Nonmetallic minerals mining", "15": "Building construction",
    "16": "Heavy construction", "17": "Special trade contractors",
    "20": "Food products", "21": "Tobacco", "22": "Textile mill products",
    "23": "Apparel", "24": "Lumber & wood", "25": "Furniture & fixtures",
    "26": "Paper & allied products", "27": "Printing & publishing",
    "28": "Chemicals", "29": "Petroleum refining",
    "30": "Rubber & plastics", "31": "Leather", "32": "Stone, clay & glass",
    "33": "Primary metals", "34": "Fabricated metal products",
    "35": "Industrial machinery", "36": "Electronic equipment",
    "37": "Transportation equipment", "38": "Instruments",
    "39": "Misc. manufacturing", "40": "Railroad transportation",
    "41": "Local passenger transit", "42": "Trucking & warehousing",
    "44": "Water transportation", "45": "Air transportation",
    "47": "Transportation services", "48": "Communications",
    "50": "Wholesale, durable goods", "51": "Wholesale, nondurable goods",
    "52": "Building materials retail", "53": "General merchandise stores",
    "54": "Food stores", "55": "Auto dealers & gas stations",
    "56": "Apparel stores", "57": "Furniture & home stores",
    "58": "Eating & drinking places", "59": "Misc. retail",
    "70": "Hotels & lodging", "72": "Personal services",
    "73": "Business services", "75": "Auto repair & services",
    "78": "Motion pictures", "79": "Amusement & recreation",
    "80": "Health services", "82": "Educational services",
    "83": "Social services", "87": "Engineering & research services",
}

# Display order of Figure 1 (top to bottom, as in the thesis)
FIG1_ORDER = ["sale_growth", "d_log_cogs", "d_log_capex", "d_log_invt",
              "d_log_rect", "d_log_debt", "d_log_xint", "d_log_ppent",
              "d_log_oi", "d_leverage"]
FIG1_LABELS = {"sale_growth": "Sales", "d_log_cogs": "COGS",
               "d_log_capex": "Capex", "d_log_invt": "Inventory",
               "d_log_rect": "Receivables", "d_log_debt": "Debt",
               "d_log_xint": "Interest expense", "d_log_ppent": "PP&E",
               "d_log_oi": "Operating income", "d_leverage": r"$\Delta$ Leverage"}


def sic2_label(code) -> str:
    c = str(int(code)).zfill(2)
    name = SIC2_NAMES.get(c)
    return f"{name} ({c})" if name else f"SIC {c}"


def fig_vi_distribution(df: pd.DataFrame) -> None:
    """A1: histogram of lagged VI, plus mean by SIC2 sector."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.6))

    vi = df["vi_lag"].dropna()
    vi = vi[vi.between(vi.quantile(0.001), vi.quantile(0.999))]
    axes[0].hist(vi, bins=60, color="0.35", edgecolor="white", linewidth=0.4)
    axes[0].axvline(vi.mean(), color="C3", linewidth=1.2, label=f"Mean = {vi.mean():.4f}")
    axes[0].axvline(vi.median(), color="C0", linewidth=1.2, linestyle="--",
                    label=f"Median = {vi.median():.4f}")
    axes[0].set_xlabel(r"Lagged vertical integration ($\mathrm{VI}_{i,t-1}$)")
    axes[0].set_ylabel("Firm-year observations")
    axes[0].set_title("(a) Distribution of lagged VI")
    axes[0].legend(frameon=False, fontsize=8)

    sec_means = (
        df.groupby("sic2")["vi_lag"]
        .agg(["mean", "count"])
        .query("count >= 200")
        .sort_values("mean")
        .tail(15)
    )
    axes[1].barh(
        [sic2_label(s) for s in sec_means.index],
        sec_means["mean"],
        color="0.45", edgecolor="white", linewidth=0.4,
    )
    axes[1].set_xlabel(r"Mean $\mathrm{VI}_{i,t-1}$")
    axes[1].set_ylabel("Sector (two-digit SIC)")
    axes[1].set_title("(b) Top 15 sectors by mean VI")

    plt.tight_layout()
    fig.savefig(OUT / "fig_vi_distribution.png")
    plt.close(fig)


def fig_mps_timeseries(df: pd.DataFrame) -> None:
    """A2: fiscal-year-aligned MPS, averaged across alignments per year."""
    annual = (
        df.drop_duplicates(subset=["year", "fy_end_month"])
        .groupby("year")["mps_orth"]
        .mean()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.bar(
        annual["year"], annual["mps_orth"],
        color=np.where(annual["mps_orth"] >= 0, "C3", "C0"),
        edgecolor="white", linewidth=0.4, width=0.8,
    )
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Year")
    ax.set_ylabel(r"$\mathrm{MPS}_t$ (orthogonalized, fiscal-year aligned)")
    ax.set_title("Bauer-Swanson orthogonalized monetary-policy surprises")
    ax.text(
        0.02, 0.95,
        "Red = tightening surprise (MPS > 0)\nBlue = easing surprise (MPS < 0)",
        transform=ax.transAxes, va="top", fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.7", lw=0.5),
    )
    plt.tight_layout()
    fig.savefig(OUT / "fig_mps_timeseries.png")
    plt.close(fig)


def fig_mps_components() -> None:
    """A3: per-year tightening (up) and easing (down) shock components."""
    df = pd.read_parquet(OUTCOME_PANEL, columns=["year", "fy_end_month",
                                                 "mps_pos", "mps_neg"])
    annual = (
        df.drop_duplicates(subset=["year", "fy_end_month"])
        .groupby("year")[["mps_pos", "mps_neg"]]
        .mean()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.bar(annual["year"], annual["mps_pos"], color="C3", width=0.8,
           edgecolor="white", linewidth=0.4, label=r"Tightening ($\mathrm{MPS}^+$)")
    ax.bar(annual["year"], annual["mps_neg"], color="C0", width=0.8,
           edgecolor="white", linewidth=0.4, label=r"Easing ($\mathrm{MPS}^-$)")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Year")
    ax.set_ylabel("Fiscal-year MPS component")
    ax.set_title("Tightening and easing components of the monetary-policy surprise")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    plt.tight_layout()
    fig.savefig(OUT / "fig_mps_components.png")
    plt.close(fig)


def fig_coef_across_outcomes() -> None:
    """Figure 1: coefficient plot for the ten outcomes (from script 06)."""
    coefs = pd.read_csv(ALT_COEFS).set_index("outcome")
    rows = [(FIG1_LABELS[o], coefs.loc[o, "coef"], coefs.loc[o, "se"])
            for o in FIG1_ORDER]
    df = pd.DataFrame(rows, columns=["outcome", "coef", "se"]).iloc[::-1]
    df["lo"] = df["coef"] - 1.96 * df["se"]
    df["hi"] = df["coef"] + 1.96 * df["se"]
    df["t"] = df["coef"] / df["se"]

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    y = np.arange(len(df))
    colors = ["C3" if abs(t) >= 1.96 else "0.55" for t in df["t"]]
    ax.errorbar(
        df["coef"], y,
        xerr=[df["coef"] - df["lo"], df["hi"] - df["coef"]],
        fmt="o", color="black", ecolor="0.4", elinewidth=1, capsize=2,
    )
    for yi, c in zip(y, colors):
        ax.plot(df["coef"].iloc[yi], yi, marker="o", color=c, markersize=6)
    ax.axvline(0, color="black", linewidth=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(df["outcome"])
    ax.set_xlabel(r"Coefficient on $\mathrm{MPS}_t \times \mathrm{VI}_{i,t-1}$ (95% CI)")
    ax.set_title(r"Heterogeneous responses across outcomes")
    plt.tight_layout()
    fig.savefig(OUT / "fig_coef_outcomes.png")
    plt.close(fig)


def fig_quantile_shapes() -> None:
    """Figure 2: the significant quantile patterns (from script 08)."""
    q = pd.read_csv(QUANTILES)

    def series(outcome):
        s = q[q["outcome"] == outcome].sort_values("tau")
        return s["tau"].tolist(), s["gamma"].tolist()

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))

    for outcome, marker, color, label in [
            ("sale_growth", "o", "C0", "Sales growth"),
            ("d_log_cogs", "s", "C3", "COGS growth"),
            ("d_log_ppent", "^", "C2", "PP&E growth")]:
        taus, gammas = series(outcome)
        axes[0].plot(taus, gammas, marker=marker, color=color,
                     linewidth=1.5, label=label)
    axes[0].axhline(0, color="black", linewidth=0.6)
    axes[0].set_title("(a) Effect rises across the distribution")
    axes[0].set_xlabel("Quantile")
    axes[0].set_ylabel(r"Coefficient on $\mathrm{MPS}_t \times \mathrm{VI}_{i,t-1}$")
    axes[0].legend(frameon=False, fontsize=8)

    taus, gammas = series("d_log_oi")
    axes[1].plot(taus, gammas, marker="o", color="C4", linewidth=1.5,
                 label="Operating income growth")
    axes[1].axhline(0, color="black", linewidth=0.6)
    axes[1].set_title("(b) Operating income: the exception")
    axes[1].set_xlabel("Quantile")
    axes[1].legend(frameon=False, fontsize=8)

    plt.tight_layout()
    fig.savefig(OUT / "fig_quantile_shapes.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(PANEL)
    df["sic2"] = df["sic2"].astype(str).str.zfill(2)
    print(f"Loaded panel: {df.shape}")
    fig_vi_distribution(df)
    fig_mps_timeseries(df)
    fig_mps_components()
    fig_coef_across_outcomes()
    fig_quantile_shapes()
    print("Wrote figures to", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
