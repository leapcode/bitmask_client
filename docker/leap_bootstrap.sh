#!/bin/bash
######################################################################
# repo-versions.sh
# Copyright (C) 2014, 2015 LEAP
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
REPOSITORIES="bitmask_client leap_pycommon soledad keymanager leap_mail bitmask_launcher leap_assets"
PACKAGES="leap_pycommon keymanager soledad/common soledad/client leap_mail bitmask_client"

_is_docker() {
    grep -q docker /proc/1/cgroup
}

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}"  )" && pwd  )"

_is_docker && BASE_PATH="/data/" || BASE_PATH=$SCRIPT_DIR
REPOS_ROOT="$BASE_PATH/repositories"  # Root path for all the needed repositories
VENV_DIR="$BASE_PATH/bitmask.venv"  # Root path for all the needed repositories

mkdir -p $REPOS_ROOT

PS4=">> " # for debugging

# Escape code
esc=`echo -en "\033"`

# Set colors
cc_green="${esc}[0;32m"
cc_yellow="${esc}[0;33m"
cc_blue="${esc}[0;34m"
cc_red="${esc}[0;31m"
cc_normal=`echo -en "${esc}[m\017"`

apt_install_dependencies() {
    status="installing system dependencies"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x
    sudo apt-get install -y git python-dev python-setuptools python-virtualenv python-pip libssl-dev python-openssl libsqlite3-dev g++ openvpn pyside-tools python-pyside libffi-dev libzmq-dev
    set +x
}

helpers() {
    if [[ "$1" == "cleanup" ]]; then
        status="removing helper files"
        echo "${cc_green}Status: $status...${cc_normal}"
        set -x
        sudo rm -f /usr/sbin/bitmask-root
        sudo rm -f /usr/share/polkit-1/actions/se.leap.bitmask.policy
        set +x
    else
        status="installing helper files"
        echo "${cc_green}Status: $status...${cc_normal}"
        set -x
        BASE=$REPOS_ROOT/bitmask_client/pkg/linux
        sudo mkdir -p /usr/share/polkit-1/actions/
        sudo cp $BASE/bitmask-root /usr/sbin/
        sudo cp $BASE/polkit/se.leap.bitmask.policy /usr/share/polkit-1/actions/
        set +x
    fi
}

clone_repos() {
    local status="clone repositories"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    if [[ "$1" == "rw" ]]; then
        # read-write remotes:
        src="ssh://gitolite@leap.se"
    else
        # read-only remotes:
        src="https://leap.se/git"
    fi
    cd $REPOS_ROOT

    for repo in $REPOSITORIES; do
        [ ! -d $repo ] && git clone $src/$repo
    done

    cd -

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}

checkout_repos(){
    local status="checkout repositories"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    for repo in $REPOSITORIES; do
        version=$(cat $1 | python -c "import json,sys;obj=json.load(sys.stdin);print obj['$repo'];")
        cd $REPOS_ROOT/$repo
        git fetch origin && git fetch --tags origin

        if [[ -n `git tag -l | grep $version` ]]; then
            # if is a tag
            git checkout -f $version
        else
            # if is a branch
            git reset --hard origin/$version
        fi
    done

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}

