install:
	python setup.py install

test: install
	cd test; python run_all.py

dev-deps:
	pip install blinker asyncio
	git clone https://github.com/watchtower/asynctest
	cd asynctest; python setup.py install
