# Baseline VI x MPS regressions and robustness checks.
#
# Reproduces:
#   Table 2  (baseline under four fixed-effect structures, all coefficients)
#   Table 3, columns 1-5 (within-firm VI, leverage interaction, pre/post-2008
#            split, lead-MPS placebo)
#
# Specification (adapted from Ottonello-Winberry 2020, eq. 3-4):
#   Y_it = a_i + a_st + gamma (MPS_it x VI_i,t-1) + beta VI_i,t-1 + d'X_i,t-1 + e
# gamma > 0: high-VI firms are less hurt by tightening, less helped by easing.
#
# Input:  data/processed/panel_baseline.csv  (script 04)
# Output: output/tables/table2_baseline.csv
#         output/tables/table3_robustness.csv
# Run:    Rscript src/05_baseline.R   (from the repository root)

library(fixest)
library(data.table)

df <- fread("data/processed/panel_baseline.csv")
cat("============================================================\n")
cat("BASELINE VI x MPS (Table 2) + ROBUSTNESS (Table 3, cols 1-5)\n")
cat("============================================================\n\n")

cat(sprintf("Data: %d obs, %d firms, %d sectors, years %d-%d\n\n",
            nrow(df), uniqueN(df$gvkey), uniqueN(df$sic2),
            min(df$year), max(df$year)))

controls <- "vi_lag + log_size_lag + leverage_lag + log_ppent_lag + log_cash_lag"

# ============================================================
# TABLE 2: Baseline under four fixed-effect structures
# ============================================================

cat("--- (1) Firm + Sector x Year FE (preferred; MPS absorbed) ---\n")
m1 <- feols(as.formula(paste("sale_growth ~ mps_x_vi +", controls, "| gvkey + sic2^year")),
            data = df, cluster = ~gvkey + year)

cat("--- (2) Firm + Sector FE + MPS ---\n")
m2 <- feols(as.formula(paste("sale_growth ~ mps_orth + mps_x_vi +", controls, "| gvkey + sic2")),
            data = df, cluster = ~gvkey + year)

cat("--- (3) Firm FE + MPS ---\n")
m3 <- feols(as.formula(paste("sale_growth ~ mps_orth + mps_x_vi +", controls, "| gvkey")),
            data = df, cluster = ~gvkey + year)

cat("--- (4) Firm + Year + Sector FE (MPS absorbed) ---\n")
m4 <- feols(as.formula(paste("sale_growth ~ mps_x_vi +", controls, "| gvkey + year + sic2")),
            data = df, cluster = ~gvkey + year)

cat("\nTABLE 2:\n=======\n\n")
etable(m1, m2, m3, m4,
       headers = c("Firm+SecxYr", "Firm+Sec+MPS", "Firm+MPS", "Firm+Yr+Sec"),
       se.below = TRUE,
       fitstat = c("n", "r2"))

# Tidy export
tidy_model <- function(m, model_label) {
  ct <- as.data.table(coeftable(m), keep.rownames = "term")
  setnames(ct, c("term", "coef", "se", "t", "p"))
  ct[, model := model_label]
  ct[, N := nobs(m)]
  ct[, r2 := unname(r2(m, "r2"))]
  ct
}
table2 <- rbindlist(list(
  tidy_model(m1, "firm_sector_x_year"),
  tidy_model(m2, "firm_sector_mps"),
  tidy_model(m3, "firm_mps"),
  tidy_model(m4, "firm_year_sector")))
fwrite(table2, "output/tables/table2_baseline.csv")
cat("\nSaved: output/tables/table2_baseline.csv\n")

# ============================================================
# TABLE 3 (1): Within-firm VI variation
# ============================================================

cat("\n============================================================\n")
cat("TABLE 3 (1): Within-firm VI variation\n")
cat("============================================================\n\n")

df[, vi_mean := mean(vi_lag, na.rm = TRUE), by = gvkey]
df[, vi_within := vi_lag - vi_mean]
df[, mps_x_vi_within := mps_orth * vi_within]

m_within <- feols(as.formula(paste("sale_growth ~ mps_x_vi_within + vi_within +",
                                    gsub("vi_lag \\+ ", "", controls), "| gvkey + sic2^year")),
                  data = df, cluster = ~gvkey + year)
print(summary(m_within))

cat(sprintf("\n  Full VI:     gamma = %.3f (SE = %.3f, t = %.2f)\n",
            coef(m1)["mps_x_vi"], se(m1)["mps_x_vi"],
            coef(m1)["mps_x_vi"] / se(m1)["mps_x_vi"]))
cat(sprintf("  Within-firm: gamma = %.3f (SE = %.3f, t = %.2f)\n",
            coef(m_within)["mps_x_vi_within"], se(m_within)["mps_x_vi_within"],
            coef(m_within)["mps_x_vi_within"] / se(m_within)["mps_x_vi_within"]))

# ============================================================
# TABLE 3 (2): Leverage x MPS (Ottonello-Winberry benchmark)
# ============================================================

cat("\n============================================================\n")
cat("TABLE 3 (2): Leverage x MPS horse race\n")
cat("============================================================\n\n")

