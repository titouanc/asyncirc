import importlib
test_suites = ["core", "tracking"]

failures = 0

for suite in test_suites:
    print("Running suite {}...".format(suite))
    failures += importlib.import_module(suite).manager.run_all()

print("{} total failures.".format(failures))

import sys
sys.exit(min(failures, 1))
