#!/bin/bash
######################################################################
# bitmask_boostrap.sh
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
# Installs requirements, and
# clones the latest leap-client

# depends on:
# (authoritative list under docs/dev/quickstart.rst)

# git python-dev python-setuptools python-virtualenv python-pip python-openssl libsqlite3-dev g++ openvpn
# pyside-tools python-pyside python-qt4

# Clone latest git (develop branch)
# change "develop" for any other branch you want.
BRANCH="develop"
BITMASK_DIR="bitmask-develop"

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

mkdir ${BITMASK_DIR}
virtualenv "${BITMASK_DIR}"
source ./${BITMASK_DIR}/bin/activate

echo "${cc_green}Installing bitmask...${cc_normal}"

pip install -e 'git+https://leap.se/git/bitmask_client@'${BRANCH}'#egg=leap.bitmask'

cd ${BITMASK_DIR}

# symlink the pyside libraries to the system libs
./src/leap.bitmask/pkg/postmkvenv.sh

cd ./src/leap.bitmask
make
cd ../../
source ./bin/activate

echo "${cc_green}bitmask installed! =)"
echo "${cc_yellow}"
echo "Launch it with: "
echo "~~~~~~~~~~~~~~~~~~~~~~"
echo "bin/bitmask --debug"
echo "~~~~~~~~~~~~~~~~~~~~~~"
echo "If you are not inside the virtualenv, source it first with "
echo "source "${BITMASK_DIR}"/bin/activate"
echo "${cc_normal}"