create_venv() {
    local status="creating virtualenv"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    virtualenv $VENV_DIR && source $VENV_DIR/bin/activate
    pip install --upgrade pip  # get the latest pip

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

setup_develop() {
    local status="installing packages"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands
    cd $REPOS_ROOT
    source $VENV_DIR/bin/activate

    # do a setup develop in every package
    for package in $PACKAGES; do
        cd $REPOS_ROOT/$package
        python setup.py develop --always-unzip
    done

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

install_dependencies() {
    local status="installing dependencies"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands
    cd $REPOS_ROOT
    source $VENV_DIR/bin/activate

    # install defined 3rd party dependencies for every package
    for package in $PACKAGES; do
        cd $REPOS_ROOT/$package
        pkg/pip_install_requirements.sh --use-leap-wheels
    done

    # symlink system's PySide inside the venv
    $REPOS_ROOT/bitmask_client/pkg/postmkvenv.sh

    # hack to solve gnupg version problem
    pip uninstall -y gnupg && pip install gnupg

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

docker_stuff() {
    local status="doing stuff needed to run bitmask on a docker container"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    helpers
    lxpolkit &
    sleep 0.5

    # this is needed for pkexec
    mkdir -p /var/run/dbus
    dbus-daemon --system | true

    set +x
    echo "${cc_green}Status: $status done.${cc_normal}"
}

run() {
    echo "${cc_green}Status: running client...${cc_normal}"
    set -x

    shift  # remove 'run' from arg list
    passthrough_args=$@

    _is_docker && docker_stuff

    source $VENV_DIR/bin/activate
    python $REPOS_ROOT/bitmask_client/src/leap/bitmask/app.py -d $passthrough_args

    set +x
}

initialize() {
    shift  # remove 'init'
    echo $@
    if [[ "$1" == "ro" ]]; then
        # echo "RO"
        shift  # remove 'ro'
        clone_repos "ro"
    else
        # echo "RW"
        clone_repos
    fi

    if [[ -z $1 ]]; then
        echo "You need to specify a bitmask.json parameter."
        echo "for example:"
    cat << EOF
{
    "bitmask_client": "0.7.0",
    "soledad": "0.6.3",
    "leap_pycommon": "0.3.9",
    "keymanager": "0.3.8",
    "leap_mail": "0.3.10",
    "bitmask_launcher": "0.3.3",
    "leap_assets": "master"
}
EOF
        exit 1
    fi

    JSON=`realpath $1`

    checkout_repos $JSON
    create_venv
    install_dependencies
    setup_develop

    cd $REPOS_ROOT/bitmask_client/
    make
    cd -
}
update() {
    local status="updating repositories"
    echo "${cc_green}Status: $status...${cc_normal}"
    set -x  # show commands

    if [[ -z $1 ]]; then
        echo "You need to specify a bitmask.json parameter."
        echo "for example:"
    cat << EOF
{
    "bitmask_client": "0.7.0",
    "soledad": "0.6.3",
    "leap_pycommon": "0.3.9",
    "keymanager": "0.3.8",
    "leap_mail": "0.3.10",
    "bitmask_launcher": "0.3.3",
    "leap_assets": "master"
}
EOF
        exit 1
    fi

    JSON=`realpath $1`

    checkout_repos $JSON
    install_dependencies
    setup_develop

    set +x
    echo "${cc_green}Status: $status done!${cc_normal}"
}


help() {
    echo ">> LEAP bootstrap - help"
    echo "Bootstraps the environment to start developing the bitmask client"
    echo "with all the needed repositories and dependencies."
    echo
    echo "Usage: $0 {init [ro] bitmask.json | update bitmask.json | run | help | deps | helpers}"
    echo
    echo "    init : Initialize repositories, create virtualenv and \`python setup.py develop\` all."
    echo "           You can use \`init ro\` in order to use the https remotes if you don't have rw access."
    echo "           The bitmask.json file contains the version that will be used for each repo."
    echo "  update : Update the repositories and install new deps (if needed)."
    echo "           The bitmask.json file contains the version that will be used for each repo."
    echo "     run : Runs the client (any extra parameters will be sent to the app)."
    echo "    help : Show this help"
    echo " -- system helpers --"
    echo "    deps : Install the system dependencies needed for bitmask dev (Debian based Linux ONLY)."
    echo " helpers : Install the helper files needed to use bitmask (Linux only)."
    echo "           You can use \`helpers cleanup\` to remove those files."
    echo
}


case "$1" in
    init)
        initialize "$@"
        ;;
    update)
        update $2
        ;;
    helpers)
        helpers $2
        ;;
    deps)
        apt_install_dependencies
        ;;
    run)
        run "$@"
        ;;
    *)
        help
        ;;
esac
