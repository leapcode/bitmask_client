FROM ubuntu:trusty

MAINTAINER Ivan Alejandro <ivanalejandro0@gmail.com>

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    g++ \
    git \
    libffi-dev \
    libsqlite3-dev \
    libssl-dev \
    libzmq-dev \
    openvpn \
    pyside-tools \
    python-dev \
    python-openssl \
    python-pip \
    python-pyside \
    python-setuptools \
    python-virtualenv \
    make realpath lxpolkit policykit-1 iptables && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


RUN mkdir -p /bitmask
WORKDIR /bitmask

COPY leap_bootstrap.sh /bitmask/

VOLUME ["/data/"]

EXPOSE 1984 2013
ENTRYPOINT ["/bitmask/leap_bootstrap.sh"]
