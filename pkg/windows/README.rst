Environment setup in debian:jessie
==================================

basically you need this to setup your environment:

# apt-get install mingw-w64
# apt-get install wine
# apt-get install nsis

this is a incomplete list of dependencies, review the pyinstaller/Dockerfile
to get a understanding of what needs to be setup in order to have a
environment that builds the installer

Requirements
============

docker-compose

Building the package
====================

make pkg


Reproducible builds
===================

please run the binary and installer builds on a clean machine eg
using docker or any virtual environment that can easily be prepared
by a third party to verify that the binaries are actually what the
sourcecode suggests.

to use reproducible build you need to install docker which then installs
a clean debian:jessie to install nsis or the mingw environment


Installer
=========

NSIS was choosen because it provided a out of the box toolchain to build
installers for the windows platform with minimal dependencies. The downside
of nsis is that it does not produce msi binaries

to build the binary dependencies run:

```
docker-compose run --rm openvpn
docker-compose run --rm pyinstaller
```

the produced binaries will be stored in ${ROOT}/build

to build the installer run:

```
docker-compose run --rm installer
```

the produced installer will be stored in ${ROOT}/dist


Pyinstaller
===========

Pyinstaller is a docker image based on debian:jessie with a cross-compile
toolchain (gcc) for building zlib and openssl in linux and wine (staging)
with installed python and mingw32 for pip/wheel compiling.
All pip installed dependencies are
part of the pyinstaller-build.sh script so they can be re-executed when the
dependencies of the project change. The image should be rebuild when openssl,
python or pyinstaller is updated:

```
docker-compose build pyinstaller
```

To debug or fine-tune the compile process it may be useful to setup the
following software on the development machine:

```
X :1 -listen tcp
DISPLAY=:1 xhost +
docker-compose run --rm pyinstaller /bin/bash
root@0fa19215321f:/# export DISPLAY=${YOUR_LOCAL_IP}:1
root@0fa19215321f:/# wine cmd
Z:\>python
>>>
```

the configured volumes are:

- the (read-only) sourcecode of the bitmask project in /var/src/bitmask
- the result of the builds in /var/build

pyinstaller-build.sh
====================

Contains all steps to build the win32 executables. The project relies on
a read-write source tree which will pollute the development environment and
make it hard to reproduce 'clean' builds. therefore it expects that the source
is freshly checked out and not used to run in the host-environment. Otherwise
pyc and ui elements will mess up the binary in unpredictable ways.

* copy the /var/src/bitmask sources to a read-write location (/var/build)
* execute ```make all``` in wine to build the qt ui and other resources
* execute ```pip install $dependencies``` to have all dependencies available
* execute ```pyinstaller``` in wine to compile the executable for
** bitmask (src/leap/bitmask/app.py)
* cleanup
** remove the read-write copy
** remove wine-dlls from the installer

As the step 'install dependencies' may take long on slow internet connections
during development it is advised to recycle the container and share the
build/executables path with a windows-vm to test the result in short cycles
instead of make pkg, uninstall, install.

```
docker-compose run --rm --entrypoint=/bin/bash pyinstalle
root@0fa19215321f:/# cd /var/src/bitmask/pkg/windows
root@0fa19215321f:/var/src/bitmask/pkg/windows# ./pyinstaller-build.sh
root@0fa19215321f:/var/src/bitmask/pkg/windows# ./pyinstaller-build.sh
root@0fa19215321f:/var/src/bitmask/pkg/windows# ./pyinstaller-build.sh
....
```

and test the result binary (accessible in bitmask/build in a separate vm.

OpenVPN
=======

OpenVPN is a straight forward cross compile image that builds the openvpn
sourcecode from the git-repository to a windows executable that can be
used by bitmask_root to launch eip.
It needs to be rebuild regulary as openssl gets a new version about every
month. PyInstaller uses the openssl that is compiled by this image

Installer
=========

Installer is a straight forward debian image with makensis installed. The
installer-build script lists the previously built files from pyinstaller and
openvpn to pass it as nsh file to makensis. bitmask.nis controls what will
be displayed to the user and how the components are installed and uninstalled