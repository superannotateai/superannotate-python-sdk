.PHONY: help coverage linter install mypy test validate

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  coverage   to make source code coverage check"
	@echo "  help       to show this help"
	@echo "  test       to make tests running"
	@echo "  validate   to make source code validation"

coverage:
	tox -e coverage

install:
	@echo "This function not implemented yet"

linter:
	tox -e linter

mypy:
	tox -e mypy

test:
	tox

validate:
	tox -e pre-commit
