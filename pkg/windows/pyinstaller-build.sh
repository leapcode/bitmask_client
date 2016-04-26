#!/bin/bash

# render dependencies into separate subdirectories
# ================================================
#
# requires
#  - a linux host with wine, wine with python and mingw installed
#  - the sourcecode mounted to /var/src/
#  - a rw directory mounted to /var/build
#  returns nonzero exit code when pyinstaller failed
#
# prepares a read-write copy of the sourcecode
# executes qt-uic and qt-rcc for gui dialogs
# installs dependencies from pkg/dependencies-windows.pip
# runs pyinstaller
# cleans up (remove wine-dlls, remove read-write copy)
# creates nsis install/uninstall scripts for the files for each package
# if $1 is set it is expected to be a branch/git-tag

product=bitmask
# the location where the pyinstaller results are placed
absolute_executable_path=/var/build/executables
# the location of the nsis installer nis files dictates the path of the files
relative_executable_path=../../build/executables
source_ro_path=/var/src/${product}
temporary_build_path=/var/build/pyinstaller
git_tag=HEAD
version_prefix=leap.bitmask
git_version=unknown
# option that is changed when a dependency-cache is found
install_dependencies=true
# default options for components
with_eip=false
with_mail=true

setups=($(ls -1 ${source_ro_path}/pkg/windows | grep '.nis$' | sed 's|.nis$||'))
# add mingw dlls that are build in other steps
function addMingwDlls() {
  root=$1
  cp /usr/lib/gcc/i686-w64-mingw32/4.9-win32/libgcc_s_sjlj-1.dll ${root}
  cp /root/.wine/drive_c/Python27/Lib/site-packages/zmq/libzmq.pyd ${root}
  cp /root/.wine/drive_c/Python27/Lib/site-packages/zmq/libzmq.pyd ${root}
  mkdir -p ${root}/pysqlcipher
  cp /var/build/pyinstaller/pkg/pyinst/build/bitmask/pysqlcipher-2.6.4-py2.7-win32.egg/pysqlcipher/_sqlite.pyd ${root}/pysqlcipher
  cp ~/.wine/drive_c/openssl/bin/*.dll ${root}
}
# cleanup the temporary build path for subsequent executes
function cleanup() {
  rm -rf ${temporary_build_path} 2>/dev/null
}
# create files that are not part of the repository but are needed
# in the windows environment:
# - license with \r\n
# - ico from png (multiple sizes for best results on high-res displays)
function createInstallablesDependencies() {
  pushd ${temporary_build_path} > /dev/null
  cat LICENSE | sed 's|\n|\r\n|g' > LICENSE.txt
  convert data/images/mask-icon.png  -filter Cubic -scale 256x256! data/images/mask-icon-256.png
  convert data/images/mask-icon-256.png -define icon:auto-resize data/images/mask-icon.ico
  # execute qt-uic / qt-rcc
  wine mingw32-make all || die 'qt-uic / qt-rcc failed'
  # get version using git (only available in host)
  git_version=$(python setup.py version| grep 'Version is currently' | awk -F': ' '{print $2}')
  # run setup.py in a path with the version contained so versioneer can
  # find the information and put it into the egg
  versioned_build_path=/var/tmp/${version_prefix}-${git_version}
  mkdir -p ${versioned_build_path}
  cp -r ${temporary_build_path}/* ${versioned_build_path}
  # apply patches to the source that are required for working code
  # should not be required in the future as it introduces possible
  # hacks that are hard to debug
  applyPatches ${versioned_build_path}
  pushd ${versioned_build_path} > /dev/null
  # XXX what's this update_files command?
  #wine python setup.py update_files || die 'setup.py update_files failed'
  wine python setup.py build || die 'setup.py build failed'
  wine python setup.py install || die 'setup.py install failed'
  popd
  rm -rf ${versioned_build_path}
  popd
}
# create installer version that may be used by installer-build.sh / makensis
# greps the version-parts from the previously extracted git_version and stores
# the result in a setup_version.nsh
# when the git_version does provide a suffix it is prefixed with a dash so the
# installer output needs no conditional for this
function createInstallerVersion() {
  setup=$1
  # [0-9]*.[0-9]*.[0-9]*-[0-9]*_g[0-9a-f]*_dirty
  VERSIONMAJOR=$(echo ${git_version} | sed 's|^\([0-9]*\)\..*$|\1|')
  VERSIONMINOR=$(echo ${git_version} | sed 's|^[0-9]*\.\([0-9]*\).*$|\1|')
  VERSIONBUILD=$(echo ${git_version} | sed 's|^[0-9]*\.[0-9]*\.\([0-9]*\).*$|\1|')
  VERSIONSUFFIX=$(echo ${git_version} | sed 's|^[0-9]*\.[0-9]*\.[0-9]*-\(.*\)$|\1|')
  echo "!define VERSIONMAJOR ${VERSIONMAJOR}" > ${absolute_executable_path}/${setup}_version.nsh
  echo "!define VERSIONMINOR ${VERSIONMINOR}" >> ${absolute_executable_path}/${setup}_version.nsh
  echo "!define VERSIONBUILD ${VERSIONBUILD}" >> ${absolute_executable_path}/${setup}_version.nsh
  if [ ${VERSIONSUFFIX} != "" ]; then
    VERSIONSUFFIX="-${VERSIONSUFFIX}"
  fi
  echo "!define VERSIONSUFFIX ${VERSIONSUFFIX}" >> ${absolute_executable_path}/${setup}_version.nsh
}
# create installable binaries with dlls
function createInstallables() {
  mkdir -p ${absolute_executable_path}
  pushd ${temporary_build_path}/pkg/pyinst
  # build install directories (contains multiple files with pyd,dll, some of
  # them look like windows WS_32.dll but are from wine)
  for setup in ${setups[@]}
  do
    # --clean do not cache anything and overwrite everything --noconfirm
    # --distpath to place on correct location
    # --debug to see what may be wrong with the result
    # --paths=c:\python\lib\site-packages;c:\python27\lib\site-packages
    wine pyinstaller \
      --clean \
      --noconfirm \
      --distpath=.\\installables \
      --paths=Z:\\var\\build\\pyinstaller\\src\\ \
      --paths=C:\\Python27\\Lib\\site-packages\\ \
      --debug \
      ${setup}.spec \
    || die 'pyinstaller for "'${setup}'" failed'
    removeWineDlls installables/${setup}
    addMingwDlls installables/${setup}
    rm -r ${absolute_executable_path}/${setup}
    cp -r installables/${setup} ${absolute_executable_path}
    cp ${absolute_executable_path}/cacert.pem ${absolute_executable_path}/${setup}
    rm -r installables
    createInstallerVersion ${setup}
  done
  popd
  pushd ${temporary_build_path}
  cp data/images/mask-icon.ico ${absolute_executable_path}/
  popd
}
# install (windows)dependencies of project
function installProjectDependencies() {
  pushd ${temporary_build_path} > /dev/null
  unsupported_packages="dirspec"
  pip_flags="--find-links=Z:${temporary_build_path}/wheels"
  for unsupported_package in ${unsupported_packages}
  do
    pip_flags="${pip_flags} --allow-external ${unsupported_package} --allow-unverified ${unsupported_package}"
  done
  pip_flags="${pip_flags} -r"

  # install dependencies
  mkdir -p ${temporary_build_path}/wheels
  wine pip install ${pip_flags} pkg/requirements-leap.pip || die 'requirements-leap.pip could not be installed'
  # fix requirements
  # python-daemon breaks windows build
  sed -i 's|^python-daemon|#python-daemon|' pkg/requirements.pip
  wine pip install ${pip_flags} pkg/requirements.pip || die 'requirements.pip could not be installed'
  git checkout pkg/requirements.pip
  popd
  cp -r /root/.wine/drive_c/Python27/Lib/site-packages ${absolute_executable_path}
  curl https://curl.haxx.se/ca/cacert.pem > ${absolute_executable_path}/cacert.pem || die 'cacert.pem could not be fetched - would result in bad ssl in installer'
}
# workaround for broken dependencies
# runs before pip install requirements
# fixes failure for pysqlcipher as this requests a https file that the
# windows-python fails to request
function installProjectDependenciesBroken() {
  pushd ${temporary_build_path} > /dev/null
  curl https://pypi.python.org/packages/source/p/pysqlcipher/pysqlcipher-2.6.4.tar.gz \
    > pysqlcipher-2.6.4.tar.gz \
    || die 'fetch pysqlcipher failed'
  tar xzf pysqlcipher-2.6.4.tar.gz
  pushd pysqlcipher-2.6.4
  curl https://downloads.leap.se/libs/pysqlcipher/amalgamation-sqlcipher-2.1.0.zip \
    > amalgamation-sqlcipher-2.1.0.zip \
    || die 'fetch amalgamation for pysqlcipher failed'
  unzip -o amalgamation-sqlcipher-2.1.0.zip || die 'unzip amalgamation failed'
  mv sqlcipher amalgamation
  patch -p0 < ${source_ro_path}/pkg/windows/pyinstaller/pysqlcipher_setup.py.patch \
    || die 'patch pysqlcipher setup.py failed'
  wine python setup.py build install || die 'setup.py for pysqlcipher failed'
  popd
  popd # temporary_build_path
}
# prepare read-write copy
function prepareBuildPath() {
  cleanup
  # ensure shared openssl for all pip builds
  test -d ${absolute_executable_path}/openvpn || die 'openvpn not available run docker-compose run --rm openvpn'
  cp -r ${absolute_executable_path}/openvpn /root/.wine/drive_c/openssl
  if [ -d ${absolute_executable_path}/site-packages ]; then
    # use pip install cache for slow connections
    rm -r /root/.wine/drive_c/Python27/Lib/site-packages
    cp -r ${absolute_executable_path}/site-packages /root/.wine/drive_c/Python27/Lib/
    install_dependencies=false
  fi
  if [ ! -z $1 ]; then
    git_tag=$1
  fi
  if [ ${git_tag} != "HEAD" ]; then
    echo "using ${git_tag} as source for the project"
    git clone ${source_ro_path} ${temporary_build_path}
    pushd ${temporary_build_path}
    git checkout ${git_tag} || die 'checkout "'${git_tag}'" failed'
    popd
  else
    echo "using current source tree for build"
    mkdir -p ${temporary_build_path}/data
    mkdir -p ${temporary_build_path}/docs
    mkdir -p ${temporary_build_path}/pkg
    mkdir -p ${temporary_build_path}/src
    mkdir -p ${temporary_build_path}/.git
    cp -r ${source_ro_path}/data/* ${temporary_build_path}/data
    cp -r ${source_ro_path}/data/* ${temporary_build_path}/docs
    cp -r ${source_ro_path}/pkg/* ${temporary_build_path}/pkg
    cp -r ${source_ro_path}/src/* ${temporary_build_path}/src
    cp -r ${source_ro_path}/.git/* ${temporary_build_path}/.git
    cp ${source_ro_path}/* ${temporary_build_path}/
  fi
}
# add patches to the sourcetree
# this function should do nothing some day and should be run after
# the version has been evaluated
function applyPatches() {
  root_path=$1
  # disable eip
  if [ !${with_eip} ]; then
    sed -i "s|HAS_EIP = True|HAS_EIP = False|" ${root_path}/src/leap/bitmask/_components.py
  fi
  # disable mail
  if [ !${with_mail} ]; then
    sed -i "s|HAS_MAIL = True|HAS_MAIL = False|" ${root_path}/src/leap/bitmask/_components.py
  fi
  # hack the logger
  sed -i "s|'bitmask.log'|str(random.random()) + '_bitmask.log'|;s|import sys|import sys\nimport random|" ${root_path}/src/leap/bitmask/logs/utils.py
  sed -i "s|perform_rollover=True|perform_rollover=False|" ${root_path}/src/leap/bitmask/app.py
  # fix requirements
  # python-daemon breaks windows build
  sed -i 's|^python-daemon|#python-daemon|' ${root_path}/pkg/requirements.pip
}
# remove wine dlls that should not be in the installer
# root: path that should be cleaned from dlls
function removeWineDlls() {
  root=$1
  declare -a wine_dlls=(\
    advapi32.dll \
    comctl32.dll \
    comdlg32.dll \
    gdi32.dll \
    imm32.dll \
    iphlpapi.dll \
    ktmw32.dll \
    msvcp90.dll \
    msvcrt.dll \
    mswsock.dll \
    mpr.dll \
    netapi32.dll \
    ole32.dll \
    oleaut32.dll \
    opengl32.dll \
    psapi.dll \
    rpcrt4.dll \
    shell32.dll \
    user32.dll \
    version.dll \
    winmm.dll \
    winspool.drv \
    ws2_32.dll \
    wtsapi32.dll \
    )
  for wine_dll in "${wine_dlls[@]}"
  do
    # not all of the listed dlls are in all directories
    rm ${root}/${wine_dll} 2>/dev/null
  done
}
# display failure message and emit non-zero exit code
function die() {
  echo "die:" $@
  exit 1
}
function main() {
  prepareBuildPath $@
  if [ ${install_dependencies} == true ]; then
    installProjectDependenciesBroken
    installProjectDependencies
  fi
  createInstallablesDependencies
  createInstallables
  cleanup
}
main $@
