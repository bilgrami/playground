# Makefile for snowflake-diff
# Usage:
#   make connect-test
#   make diff
#   make diff-fast
#   make diff-ddl
#   make showreport

PYTHON ?= python3
CONFIG ?= config.yml
OUT ?= out

.PHONY: help install test connect-test diff diff-fast diff-ddl showreport clean

help:
	@echo "Targets:"
	@echo "  install       Install python deps"
	@echo "  test          Run unit tests with coverage"
	@echo "  connect-test  Run connection tests for left/right"
	@echo "  diff          Full diff (default config options)"
	@echo "  diff-fast     Skip data hashing + skip procedures"
	@echo "  diff-ddl      Only DDL + schema (no data/comments/last-changed)"
	@echo "  showreport    Print paths to report + summary"
	@echo "  clean         Remove output directory"

install:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m pytest --cov=scripts --cov-report=term-missing --cov-fail-under=80

connect-test:
	$(PYTHON) -m scripts.snowdiff --config $(CONFIG) connect-test

diff:
	$(PYTHON) -m scripts.snowdiff --config $(CONFIG) diff --out $(OUT)

diff-fast:
	$(PYTHON) -m scripts.snowdiff --config $(CONFIG) diff --out $(OUT) --no-data --no-procs

diff-ddl:
	$(PYTHON) -m scripts.snowdiff --config $(CONFIG) diff --out $(OUT) --no-data --no-comments --no-last-changed

showreport:
	@echo "Summary: $(OUT)/SUMMARY.md"
	@echo "Report : $(OUT)/report.txt"
	@echo "Diffs  : $(OUT)/diffs/"
	@echo "Snaps  : $(OUT)/snapshots/"

clean:
	rm -rf $(OUT)
