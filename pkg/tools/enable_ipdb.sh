#!/bin/sh

# This script installs modules needed for using IPythin debug shell in a
# Bitmask bundle directory. It uses a python virtual environment in which it
# installs needed modules and then links them into the appropriate directory
# inside the bundle directory.

MODULES="ast.py runpy.py"
SITE_MODULES="ipdb IPython simplegeneric.py decorator.py pexpect"

if [ $# != 1 ]; then
  echo "Usage: $0 bundle_path"
  exit 1
fi

BUNDLE_PATH=`echo $1 | sed -e "s/\/\$//"`
BUNDLE_LIB=${BUNDLE_PATH}/lib
BUNDLE_VENV=${BUNDLE_PATH}/.venv

function check_bundle_dirs() {
  if [ ! -d ${BUNDLE_PATH} ]; then
    echo "Argument ${BUNDLE_PATH} is not a directory."
    exit 2
  fi

  if [ ! -d ${BUNDLE_LIB} ]; then
    echo "Expected library directory ${BUNDLE_LIB} is not a directory."
    exit 2
  fi

  if [ ! -w ${BUNDLE_LIB} ]; then
    echo "Directory ${BUNDLE_LIB} is not writable."
    exit 2
  fi
}

function confirm_installation() {
  echo -n "Are you sure you want to enable IPython debugger in ${BUNDLE_PATH} (y/N)? "
  read confirm
  if [[ "${confirm}" != "y" && "${confirm}" != "Y" ]]; then
    echo "Bailing out..."
    exit 0
  fi
}

function setup_virtualenv() {
  if [ ! -d ${BUNDLE_VENV} ]; then
    virtualenv ${BUNDLE_VENV}
  fi
  source ${BUNDLE_VENV}/bin/activate
  pip install ipdb
}

function link_modules() {
  for package in ${MODULES}; do
    package_path=${BUNDLE_LIB}/${package}
    if [[ ! -f ${package_path} && ! -d ${package_path} ]]; then
      ln -sf /usr/lib/python2.7/${package} ${BUNDLE_LIB}
    fi
  done
  for package in ${SITE_MODULES}; do
    package_path=${BUNDLE_LIB}/${package}
    if [[ ! -f ${package_path} && ! -d ${package_path} ]]; then
      ln -sf ${BUNDLE_VENV}/lib/python2.7/site-packages/${package} ${BUNDLE_LIB}
    fi
  done
}

function main() {
  check_bundle_dirs
  confirm_installation
  setup_virtualenv
  link_modules
  echo "All done."
  exit 0
}

main