df[, mps_x_lev := mps_orth * leverage_lag]

m_both <- feols(sale_growth ~ mps_x_vi + mps_x_lev + vi_lag + leverage_lag +
                log_size_lag + log_ppent_lag + log_cash_lag | gvkey + sic2^year,
                data = df, cluster = ~gvkey + year)
print(summary(m_both))

# ============================================================
# TABLE 3 (3)-(4): Pre/post-2008 split (conventional vs ZLB era)
# ============================================================
# O-W (2020), footnote 5, stop in Dec 2007 to study conventional policy;
# the funds rate hits the ZLB in late 2008.

cat("\n============================================================\n")
cat("TABLE 3 (3)-(4): Pre-2008 vs Post-2008\n")
cat("============================================================\n\n")

m_pre <- feols(as.formula(paste("sale_growth ~ mps_x_vi +", controls, "| gvkey + sic2^year")),
               data = df[year <= 2007], cluster = ~gvkey + year)
m_post <- feols(as.formula(paste("sale_growth ~ mps_x_vi +", controls, "| gvkey + sic2^year")),
                data = df[year >= 2008], cluster = ~gvkey + year)

etable(m_pre, m_post, headers = c("Pre-2008", "Post-2008"),
       se.below = TRUE, fitstat = c("n", "r2"))

cat(sprintf("\nPre-2008 (conv. MP): gamma = %.3f (t = %.2f), N = %d\n",
            coef(m_pre)["mps_x_vi"], coef(m_pre)["mps_x_vi"] / se(m_pre)["mps_x_vi"],
            nobs(m_pre)))
cat(sprintf("Post-2008 (ZLB/QE):  gamma = %.3f (t = %.2f), N = %d\n",
            coef(m_post)["mps_x_vi"], coef(m_post)["mps_x_vi"] / se(m_post)["mps_x_vi"],
            nobs(m_post)))

# ============================================================
# TABLE 3 (5): Placebo (lead MPS)
# ============================================================

cat("\n============================================================\n")
cat("TABLE 3 (5): Placebo test (lead MPS)\n")
cat("============================================================\n\n")

df[, mps_lead := shift(mps_orth, -1), by = gvkey]
df[, mps_x_vi_lead := mps_lead * vi_lag]

m_placebo <- feols(as.formula(paste("sale_growth ~ mps_x_vi_lead + vi_lag +",
                                     gsub("vi_lag \\+ ", "", controls), "| gvkey + sic2^year")),
                   data = df, cluster = ~gvkey + year)
print(summary(m_placebo))

cat(sprintf("\nPlacebo: gamma_lead = %.3f (t = %.2f)\n",
            coef(m_placebo)["mps_x_vi_lead"],
            coef(m_placebo)["mps_x_vi_lead"] / se(m_placebo)["mps_x_vi_lead"]))

# ============================================================
# Tidy export for Table 3 columns 1-5
# ============================================================

table3 <- rbindlist(list(
  tidy_model(m_within, "within_firm"),
  tidy_model(m_both, "vi_plus_leverage"),
  tidy_model(m_pre, "pre_2008"),
  tidy_model(m_post, "post_2008"),
  tidy_model(m_placebo, "lead_placebo")))
fwrite(table3, "output/tables/table3_robustness.csv")
cat("\nSaved: output/tables/table3_robustness.csv\n")

# ============================================================
# SUMMARY
# ============================================================

cat("\n============================================================\n")
cat("SUMMARY\n")
cat("============================================================\n\n")
cat(sprintf("Baseline (Firm+SecxYr):  gamma = %.3f (SE %.3f, t = %.2f), N = %d\n",
            coef(m1)["mps_x_vi"], se(m1)["mps_x_vi"],
            coef(m1)["mps_x_vi"] / se(m1)["mps_x_vi"], nobs(m1)))
cat(sprintf("Within-firm VI:          gamma = %.3f (t = %.2f)\n",
            coef(m_within)["mps_x_vi_within"],
            coef(m_within)["mps_x_vi_within"] / se(m_within)["mps_x_vi_within"]))
cat(sprintf("With MPS x Leverage:     gamma = %.3f (t = %.2f)\n",
            coef(m_both)["mps_x_vi"], coef(m_both)["mps_x_vi"] / se(m_both)["mps_x_vi"]))
cat(sprintf("Pre-2008:                gamma = %.3f (t = %.2f)\n",
            coef(m_pre)["mps_x_vi"], coef(m_pre)["mps_x_vi"] / se(m_pre)["mps_x_vi"]))
cat(sprintf("Post-2008:               gamma = %.3f (t = %.2f)\n",
            coef(m_post)["mps_x_vi"], coef(m_post)["mps_x_vi"] / se(m_post)["mps_x_vi"]))
cat(sprintf("Lead placebo:            gamma = %.3f (t = %.2f)\n",
            coef(m_placebo)["mps_x_vi_lead"],
            coef(m_placebo)["mps_x_vi_lead"] / se(m_placebo)["mps_x_vi_lead"]))
