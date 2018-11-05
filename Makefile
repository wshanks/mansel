.DEFAULT_GOAL := all

all: lib cli pyqt-cli

init:
	pip install --upgrade pipenv
	pipenv install --dev --skip-lock

lib:
	cd lib && pipenv run python setup.py sdist bdist_wheel

cli:
	cd cli && pipenv run python setup.py sdist bdist_wheel

pyqt-cli:
	cd pyqt-cli && pipenv run python setup.py sdist bdist_wheel

test:
	pipenv run pytest -vvv -s

release: release-lib release-cli release-pyqt-cli

release-lib:
	pipenv run twine upload lib/dist/*

release-cli:
	pipenv run twine upload cli/dist/*

release-pyqt-cli:
	pipenv run twine upload pyqt-cli/dist/*

clean:
	cd lib && rm -rf build dist mansel.egg-info
	cd cli && rm -rf build dist mansel-cli.egg-info
	cd pyqt-cli && rm -rf build dist mansel-pyqt.egg-info

.PHONY: all clean lib cli pyqt-cli release release-lib release-cli release-pyqt-cli test
