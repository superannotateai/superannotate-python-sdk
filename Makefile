.PHONY: clean tests stress-tests test_coverage install lint docs dist check_formatting

MAKEFLAGS += -j1

PYTHON=python3
PIP=pip3
PYLINT=pylint
PYTESTS=pytest
COVERAGE=coverage

tests: check_formatting docs
	$(PYTESTS) -n auto --full-trace tests

stress-tests: SA_STRESS_TESTS=1
stress-tests: tests

clean:
	rm -rf superannotate.egg-info
	rm -rf build
	rm -rf dist
	rm -rf htmlcov

test_coverage: check_formatting
	-$(PYTESTS) --cov=superannotate -n auto tests
	$(COVERAGE) html
	@echo "\033[95m\n\nCoverage successful! View the output at file://htmlcov/index.html.\n\033[0m"

install:
	$(PIP) install -e .

lint: check_formatting
	-$(PYLINT) --output-format=json superannotate/ | pylint-json2html -o pylint.html

lint_tests:
	-$(PYLINT) tests/*

docs:
	cd docs && make html SPHINXOPTS="-W"
	@echo "\033[95m\n\nBuild successful! View the docs homepage at file://docs/build/html/index.html.\n\033[0m"

dist:
	-rm -rf dist/*
	$(PYTHON) setup.py sdist
	twine upload dist/*

check_formatting:
	yapf -p -r --diff superannotate

docker_run_dev_env: docker_pull_dev_env
	docker run -it -p 8888:8888 \
		-v ${HOME}/.superannotate:/root/.superannotate \
		-v $(pwd):/root/superannotate-python-sdk \
		superannotate/pythonsdk-dev-env

docker_run_dev_env_local_copy: docker_build_dev_env_from_local_copy
	docker run -it -p 8888:8888 \
	    -v ${HOME}/.superannotate:/root/.superannotate \
	    -v $(pwd):/root/superannotate-python-sdk \
	    superannotate/pythonsdk-dev-env \
	    bash -c "pip install -e superannotate-python-sdk && jupyter lab --allow-root --NotebookApp.token='' --NotebookApp.password='' --no-browser --ip 0.0.0.0"

docker_build_dev_env_from_local_copy:
	docker build -t superannotate/pythonsdk-dev-env:latest -f Dockerfile_dev_env .

docker_pull_dev_env:
	docker pull superannotate/pythonsdk-dev-env:latest