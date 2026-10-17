# Plain equivalents (when make is absent):
#   python -m pip install -e ".[dev]"
#   python -m ruff check src tests && python -m ruff format --check src tests
#   python -m mypy
#   python -m pytest
#   python -m hemp eval
#   python -m hemp eval-regression          # exits 1 when the gate goes red
#   python -m hemp demo
#   python -m hemp.secretscan

PYTHON ?= python3

.PHONY: setup lint format typecheck test eval eval-regression eval-regression-assert demo secrets secretscan-hash ci

setup:
	$(PYTHON) -m pip install -e ".[dev]"
	pre-commit install || true

lint:
	$(PYTHON) -m ruff check src tests
	$(PYTHON) -m ruff format --check src tests

format:
	$(PYTHON) -m ruff format src tests
	$(PYTHON) -m ruff check --fix src tests

typecheck:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m pytest

eval:
	$(PYTHON) -m hemp eval

# This target is expected to fail (exit 1). That is the gate going red.
eval-regression:
	$(PYTHON) -m hemp eval-regression

eval-regression-assert:
	@set +e; \
	$(PYTHON) -m hemp eval-regression > /tmp/hemp-reg.txt; \
	status=$$?; \
	set -e; \
	cat /tmp/hemp-reg.txt; \
	test "$$status" -eq 1; \
	grep -q GATE_RED /tmp/hemp-reg.txt

demo:
	$(PYTHON) -m hemp demo

secrets:
	$(PYTHON) -m hemp.secretscan

secretscan-hash:
	@$(PYTHON) -c 'import hashlib, pathlib, sys; digest = hashlib.sha256(pathlib.Path("src/hemp/secretscan.py").read_bytes()).hexdigest(); text = pathlib.Path("docs/PROVENANCE.md").read_text(encoding="utf-8"); needle = "src/hemp/secretscan.py sha256 " + digest; \
sys.exit(0 if needle in text else (print("secretscan hash mismatch", digest) or 1))'

ci: lint typecheck test eval secrets secretscan-hash eval-regression-assert
