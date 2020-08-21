.PHONY: all clean tests coverage

PYTHON=python
PYLINT=pylint
PYTESTS=pytest
COVERAGE=coverage
BROWSER=google-chrome

all: coverage tests
	$(PYTHON) setup.py build_ext --inplace

tests:
	$(PYTESTS)

stress-tests: AO_TEST_LEVEL=stress
stress-tests: tests
	$(PYTESTS)

clean:
	rm -rf superannotate.egg-info
	rm -rf build
	rm -rf dist
	rm -rf htmlcov

coverage: test_coverage

test_coverage:
	$(COVERAGE) run -m  --source=./superannotate/  $(PYTESTS)
	$(COVERAGE) html
	$(BROWSER) htmlcov/index.html

install:
	pip install .

lint:
	-$(PYLINT) superannotate/
	-$(PYLINT) tests/*
