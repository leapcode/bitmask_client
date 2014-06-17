#!/bin/bash

# File: leap-install-helper.sh
# Copy the needed binaries and helper files to their destination.
# Copyright (C) 2014 LEAP Encryption Access Project.
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

LOCAL_SBIN_FOLDER=/usr/local/sbin

POLKIT_FOLDER="/usr/share/polkit-1/actions"
POLKIT_FILE="se.leap.bitmask.bundle.policy"
POLKIT_PATH="${POLKIT_FOLDER}/${POLKIT_FILE}"

BITMASK_ROOT_FILE="bitmask-root"
BITMASK_ROOT_PATH="${LOCAL_SBIN_FOLDER}/${BITMASK_ROOT_FILE}"

OPENVPN_FILE="leap-openvpn"
OPENVPN_PATH="${LOCAL_SBIN_FOLDER}/${OPENVPN_FILE}"

# The following array stores global files that have been deprecated and we want
# to remove from the system path, after having dropped them there in the past.

DEPRECATED_FILES=(
  '/usr/share/polkit-1/actions/net.openvpn.gui.leap.policy'
)


# Variables for parsing and storing the script options.

FROM_PATH=NONE
REMOVE_OLD_FILES=NO
INSTALL_BITMASK_ROOT=NO
INSTALL_POLKIT_FILE=NO
INSTALL_OPENVPN=NO


# Process the options

while [[ $# > 1 ]]
do
key="$1"
shift

case $key in
    -f|--from-path)
    FROM_PATH="$1"
    shift
    ;;
    -r|--remove-old-files)
    REMOVE_OLD_FILES="$1"
    shift
    ;;
    --install-bitmask-root)
    INSTALL_BITMASK_ROOT="$1"
    shift
    ;;
    --install-polkit-file)
    INSTALL_POLKIT_FILE="$1"
    shift
    ;;
    --install-openvpn)
    INSTALL_OPENVPN="$1"
    shift
    ;;
    *)
    # unknown option
    ;;
esac
done
echo "LEAP_INSTALL_HELPER"
echo "-------------------"
echo FROM_PATH	          = "${FROM_PATH}"
echo REMOVE_OLD_FILES     = "${REMOVE_OLD_FILES}"
echo INSTALL_BITMASK_ROOT = "${INSTALL_BITMASK_ROOT}"
echo INSTALL_POLKIT_FILE  = "${INSTALL_POLKIT_FILE}"
echo INSTALL_OPENVPN      = "${INSTALL_OPENVPN}"
echo


#
# helper functions
#

function check_current_uid() {
  current_uid=`id | sed 's/^uid=//;s/(.*$//'`
  if [ $current_uid != 0 ]
  then
    echo "[ERROR] NEED TO BE RUN AS ROOT"
    exit 1
  fi
}

function check_from_path() {
  if [ $FROM_PATH == NONE ]
  then
    echo "[ERROR] YOU NEED TO GIVE --from-path VALUE..."
    exit 1
  fi
}

function remove_old_files() {
  for file in "${DEPRECATED_FILES[@]}"
  do
    rm $file
  done
}

function copy_bitmask_root() {
  mkdir -p "${LOCAL_SBIN_FOLDER}"
  cp "${FROM_PATH}/${BITMASK_ROOT_FILE}" "${BITMASK_ROOT_PATH}"
  chmod 744 "${BITMASK_ROOT_PATH}"

}

function copy_polkit_file() {
  cp "${FROM_PATH}/${POLKIT_FILE}" "${POLKIT_PATH}"
  chmod 644 "${POLKIT_PATH}"
}

function copy_openvpn_file() {
  mkdir -p "${LOCAL_SBIN_FOLDER}"
  cp "${FROM_PATH}/${OPENVPN_FILE}" "${OPENVPN_PATH}"
  chmod 744 "${OPENVPN_PATH}"

}


#
# Process options and run functions.
#

check_current_uid

if [ $INSTALL_BITMASK_ROOT == YES ] || [ $INSTALL_POLKIT_FILE == YES ] || [ $INSTALL_OPENVPN == YES ]
then
  check_from_path
fi

if [ $REMOVE_OLD_FILES == YES ]
then
  echo "REMOVING OLD FILES..."
  remove_old_files
fi

if [ $INSTALL_BITMASK_ROOT == YES ]
then
  echo "INSTALLING bitmask-root..."
  copy_bitmask_root
fi

if [ $INSTALL_POLKIT_FILE == YES ]
then
  echo "INSTALLING policykit file..."
  copy_polkit_file
fi

if [ $INSTALL_OPENVPN == YES ]
then
  echo "INSTALLING openvpn..."
  copy_openvpn_file
fi
