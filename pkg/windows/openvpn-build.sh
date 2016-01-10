#!/bin/bash

# render openvpn prepared for installer
# ================================================
#
# requires
#  - a linux host with mingw installed
#  - a rw directory mounted to /var/build
#  returns nonzero exit code when failed
#
# clone openvpn-build repository
# runs cross-compile build
# - downloads openvpn dependencies
# - compiles
# copy files to executables so they can be installed
# cleans up (remove read-write copy)

# the location where the openvpn binaries are placed
absolute_executable_path=/var/build/executables
temporary_build_path=/var/build/openvpn

# cleanup the temporary build path for subsequent executes
function cleanup() {
  rm -r ${temporary_build_path} 2>/dev/null
}
# build openvpn source
function buildSource() {
  pushd ${temporary_build_path}/openvpn-build/generic
  CHOST=i686-w64-mingw32 \
  CBUILD=i686-pc-linux-gnu \
  ./build \
  || die 'build openvpn from source failed'
  cp -r image/openvpn ${absolute_executable_path}/openvpn
  popd
}
# fetch tap-windows.exe as defined in the openvpn vars
function fetchTapWindows() {
  pushd ${temporary_build_path}/openvpn-build
  source windows-nsis/build-complete.vars
  wget ${TAP_WINDOWS_INSTALLER_URL} -O ${absolute_executable_path}/openvpn/tap-windows.exe || die 'tap-windows.exe could not be fetched'
  popd
}
# prepare read-write copy
function prepareBuildPath() {
  cleanup
  mkdir -p ${temporary_build_path}
  pushd ${temporary_build_path}
  git clone https://github.com/OpenVPN/openvpn-build || die 'openvpn-build could not be cloned'
  popd
}
# display failure message and emit non-zero exit code
function die() {
  echo "die:" $@
  exit 1
}
function main() {
  prepareBuildPath
  buildSource
  fetchTapWindows
  cleanup
}
main $@