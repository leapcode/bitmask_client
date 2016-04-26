FROM debian:jessie
MAINTAINER paixu@0xn0.de
RUN apt-get update

######
# install packages required to build

RUN apt-get -y install \
    nsis
WORKDIR /var/src/bitmask/pkg/windows

######
# set a specific user
# needs external tuning of the /var/dist rights!
# RUN useradd installer
# USER installer
ENTRYPOINT ["/var/src/bitmask/pkg/windows/installer-build.sh"]