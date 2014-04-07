#!/bin/bash
######################################################################
# boostrap_develop.sh
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
######################################################################

# Script that gives a summary of changes between two annotated tags.
# Automatically detects the last annotated tag and the previous on.
# This is useful to give information during a release.

# Example output:
# Changes summary between closest annotated tag to current annotated tag
# ======================================================================
#
# ----------------------------------------------------------------------
# Stats for: bitmask_client - 0.3.8..0.5.0
# Stats: 65 files changed, 4384 insertions(+), 1384 deletions(-)
# Merges: 580
# ----------------------------------------------------------------------
# Stats for: leap_pycommon - 0.3.6..0.3.7
# Stats: 9 files changed, 277 insertions(+), 18 deletions(-)
# Merges: 41
# ----------------------------------------------------------------------
# Stats for: soledad - 0.4.4..0.4.5
# Stats: 61 files changed, 5361 insertions(+), 1377 deletions(-)
# Merges: 258
# ----------------------------------------------------------------------
# Stats for: keymanager - 0.3.7..0.3.8
# Stats: 9 files changed, 118 insertions(+), 67 deletions(-)
# Merges: 83
# ----------------------------------------------------------------------
# Stats for: leap_mail - 0.3.8..0.3.9
# Stats: 43 files changed, 9487 insertions(+), 2159 deletions(-)
# Merges: 419
# ----------------------------------------------------------------------
#
# TOTAL
# Stats: 187 files changed, 19627 insertions(+), 5005 deletions(-)
# Merges: 1381

REPOSITORIES="bitmask_client leap_pycommon soledad keymanager leap_mail"

CHANGED=0
INSERTIONS=0
DELETIONS=0
MERGES_TOTAL=0

echo "Changes summary between closest annotated tag to current annotated tag"
echo "======================================================================"
echo
echo "----------------------------------------------------------------------"

for repo in $REPOSITORIES; do
    cd $repo

    LAST_TWO_TAGS=(`git for-each-ref refs/tags --sort=-taggerdate --format='%(refname)' --count=2 | cut -d/ -f3`)
    CURRENT=${LAST_TWO_TAGS[0]}
    PREV=${LAST_TWO_TAGS[1]}

    echo "Stats for: $repo - $PREV..$CURRENT"
    STATS=$(git diff --shortstat $PREV..$CURRENT)
    MERGES=$(git log --merges $PREV..$CURRENT | wc -l)
    echo "Stats:$STATS"
    echo "Merges: $MERGES"
    echo "----------------------------------------------------------------------"

    # Sum all the results for the grand total
    VALUES=(`echo $STATS | awk '{ print $1, $4, $6 }'`)  # use array to store/split values
    CHANGED=$(echo $CHANGED + ${VALUES[0]} | bc)
    INSERTIONS=$(echo $INSERTIONS + ${VALUES[1]} | bc)
    DELETIONS=$(echo $DELETIONS + ${VALUES[2]} | bc)
    MERGES_TOTAL=$(echo $MERGES_TOTAL + $MERGES | bc)

    cd ..
done

echo
echo "TOTAL"
echo "Stats: $CHANGED files changed, $INSERTIONS insertions(+), $DELETIONS deletions(-)"
echo "Merges: $MERGES_TOTAL"
