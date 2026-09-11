.DEFAULT_GOAL := help
PY ?= python3
export PYTHONPATH := $(CURDIR)

.PHONY: help list offline demo mock scan hooks doctor lint clean

help: ## Show this help
	@echo
	@echo "Donkey Development Kit (DDK) demos"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "  Run one demo:      make demo N=03"
	@echo "  Present a demo:    DEMO_PAUSE=1 make demo N=03"
	@echo

list: ## List the demos and what each one needs
	@$(PY) run.py

offline: ## Run every demo that needs no credentials
	@$(PY) run.py --offline

demo: ## Run one demo, e.g. make demo N=03
	@test -n "$(N)" || (echo "usage: make demo N=03"; exit 2)
	@$(PY) run.py $(N)

mock: ## Start the local gateway simulator in the foreground (second pane)
	@donkey mock --port $${DEMO_MOCK_PORT:-8080}

scan: ## Fail if anything that looks like a credential is tracked or staged
	@$(PY) scripts/scan_secrets.py --all

hooks: ## Install the secret scan as a pre-commit hook
	@mkdir -p .git/hooks
	@printf '#!/bin/sh\nexec %s scripts/scan_secrets.py --staged\n' "$(PY)" > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "installed .git/hooks/pre-commit -> scripts/scan_secrets.py --staged"

doctor: ## Report what is installed and what each demo can therefore run
	@$(PY) scripts/doctor.py

lint: ## Ruff, if it is installed
	@ruff check . || true

clean: ## Remove caches and any stray demo output
	@rm -rf .ruff_cache .mypy_cache .pytest_cache out transcripts
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
