#!/bin/bash

# Escape code
esc=`echo -en "\033"`

# Set colors
cc_green="${esc}[0;32m"
cc_red="${esc}[0;31m"
cc_normal=`echo -en "${esc}[m\017"`


[[ -z "$1" ]] && WHERE='src/leap/bitmask' || WHERE=$1

PEP8="pep8 --ignore=E202,W602 --exclude=*_rc.py,ui_*,_version.py $WHERE"
echo "${cc_green}$PEP8${cc_normal}"
$PEP8

echo
FLAKE8="flake8 --ignore=E202,W602 --exclude=*_rc.py,ui_*,_version.py $WHERE"
echo "${cc_green}$FLAKE8${cc_normal}"
$FLAKE8

echo
echo "${cc_green}Looking for 'print's, no prints in code, use logging/twisted.log.${cc_normal}"
echo `git grep -n "print " | wc -l` 'coincidences.'

echo
echo "${cc_green}Grepping for 'pdb' code left behind.${cc_normal}"
git grep -n "pdb"

echo
echo "${cc_green}Grepping for 'XXX|TODO|FIXME|NOTE|HACK'.${cc_normal}"
echo `git grep -E "XXX|TODO|FIXME|NOTE|HACK" | wc -l` 'coincidences.'
