PYTEST_FLAGS=-W error::SyntaxWarning

SPHINXOPTS    = -W --keep-going
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = launchdarkly-openfeature-server
SOURCEDIR     = docs
BUILDDIR      = $(SOURCEDIR)/build

.PHONY: help
help: #! Show this help message
	@echo 'Usage: make [target] ... '
	@echo ''
	@echo 'Targets:'
	@grep -h -F '#!' $(MAKEFILE_LIST) | grep -v grep | sed 's/:.*#!/:/' | column -t -s":"

.PHONY: install
install:
	@poetry install

#
# Quality control checks
#

.PHONY: test
test: #! Run unit tests
test: install
	@poetry run pytest $(PYTEST_FLAGS)

.PHONY: lint
lint: #! Run type analysis and linting checks
lint: install
	@mkdir -p .mypy_cache
	@poetry run mypy ld_openfeature tests

#
# Documentation generation
#

.PHONY: docs
docs: #! Generate sphinx-based documentation
	@poetry install --with docs
	@cd docs
	@poetry run $(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
