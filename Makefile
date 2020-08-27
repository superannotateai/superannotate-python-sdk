.PHONY: all clean tests stress-tests coverage test_coverage install lint docs dist

PYTHON=python3
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
	@echo "\033[95m\n\nCoverage successful! View the output at file://htmlcov/index.html.\n\033[0m"

install:
	pip install .

lint:
	-$(PYLINT) superannotate/
	-$(PYLINT) tests/*

docs:
	cd docs && make html
	@echo "\033[95m\n\nBuild successful! View the docs homepage at file://docs/build/html/index.html.\n\033[0m"

dist:
	-rm -rf dist/*
	$(PYTHON) setup.py sdist
	twine upload dist/*
