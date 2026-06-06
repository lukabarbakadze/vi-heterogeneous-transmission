# Quantile regressions: where in the outcome distribution does the effect sit?
#
# Reproduces:
#   Figure 2     (quantile profiles; coefficients exported to
#                 output/tables/quantile_all_outcomes.csv for script 09)
#   Appendix B3  (gamma by quantile for all ten outcomes, with the
#                 H0: gamma_0.10 = gamma_0.90 test)
#
# Quantile regression cannot absorb high-dimensional firm fixed effects, so
# firm heterogeneity is captured with a Mundlak correction (firm-level means
# of VI and size) alongside year dummies. Standard errors are asymptotic
# ("nid"), not two-way clustered, so precision is not directly comparable to
# the baseline; the relevant statistic is the 10th-vs-90th percentile test.
#
# Input:  data/processed/panel_outcomes.csv  (script 04)
# Output: output/tables/quantile_all_outcomes.csv
# Run:    Rscript src/08_quantile.R   (from the repository root; ~5-10 min)

library(quantreg)
library(data.table)

cat("============================================================\n")
cat("QUANTILE REGRESSION (Figure 2, Appendix B3)\n")
cat("Started:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n")
cat("============================================================\n\n")

df <- fread("data/processed/panel_outcomes.csv")
cat(sprintf("Data: %d obs, %d firms\n\n", nrow(df), uniqueN(df$gvkey)))

# Mundlak correction: firm-level means of the key time-varying regressors
df[, vi_mean := mean(vi_lag, na.rm = TRUE), by = gvkey]
df[, size_mean := mean(log_size_lag, na.rm = TRUE), by = gvkey]

taus <- c(0.10, 0.25, 0.50, 0.75, 0.90)

outcomes <- c("sale_growth", "d_log_debt", "d_leverage", "d_log_cogs",
              "d_log_invt", "d_log_capex", "d_log_ppent", "d_log_oi",
              "d_log_xint", "d_log_rect")
labels <- c("Sale Growth", "Debt Growth", "D Leverage", "COGS Growth",
            "Inventory", "Capex", "PP&E", "Op. Income", "Interest",
            "Receivables")

all_results <- list()

for (i in seq_along(outcomes)) {
  outcome <- outcomes[i]
  cat("============================================================\n")
  cat(sprintf("QUANTILE REGRESSION: %s (%s)\n", labels[i], outcome))
  cat("============================================================\n\n")

  form <- as.formula(paste0(outcome, " ~ mps_x_vi + vi_lag + log_size_lag + ",
                            "leverage_lag + log_ppent_lag + log_cash_lag + ",
                            "vi_mean + size_mean + factor(year)"))

  results <- data.table(outcome = character(), tau = numeric(),
                        gamma = numeric(), se = numeric(), t = numeric(),
                        ci_lo = numeric(), ci_hi = numeric())

  for (tau in taus) {
    cat(sprintf("  tau = %.2f ... ", tau))
    start_time <- Sys.time()
    tryCatch({
      m <- rq(form, data = df, tau = tau)
      s <- summary(m, se = "nid")
      gamma <- coef(m)["mps_x_vi"]
      se <- s$coefficients["mps_x_vi", "Std. Error"]
      results <- rbind(results, data.table(
        outcome = outcome, tau = tau,
        gamma = unname(gamma), se = unname(se), t = unname(gamma / se),
        ci_lo = unname(gamma - 1.96 * se), ci_hi = unname(gamma + 1.96 * se)))
      elapsed <- round(difftime(Sys.time(), start_time, units = "secs"), 1)
      cat(sprintf("gamma = %.2f (SE = %.2f, t = %.2f) [%s sec]\n",
                  gamma, se, gamma / se, elapsed))
    }, error = function(e) cat(sprintf("ERROR: %s\n", e$message)))
  }

  all_results[[outcome]] <- results

  # Test gamma_0.10 = gamma_0.90 (independent-normal approximation)
  if (0.1 %in% results$tau & 0.9 %in% results$tau) {
    g10 <- results[tau == 0.1, gamma]; se10 <- results[tau == 0.1, se]
    g90 <- results[tau == 0.9, gamma]; se90 <- results[tau == 0.9, se]
    d <- g10 - g90; se_d <- sqrt(se10^2 + se90^2)
    p_d <- 2 * pnorm(-abs(d / se_d))
    cat(sprintf("\n  H0: gamma_0.10 = gamma_0.90: diff = %.2f (SE = %.2f, t = %.2f, p = %.3f) -> %s\n\n",
                d, se_d, d / se_d, p_d,
                ifelse(p_d < 0.05, "REJECT", "fail to reject")))
  }
}

# ============================================================
# Combined summary
# ============================================================

combined <- rbindlist(all_results)

cat("============================================================\n")
cat("COMBINED SUMMARY: gamma (MPS x VI) by quantile\n")
cat("============================================================\n\n")
cat("| Outcome      | t=0.10 | t=0.25 | t=0.50 | t=0.75 | t=0.90 |\n")
cat("|--------------|--------|--------|--------|--------|--------|\n")
for (i in seq_along(outcomes)) {
  res <- combined[outcome == outcomes[i]]
  if (nrow(res) == 0) next
  g <- sapply(taus, function(tt) res[tau == tt, gamma])
  cat(sprintf("| %-12s | %6.2f | %6.2f | %6.2f | %6.2f | %6.2f |\n",
              substr(labels[i], 1, 12), g[1], g[2], g[3], g[4], g[5]))
}

fwrite(combined, "output/tables/quantile_all_outcomes.csv")
cat("\nSaved: output/tables/quantile_all_outcomes.csv\n")
cat("\nFinished:", format(Sys.time(), "%Y-%m-%d %H:%M:%S"), "\n")
