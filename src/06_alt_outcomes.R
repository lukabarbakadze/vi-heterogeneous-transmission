# VI x MPS across ten outcomes, plus placebo tests.
#
# Reproduces:
#   Figure 1     (coefficient plot across outcomes; coefficients exported
#                 to output/tables/alt_outcomes_coefs.csv for script 09)
#   Appendix B1  (all coefficients, ten outcomes)
#   Appendix C.4 (lead-MPS placebos, incl. the inventory exception)
#
# Same specification as the baseline; only the dependent variable changes.
#
# Input:  data/processed/panel_outcomes.csv  (script 04)
# Output: output/tables/alt_outcomes_coefs.csv
#         output/tables/appendix_b1_all_coefficients.csv
# Run:    Rscript src/06_alt_outcomes.R   (from the repository root)

library(fixest)
library(data.table)

df <- fread("data/processed/panel_outcomes.csv")
cat("============================================================\n")
cat("ALTERNATIVE OUTCOMES (Figure 1, Appendix B1, Appendix C.4)\n")
cat("============================================================\n\n")

cat(sprintf("Data: %d obs, %d firms, %d sectors, years %d-%d\n\n",
            nrow(df), uniqueN(df$gvkey), uniqueN(df$sic2),
            min(df$year), max(df$year)))

controls <- "vi_lag + log_size_lag + leverage_lag + log_ppent_lag + log_cash_lag"

outcomes <- c("sale_growth", "d_log_debt", "d_leverage", "d_log_cogs",
              "d_log_invt", "d_log_capex", "d_log_ppent", "d_log_oi",
              "d_log_xint", "d_log_rect")
labels <- c("Sales", "Debt", "Leverage", "COGS", "Inventory", "Capex",
            "PP&E", "Operating income", "Interest expense", "Receivables")

# ============================================================
# MAIN: ten outcomes, Firm + Sector x Year FE, two-way clustering
# ============================================================

models <- list()
for (i in seq_along(outcomes)) {
  cat(sprintf("--- (%d) %s: %s ---\n", i, labels[i], outcomes[i]))
  f <- as.formula(paste(outcomes[i], "~ mps_x_vi +", controls, "| gvkey + sic2^year"))
  models[[i]] <- feols(f, data = df, cluster = ~gvkey + year)
}

cat("\nRESULTS TABLE (outcomes 1-5):\n\n")
etable(models[[1]], models[[2]], models[[3]], models[[4]], models[[5]],
       headers = labels[1:5], se.below = TRUE, fitstat = c("n", "r2"))
cat("\nRESULTS TABLE (outcomes 6-10):\n\n")
etable(models[[6]], models[[7]], models[[8]], models[[9]], models[[10]],
       headers = labels[6:10], se.below = TRUE, fitstat = c("n", "r2"))

# ============================================================
# Export: gamma per outcome (Figure 1) + all coefficients (Appendix B1)
# ============================================================

coefs <- rbindlist(lapply(seq_along(outcomes), function(i) {
  m <- models[[i]]
  data.table(outcome = outcomes[i], label = labels[i],
             coef = unname(coef(m)["mps_x_vi"]),
             se = unname(se(m)["mps_x_vi"]),
             t = unname(coef(m)["mps_x_vi"] / se(m)["mps_x_vi"]),
             N = nobs(m), r2 = unname(r2(m, "r2")))
}))
fwrite(coefs, "output/tables/alt_outcomes_coefs.csv")
cat("\nSaved: output/tables/alt_outcomes_coefs.csv\n")

all_coefs <- rbindlist(lapply(seq_along(outcomes), function(i) {
  m <- models[[i]]
  ct <- as.data.table(coeftable(m), keep.rownames = "term")
  setnames(ct, c("term", "coef", "se", "t", "p"))
  ct[, outcome := outcomes[i]]
  ct[, N := nobs(m)]
  ct[, r2 := unname(r2(m, "r2"))]
  ct
}))
fwrite(all_coefs, "output/tables/appendix_b1_all_coefficients.csv")
cat("Saved: output/tables/appendix_b1_all_coefficients.csv\n")

cat("\nSUMMARY: gamma (MPS x VI) per outcome\n")
cat("| Outcome          |    gamma |     SE |      t |\n")
cat("|------------------|----------|--------|--------|\n")
for (i in seq_along(outcomes)) {
  cat(sprintf("| %-16s | %8.3f | %6.3f | %6.2f |\n",
              labels[i], coefs$coef[i], coefs$se[i], coefs$t[i]))
}

# ============================================================
# Appendix C.4: lead-MPS placebo per outcome
# ============================================================

cat("\n============================================================\n")
cat("APPENDIX C.4: Placebo test (lead MPS) per outcome\n")
cat("============================================================\n\n")

df[, mps_lead := shift(mps_orth, -1), by = gvkey]
df[, mps_x_vi_lead := mps_lead * vi_lag]

# Same five key outcomes as the thesis placebo table
key_outcomes <- c("sale_growth", "d_log_cogs", "d_log_invt", "d_log_capex", "d_log_debt")
key_labels <- c("Sales", "COGS", "Inventory", "Capex", "Debt")

cat("| Outcome          | Placebo gamma |      t | Pass? |\n")
cat("|------------------|---------------|--------|-------|\n")
placebos <- rbindlist(lapply(seq_along(key_outcomes), function(i) {
  f <- as.formula(paste(key_outcomes[i], "~ mps_x_vi_lead + vi_lag +",
                        gsub("vi_lag \\+ ", "", controls), "| gvkey + sic2^year"))
  m <- feols(f, data = df, cluster = ~gvkey + year)
  g <- unname(coef(m)["mps_x_vi_lead"]); t <- g / unname(se(m)["mps_x_vi_lead"])
  cat(sprintf("| %-16s | %13.2f | %6.2f | %-5s |\n",
              key_labels[i], g, t, ifelse(abs(t) < 1.96, "Yes", "NO")))
  data.table(outcome = key_outcomes[i], coef = g, se = g / t, t = t, N = nobs(m))
}))
fwrite(placebos, "output/tables/appendix_c4_lead_placebos.csv")
cat("\nPlacebo passes if NOT significant (|t| < 1.96).\n")
cat("Saved: output/tables/appendix_c4_lead_placebos.csv\n")
