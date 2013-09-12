#!/bin/bash

# Installs requirements, and
# clones the latest leap-client

# depends on:
# openvpn git-core libgnutls-dev python-dev python-qt4 python-setuptools python-virtualenv

# Escape code
esc=`echo -en "\033"`

# Set colors
cc_green="${esc}[0;32m"
cc_yellow="${esc}[0;33m"
cc_blue="${esc}[0;34m"
cc_red="${esc}[0;31m"
cc_normal=`echo -en "${esc}[m\017"`

echo "${cc_yellow}"
echo "~~~~~~~~~~~~~~~~~~~~~~~"
echo " Bitmask bootstrapping "
echo "~~~~~~~~~~~~~~~~~~~~~~~"
echo ""
echo "${cc_green}Creating virtualenv...${cc_normal}"

mkdir bitmask-testbuild
virtualenv bitmask-testbuild
source bitmask-testbuild/bin/activate

echo "${cc_green}Installing bitmask...${cc_normal}"

# Clone latest git (develop branch)
# change "develop" for any other branch you want.


pip install -e 'git://leap.se/leap_client@develop#egg=leap.bitmask'

cd bitmask-testbuild

# symlink the pyside libraries to the system libs
./src/leap.bitmask/pkg/postmkvenv.sh

echo "${cc_green}bitmask installed! =)"
echo "${cc_yellow}"
echo "Launch it with: "
echo "~~~~~~~~~~~~~~~~~~~~~~"
echo "bin/bitmask"
echo "~~~~~~~~~~~~~~~~~~~~~~"
echo "${cc_normal}"
