# Asymmetric (tightening vs easing) VI x MPS regressions.
#
# Reproduces:
#   Table 3, column 6 (asymmetric specification, sales)
#   Appendix B2      (asymmetric specification, all ten outcomes)
#
# Each FOMC surprise is split by sign BEFORE aggregation to the fiscal year
# (script 02), so MPS+ and MPS- decompose the within-year shock path and
# MPS+ + MPS- = MPS. The specification replaces the single interaction with
# the two signed interactions:
#   beta1 (MPS+ x VI): > 0 means high-VI firms do better during tightening
#   beta2 (MPS- x VI): > 0 means high-VI firms gain less during easing
# beta1 > 0 and beta2 > 0 together = symmetric attenuation. The asymmetry
# test is H0: beta1 = beta2.
#
# Input:  data/processed/panel_outcomes.csv  (script 04)
# Output: output/tables/asymmetric_coefs.csv
# Run:    Rscript src/07_asymmetric.R   (from the repository root)

library(fixest)
library(data.table)

df <- fread("data/processed/panel_outcomes.csv")
cat("============================================================\n")
cat("ASYMMETRIC EFFECTS (Table 3 col 6, Appendix B2)\n")
cat("============================================================\n\n")

cat(sprintf("Data: %d obs, %d firms, years %d-%d\n\n",
            nrow(df), uniqueN(df$gvkey), min(df$year), max(df$year)))

cat("MPS components:\n")
cat(sprintf("  mps_pos (tightening): mean=%.4f, sd=%.4f, always >= 0\n",
            mean(df$mps_pos, na.rm = TRUE), sd(df$mps_pos, na.rm = TRUE)))
cat(sprintf("  mps_neg (easing):     mean=%.4f, sd=%.4f, always <= 0\n",
            mean(df$mps_neg, na.rm = TRUE), sd(df$mps_neg, na.rm = TRUE)))
cat(sprintf("  |mps_pos + mps_neg - mps_orth| = %.6f (should be ~0)\n\n",
            mean(abs(df$mps_pos + df$mps_neg - df$mps_orth), na.rm = TRUE)))

controls <- "vi_lag + log_size_lag + leverage_lag + log_ppent_lag + log_cash_lag"

outcomes <- c("sale_growth", "d_log_debt", "d_leverage", "d_log_cogs",
              "d_log_invt", "d_log_capex", "d_log_ppent", "d_log_oi",
              "d_log_xint", "d_log_rect")
labels <- c("Sales", "Debt", "Leverage", "COGS", "Inventory", "Capex",
            "PP&E", "Operating income", "Interest expense", "Receivables")

# ============================================================
# All ten asymmetric regressions
# ============================================================

models <- list()
for (i in seq_along(outcomes)) {
  cat(sprintf("--- (%d) %s ---\n", i, labels[i]))
  f <- as.formula(paste(outcomes[i], "~ mps_pos_x_vi + mps_neg_x_vi +",
                        controls, "| gvkey + sic2^year"))
  models[[i]] <- feols(f, data = df, cluster = ~gvkey + year)
}

cat("\nRESULTS TABLE (outcomes 1-5):\n\n")
etable(models[[1]], models[[2]], models[[3]], models[[4]], models[[5]],
       headers = labels[1:5], se.below = TRUE, fitstat = c("n", "r2"))
cat("\nRESULTS TABLE (outcomes 6-10):\n\n")
etable(models[[6]], models[[7]], models[[8]], models[[9]], models[[10]],
       headers = labels[6:10], se.below = TRUE, fitstat = c("n", "r2"))

# ============================================================
# Summary + asymmetry tests (H0: beta1 = beta2)
# ============================================================

cat("\nSUMMARY: beta1 (tightening) vs beta2 (easing), and H0: beta1 = beta2\n\n")
cat("| Outcome          | beta1   |    t  | beta2   |    t  | diff   | SE(d) |  p    |\n")
cat("|------------------|---------|-------|---------|-------|--------|-------|-------|\n")

rows <- rbindlist(lapply(seq_along(outcomes), function(i) {
  m <- models[[i]]
  b1 <- unname(coef(m)["mps_pos_x_vi"]); se1 <- unname(se(m)["mps_pos_x_vi"])
  b2 <- unname(coef(m)["mps_neg_x_vi"]); se2 <- unname(se(m)["mps_neg_x_vi"])
  V <- vcov(m)
  se_d <- sqrt(V["mps_pos_x_vi", "mps_pos_x_vi"] +
               V["mps_neg_x_vi", "mps_neg_x_vi"] -
               2 * V["mps_pos_x_vi", "mps_neg_x_vi"])
  t_d <- (b1 - b2) / se_d
  p_d <- 2 * pt(-abs(t_d), df = nobs(m) - length(coef(m)))
  cat(sprintf("| %-16s | %7.2f | %5.2f | %7.2f | %5.2f | %6.2f | %5.2f | %5.3f |\n",
              labels[i], b1, b1 / se1, b2, b2 / se2, b1 - b2, se_d, p_d))
  data.table(outcome = outcomes[i], label = labels[i],
             beta_pos = b1, se_pos = se1, t_pos = b1 / se1,
             beta_neg = b2, se_neg = se2, t_neg = b2 / se2,
             diff = b1 - b2, se_diff = se_d, p_diff = p_d, N = nobs(m))
}))
fwrite(rows, "output/tables/asymmetric_coefs.csv")
cat("\nEqual coefficients (p > 0.05) = symmetric attenuation.\n")
cat("Saved: output/tables/asymmetric_coefs.csv\n")
