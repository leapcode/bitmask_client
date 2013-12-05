#!/bin/bash

#Wraps a command in a virtualenwrapper passed as first argument.
#Example:
#with_virtualenvwrapper.sh leap-bitmask ./run_tests.sh

alias pyver='python -c "import $1;print $1.__path__[0]; print $1.__version__;"'

source `which virtualenvwrapper.sh`
workon $1
echo "running version: " `pyver leap.bitmask`
$2 $3 $4 $5
