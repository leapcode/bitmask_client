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
set -e  # Exit immediately if a command exits with a non-zero status.
REPOSITORIES="bitmask_client leap_pycommon soledad keymanager leap_mail"
PACKAGES="leap_pycommon keymanager soledad/common soledad/client soledad/server leap_mail bitmask_client"
REPOS_ROOT=`pwd`  # Root path for all the needed repositories

PS4=">> " # for debugging

# Escape code
esc=`echo -en "\033"`

# Set colors
cc_green="${esc}[0;32m"
cc_yellow="${esc}[0;33m"
cc_blue="${esc}[0;34m"
cc_red="${esc}[0;31m"
cc_normal=`echo -en "${esc}[m\017"`

clone_repos() {
    status="cloning repositories"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    if [[ "$1" == "ro" ]]; then
        # read-only remotes:
        git clone https://leap.se/git/bitmask_client
        git clone https://leap.se/git/leap_pycommon
        git clone https://leap.se/git/soledad
        git clone https://leap.se/git/keymanager
        git clone https://leap.se/git/leap_mail
    else
        # read-write remotes:
        git clone ssh://gitolite@leap.se/bitmask_client
        git clone ssh://gitolite@leap.se/leap_pycommon
        git clone ssh://gitolite@leap.se/soledad
        git clone ssh://gitolite@leap.se/keymanager
        git clone ssh://gitolite@leap.se/leap_mail
    fi

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}

checkout_develop(){
    status="checkout develop"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    # get the latest develop in every repo
    for repo in $REPOSITORIES; do
        cd $REPOS_ROOT/$repo
        git checkout -f develop
    done

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}

update_repos() {
    status="updating repositories"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    # get the latest develop in every repo
    for repo in $REPOSITORIES; do
        cd $REPOS_ROOT/$repo
        git checkout -f develop
        git fetch origin; git fetch --tags origin
        git reset --hard origin/develop
    done

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}

create_venv() {
    status="creating virtualenv"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    # create and activate the virtualenv
    cd $REPOS_ROOT
    virtualenv bitmask.venv && source ./bitmask.venv/bin/activate

    # symlink PySide to the venv
    cd $REPOS_ROOT/bitmask_client
    ./pkg/postmkvenv.sh

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

setup_develop() {
    status="installing packages"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    # do a setup develop in every package
    for package in $PACKAGES; do
        cd $REPOS_ROOT/$package
        python setup.py develop --always-unzip
    done

    # hack to solve gnupg version problem
    pip uninstall -y gnupg && pip install gnupg

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

finish(){
    echo "${cc_green}Status: process completed.${cc_normal}"
    echo "You can run the client with the following command:"
    echo -n "${cc_yellow}"
    echo "    shell> source bitmask.venv/bin/activate"
    echo "    shell> python bitmask_client/src/leap/bitmask/app.py -d"
    echo "${cc_normal}"
    echo "or with this script using:"
    echo "${cc_yellow}    shell> $0 run${cc_normal}"
    echo
}

initialize() {
    clone_repos $1
    checkout_develop
    create_venv
    setup_develop

    # make: compile ui and resources in client
    make

    finish
}

update() {
    update_repos

    source $REPOS_ROOT/bitmask.venv/bin/activate

    setup_develop

    # make: compile ui and resources in client
    make

    finish
}

run() {
    echo "${cc_green}Status: running client...${cc_normal}"
    source bitmask.venv/bin/activate
    set -x
    python bitmask_client/src/leap/bitmask/app.py -d $*
    set +x
}

help() {
    echo ">> LEAP developer helper"
    echo "Bootstraps the environment to start developing the bitmask client"
    echo "with all the needed repositories and dependencies."
    echo
    echo "Usage: $0 {init | update | help}"
    echo
    echo "   init : Initialize repositories, create virtualenv and \`python setup.py develop\` all."
    echo "          You can use \`init ro\` in order to use the https remotes if you don't have rw access."
    echo " update : Update the repositories and install new deps (if needed)."
    echo "    run : Runs the client (any extra parameters will be sent to the app)."
    echo "   help : Show this help"
    echo
}

case "$1" in
    init)
        initialize $2
        ;;
    update)
        update
        ;;
    run)
        run
        ;;
    *)
        help
        ;;
esac
