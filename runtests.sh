#!/bin/bash

# virtual-env setup
set -e
. ./venv/bin/activate

# run pylint first (currently not on tests)
pylint *.py

# run unittest files
python -m unittest discover --pattern '*_test.py'

echo "All tests passed"
