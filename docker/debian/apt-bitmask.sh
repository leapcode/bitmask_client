#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

distro(){
    # for ubuntu/mint:
    name=`lsb_release -a 2>&1 | grep Codename | cut -f2`

    # for debian:
    [[ -z $name ]] && name=`grep -oP "VERSION=.*\(\K\w+" /etc/os-release`

    # for debian sid
    [[ -z $name ]] && name=`grep -o sid /etc/debian_version`

    declare -A distros
    distros=(
        ['nadia']='quantal'
        ['olivia']='raring'
        ['petra']='saucy'
        ['qiana']='trusty'
        ['rebecca']='trusty'
        ['rafaela']='trusty'
    )

    # if name is in the above list -> replace
    [ ${distros[$name]+abc} ] && name=${distros[$name]}

    echo $name | tr "[A-Z]" "[a-z]"
}

is_supported(){
    distros=(
        # 'wheezy'  # Debian 7 - stable
        'jessie'  # Debian 8 - testing
        'sid'     # Debian unstable
        # 'quantal' # Ubuntu 12.10
        # 'raring'  # Ubuntu 13.04
        # 'saucy'   # Ubuntu 13.10
        # 'trusty'  # Ubuntu 14.04
        # 'utopic'  # Ubuntu 14.10
        'vivid'   # Ubuntu 15.04
        'wily'    # Ubuntu 15.10
    )

    my_distro=`distro`

    for p in "${distros[@]}"; do
        if [[ $my_distro = ${p}* ]]; then
            echo true
            return
        fi
    done
    echo false
}

if [[ `is_supported` == "false" ]]; then
    echo "ERROR: Sorry, your distro (`distro`) is currently not supported."
    exit 1
fi;

help() {
    echo ">> Bitmask .deb automatic installer helper"
    echo "This script does all the needed stuff in order to get bitmask stable or unstable into your machine."
    echo
    echo "Usage: $0 ( stable | unstable | help )"
    echo
    echo "   stable : Install the stable bitmask package."
    echo " unstable : Install the unstable bitmask package."
    echo "     help : Show this help"
    echo
    echo "NOTE: you need to run this with root privileges."
    echo
}

case ${1:-} in
    stable)
        REPO='debian'
        ;;
    unstable)
        REPO='experimental'
        ;;
    *)
        help
        exit 1
        ;;
esac

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

# -------------------------------
# instructions from http://deb.leap.se/experimental/
# run this with admin privileges

DISTRO=`distro`

if [[ $REPO == 'debian' ]]; then
    # stable
    # wget -O- https://dl.bitmask.net/apt.key | apt-key add -

    # HACK: do this twice since the first one fails due to gpg not having a configuration
    gpg --recv-key 0x1E34A1828E207901 &> /dev/null || true
    gpg --recv-key 0x1E34A1828E207901

    gpg --armor --export 0x1E34A1828E207901  | apt-key add -
else  # $REPO == 'experimental'
    if [[ ! -f "leap-experimental.key" ]]; then
        echo "ERROR: you need to copy the leap-experimental.key file into this directory."
        exit 1
    fi

    # sha256sum leap-experimental.key
    echo "ed3f4f3e3e0835a044457451755ae743741d7bafa55bcd31cc464a54e8c5e7f9  leap-experimental.key" | sha256sum -c -
    apt-key add leap-experimental.key
fi

echo "deb http://deb.leap.se/$REPO $DISTRO main" > /etc/apt/sources.list.d/bitmask.list
echo "deb-src http://deb.leap.se/$REPO $DISTRO main" >> /etc/apt/sources.list.d/bitmask.list

apt-get update
apt-get install -y bitmask
