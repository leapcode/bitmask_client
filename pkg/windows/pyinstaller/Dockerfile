FROM debian:jessie
MAINTAINER paixu@0xn0.de

ENV PYTHON_VERSION=2.7.11
ENV OPENSSL_VERSION=1.0.2f
ENV ZLIB_VERSION=1.2.8
ENV MINGW_VERSION=0.6.2-beta-20131004-1
ENV MINGW_BIN_VERSION=0.6.2-mingw32-beta-20131004-1-bin
ENV WINEDEBUG=fixme-all

######
# install packages required to build
# https-transport: winehq deb
# winbind: pip install keyring (requirements.pip) needs this somehow
# git-core: clone rw copy of repo and build specific commit
# imagemagick: convert png to ico-files
RUN apt-get update && apt-get -y install \
    unzip curl apt-transport-https \
    winbind \
    build-essential autoconf bison gperf flex libtool mingw-w64 \
    git-core \
    imagemagick \
    pkg-config

# install wine > 1.6.2 (debian:jessie version fails with pip)
RUN dpkg --add-architecture i386 \
 && curl https://dl.winehq.org/wine-builds/Release.key | apt-key add - \
 && echo 'deb https://dl.winehq.org/wine-builds/debian/ jessie main' >> /etc/apt/sources.list.d/wine.list \
 && apt-get update

RUN curl https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}.msi > /tmp/python-${PYTHON_VERSION}.msi
RUN curl -L http://sourceforge.net/projects/mingw/files/Installer/mingw-get/mingw-get-${MINGW_VERSION}/mingw-get-${MINGW_BIN_VERSION}.zip/download > /tmp/mingw-get.zip

# alternative with messy python afterwards
# RUN curl -L http://download.microsoft.com/download/7/9/6/796EF2E4-801B-4FC4-AB28-B59FBF6D907B/VCForPython27.msi > /tmp/msvcforpython27.msi

RUN curl -L http://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz > /tmp/openssl-${OPENSSL_VERSION}.tar.gz
RUN apt-get install -y winehq-staging

RUN curl -L http://sourceforge.net/projects/mingw/files/Installer/mingw-get/mingw-get-${MINGW_VERSION}/mingw-get-${MINGW_BIN_VERSION}.zip/download > /tmp/mingw-get.zip
RUN mkdir -p  /root/.wine/drive_c/mingw \
 && unzip -d /root/.wine/drive_c/mingw /tmp/mingw-get.zip

#######
# Build python dependency
# using the 'host' (linux) xcompiler instead of fiddeling in wine
# zlib - needs a update every 5 years
# adds a patch that makes a shared lib - default is static
RUN curl -L http://zlib.net/zlib-${ZLIB_VERSION}.tar.gz > /tmp/zlib-${ZLIB_VERSION}.tar.gz
ADD zlib-mingw-shared.patch /zlib-mingw-shared.patch
RUN mkdir -p /root/.wine/drive_c/zlib/src \
 && mv /tmp/zlib-${ZLIB_VERSION}.tar.gz /root/.wine/drive_c/zlib/src \
 && cd /root/.wine/drive_c/zlib/src \
 && tar xzf zlib-${ZLIB_VERSION}.tar.gz \
 && cd zlib-${ZLIB_VERSION} \
 && patch -p0 < /zlib-mingw-shared.patch \
 && make -f win32/Makefile.gcc PREFIX=/usr/bin/i686-w64-mingw32- \
 && make -f win32/Makefile.gcc INCLUDE_PATH=/root/.wine/drive_c/zlib/include LIBRARY_PATH=/root/.wine/drive_c/zlib/lib BINARY_PATH=/root/.wine/drive_c/zlib/bin  install

######
# install gcc for most pip builds
# install g++ for pycryptopp
# this is mingw in wine, not to get confused with mingw-w64 in container-host
RUN wine msiexec -i /tmp/python-${PYTHON_VERSION}.msi -q \
 && wine c:/mingw/bin/mingw-get.exe install gcc g++ mingw32-make \
 && rm -r /tmp/.wine-0

####
# pip configuration
# set wine mingw compiler to be used by "python setup build"
# set default include dirs, libraries and library paths
# the libraries=crypto is added because srp will only link using -lssl but links to BN_* (libcrypto) code
# 'install' zlib to mingw so python may find its dlls
# pyside-rcc fix (https://srinikom.github.io/pyside-bz-archive/670.html)
RUN printf "[build]\ncompiler=mingw32\n\n[build_ext]\ninclude_dirs=c:\\openssl\\include;c:\\zlib\\include\nlibraries=crypto\nlibrary_dirs=c:\\openssl\\lib;c:\\openssl\\bin;c:\\zlib\\lib;c:\\zlib\\bin" > /root/.wine/drive_c/Python27/Lib/distutils/distutils.cfg \
 && printf 'REGEDIT4\n\n[HKEY_CURRENT_USER\\Environment]\n"PATH"="C:\\\\python27;C:\\\\python27\\\\Scripts;C:\\\\python27\\\\Lib\\\\site-packages\\\\PySide;C:\\\\mingw\\\\bin;c:\\\\windows;c:\\\\windows\\\\system"' > /root/.wine/drive_c/path.reg \
 && printf 'REGEDIT4\n\n[HKEY_CURRENT_USER\\Environment]\n"OPENSSL_CONF"="C:\\\\openssl"' > /root/.wine/drive_c/openssl_conf.reg \
 && printf 'REGEDIT4\n\n[HKEY_CURRENT_USER\\Environment]\n"PYTHONPATH"="C:\\\\python27\\\\lib\\\\site-packages;Z:\\\\var\\\\build\\\\bitmask_rw\\\\src"' > /root/.wine/drive_c/pythonpath.reg \
 && cp /root/.wine/drive_c/zlib/bin/zlib1.dll /root/.wine/drive_c/mingw/bin \
 && cp /root/.wine/drive_c/zlib/lib/libz.dll.a /root/.wine/drive_c/mingw/lib

####
# prepare the environment with all python dependencies installed
# inject dirspec from distribution
#
RUN apt-get install -y python-dirspec \
 && cp -r /usr/lib/python2.7/dist-packages/dirspec* /root/.wine/drive_c/Python27/Lib/site-packages/
RUN apt-get install -y python-setuptools
RUN wine regedit /root/.wine/drive_c/path.reg \
 && wine regedit /root/.wine/drive_c/openssl_conf.reg \
 && wine regedit /root/.wine/drive_c/pythonpath.reg \
 && wine pip install virtualenv pyinstaller \
 && wine pip install wheel \
 && wine pip install -U setuptools-scm \
 && wine pip install -U setuptools_scm \
 && wine pip install -U pyside python-qt \
 && wine pip install -I psutil==3.4.2 \
 && rm -r /tmp/.wine-0

# alternative msvc: after python is installed (or before?)
# && wine msiexec -i /tmp/msvcforpython27.msi -q \

RUN apt-get -y install \
    mc
ENTRYPOINT ["/var/src/bitmask/pkg/windows/pyinstaller-build.sh"]