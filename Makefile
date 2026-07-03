# buddy — developer tasks. Run targets use PYTHONPATH=src so they work even when
# macOS re-hides .venv and the editable install stops resolving (see README dev note).

VENV := .venv
PY   := $(VENV)/bin/python
RUFF := $(VENV)/bin/ruff
RUN  := PYTHONPATH=src $(PY)
SITE := $(shell $(PY) -c "import site; print(site.getsitepackages()[0])" 2>/dev/null)

.DEFAULT_GOAL := help
.PHONY: help run list sheet test lint fmt fix check snapshots install link hooks fix-venv

help: ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

run: ## Run buddy (pass ARGS="--animal cat --seed 1")
	$(RUN) -m buddy $(ARGS)

list: ## List available critters
	$(RUN) -m buddy --list

sheet: ## Print the colored critter contact sheet
	$(RUN) -m buddy.devsheet

test: ## Run the full test gate (unit + snapshots)
	$(PY) -m pytest

lint: ## Lint with ruff
	$(RUFF) check src tests

fmt: ## Check formatting (no writes)
	$(RUFF) format --check src tests

fix: ## Auto-fix lint + formatting
	$(RUFF) check --fix src tests
	$(RUFF) format src tests

check: lint fmt test ## The standing local gate: lint + format-check + tests

snapshots: ## Regenerate SVG snapshot baselines
	$(PY) -m pytest tests/test_app_snapshot.py --snapshot-update

install: ## (Re)install the package into the venv (editable + durable symlink + git hooks)
	$(VENV)/bin/pip install -e ".[dev]"
	$(MAKE) link
	$(MAKE) hooks

hooks: ## Activate the git hooks so `make check` runs automatically on every commit
	git config core.hooksPath hooks
	@echo "git hooks active (core.hooksPath=hooks) — the gate runs on every commit"

link: ## Symlink src/buddy into site-packages so `buddy` imports even when .venv is hidden
	@test -n "$(SITE)" || { echo "could not locate site-packages (is the venv built?)"; exit 1; }
	ln -sfn "$(CURDIR)/src/buddy" "$(SITE)/buddy"
	@echo "linked $(SITE)/buddy -> $(CURDIR)/src/buddy"

fix-venv: link ## Restore `.venv/bin/buddy` after macOS re-hides .venv (recreates the symlink)
	-chflags -R nohidden $(VENV)
	@echo "buddy resolution restored (live symlink; UF_HIDDEN cleared if it was set)"
