.PHONY: all clean tests stress-tests coverage test_coverage install lint docs dist

PYTHON=python3
PYLINT=pylint
PYTESTS=pytest
COVERAGE=coverage

all: coverage tests
	$(PYTHON) setup.py build_ext --inplace

tests:
	$(PYTESTS) -n 8

stress-tests: SA_STRESS_TESTS=1
stress-tests: tests
	$(PYTESTS) -n 8

clean:
	rm -rf superannotate.egg-info
	rm -rf build
	rm -rf dist
	rm -rf htmlcov

coverage: test_coverage

test_coverage:
	-$(PYTESTS) --cov=superannotate -n 8
	$(COVERAGE) html
	@echo "\033[95m\n\nCoverage successful! View the output at file://htmlcov/index.html.\n\033[0m"

install:
	pip install .

lint:
	-$(PYLINT) --output-format=json superannotate/ | pylint-json2html -o pylint.html

lint_tests:
	-$(PYLINT) tests/*

docs:
	cd docs && make html
	@echo "\033[95m\n\nBuild successful! View the docs homepage at file://docs/build/html/index.html.\n\033[0m"

dist:
	-rm -rf dist/*
	$(PYTHON) setup.py sdist
	twine upload dist/*
