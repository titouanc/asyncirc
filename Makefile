localtest:
	cd test; python run_all.py

coverage:
	cd test; coverage run --source asyncirc.plugins run_all.py; coverage html
	cd test/htmlcov; google-chrome-stable index.html

clean:
	rm -rf test/htmlcov
	rm -f test/.coverage
	rm -rf build dist

install:
	python setup.py install

test: install
	pip install coverage codacy-coverage
	cd test; python run_all.py
	cd test; coverage run --source asyncirc.plugins run_all.py; coverage report; coverage xml

codacy-coverage: test
	cd test; python-codacy-coverage -r coverage.xml

dev-deps:
	pip install blinker asyncio
	git clone https://github.com/watchtower/asynctest
	cd asynctest; python setup.py install
