FROM debian:jessie
MAINTAINER paixu@0xn0.de

######
# install packages required to build
# https-transport: winehq deb
# winbind: pip install keyring (requirements.pip) needs this somehow
# git-core: clone rw copy of repo and build specific commit
# imagemagick: convert png to ico-files
RUN apt-get update && apt-get -y install \
    unzip bzip2 \
    curl wget \
    apt-transport-https \
    man2html \
    git-core \
    build-essential autoconf mingw-w64
ENTRYPOINT ["/var/src/bitmask/pkg/windows/openvpn-build.sh"]