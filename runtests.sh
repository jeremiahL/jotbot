#!/bin/sh

# setup
set -e
. ./venv/bin/activate
set -x

# tests
pylint server.py screen.py parser.py
python server_test.py
python screen_test.py
python parser_test.py
set +x
echo "All tests passed"
