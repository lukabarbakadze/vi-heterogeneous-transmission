# Replication pipeline for "Vertical Integration and the Heterogeneous
# Transmission of Monetary Policy".
#
# Stage 1 (Python): raw data -> processed inputs -> analysis panels
# Stage 2 (R):      panels   -> tables (logs in output/logs/)
# Stage 3 (Python): figures
#
# Run everything:           make all
# Run a single stage:       make data / make panels / make tables / make figures

PY  := python3
R   := Rscript
LOG := output/logs

all: data panels tables figures

# ---------------------------------------------------------------- Stage 1
data: data/processed/compustat_yearly.parquet \
      data/processed/mps_fiscal_year.parquet \
      data/processed/hp_firm_panel.parquet

data/processed/compustat_yearly.parquet: src/01_build_compustat.py
	$(PY) src/01_build_compustat.py 2>&1 | tee $(LOG)/01_build_compustat.log

data/processed/mps_fiscal_year.parquet: src/02_build_mps.py
	$(PY) src/02_build_mps.py 2>&1 | tee $(LOG)/02_build_mps.log

data/processed/hp_firm_panel.parquet: src/03_build_hp.py
	$(PY) src/03_build_hp.py 2>&1 | tee $(LOG)/03_build_hp.log

panels: data/processed/panel_baseline.parquet

data/processed/panel_baseline.parquet: src/04_build_panels.py \
		data/processed/compustat_yearly.parquet \
		data/processed/mps_fiscal_year.parquet \
		data/processed/hp_firm_panel.parquet
	$(PY) src/04_build_panels.py 2>&1 | tee $(LOG)/04_build_panels.log

# ---------------------------------------------------------------- Stage 2
tables: table2 alt_outcomes asymmetric quantile

table2: src/05_baseline.R
	$(R) src/05_baseline.R 2>&1 | tee $(LOG)/05_baseline.log

alt_outcomes: src/06_alt_outcomes.R
	$(R) src/06_alt_outcomes.R 2>&1 | tee $(LOG)/06_alt_outcomes.log

asymmetric: src/07_asymmetric.R
	$(R) src/07_asymmetric.R 2>&1 | tee $(LOG)/07_asymmetric.log

quantile: src/08_quantile.R
	$(R) src/08_quantile.R 2>&1 | tee $(LOG)/08_quantile.log

# ---------------------------------------------------------------- Stage 3
figures: src/09_figures.py
	$(PY) src/09_figures.py 2>&1 | tee $(LOG)/09_figures.log

clean:
	rm -rf data/processed/* output/tables/* output/figures/* output/logs/*
	touch data/processed/.gitkeep output/tables/.gitkeep \
	      output/figures/.gitkeep output/logs/.gitkeep

.PHONY: all data panels tables table2 alt_outcomes asymmetric quantile figures clean
