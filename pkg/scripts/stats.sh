#!/bin/bash

REPOSITORIES="bitmask_client leap_pycommon soledad keymanager leap_mail"

CHANGED=0
INSERTIONS=0
DELETIONS=0
MERGES_TOTAL=0

echo "Changes summary between closest annotated tag to HEAD"
echo "====================================================="
echo

for repo in $REPOSITORIES; do
    cd $repo
    echo "Stats for: $repo"
    # the 'describe' command gives the closest annotated tag
    STATS=$(git diff --shortstat `git describe --abbrev=0`..HEAD)
    MERGES=$(git log --merges `git describe --abbrev=0`..HEAD | wc -l)
    echo "Stats:$STATS"
    echo "Merges: $MERGES"
    VALUES=(`echo $STATS | awk '{ print $1, $4, $6 }'`)  # use array to store values
    CHANGED=$(echo $CHANGED + ${VALUES[0]} | bc)
    INSERTIONS=$(echo $INSERTIONS + ${VALUES[1]} | bc)
    DELETIONS=$(echo $DELETIONS + ${VALUES[2]} | bc)
    MERGES_TOTAL=$(echo $MERGES_TOTAL + $MERGES | bc)
    echo "----------------------------------------------------------------------"
    cd ..
done

echo
echo "TOTAL"
echo "Stats: $CHANGED files changed, $INSERTIONS insertions(+), $DELETIONS deletions(-)"
echo "Merges: $MERGES_TOTAL"
