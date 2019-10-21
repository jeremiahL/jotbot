#!/bin/sh

# setup
set -e
. ./venv/bin/activate
set -x

# tests
pylint server.py
python tests.py
set +x
echo "All tests passed"
