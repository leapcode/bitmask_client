#!/bin/bash

set -e
set -x

mkdir -p ~/openvpn && cd ~/openvpn

BASE=`pwd`
SRC=$BASE/src
WGET="wget --prefer-family=IPv4"
DEST=$BASE/stuff
LDFLAGS="-L$DEST/lib -Wl"
CPPFLAGS="-I$DEST/include"
CFLAGS="-O3"
CXXFLAGS=$CFLAGS
CONFIGURE="./configure --prefix=/stuff"
MAKE="make -j2"
mkdir -p $SRC

######## ####################################################################
# ZLIB # ####################################################################
######## ####################################################################

mkdir $SRC/zlib && cd $SRC/zlib

if [ ! -f zlib-1.2.8.tar.gz ]; then
    $WGET http://zlib.net/zlib-1.2.8.tar.gz
fi
tar zxvf zlib-1.2.8.tar.gz
cd zlib-1.2.8

LDFLAGS=$LDFLAGS \
CPPFLAGS=$CPPFLAGS \
CFLAGS=$CFLAGS \
CXXFLAGS=$CXXFLAGS \
./configure \
--prefix=/stuff

$MAKE
make install DESTDIR=$BASE

########### #################################################################
# OPENSSL # #################################################################
########### #################################################################

#mkdir -p $SRC/openssl && cd $SRC/openssl
#if [ ! -f openssl-1.0.2f.tar.gz ]; then
#    $WGET https://www.openssl.org/source/openssl-1.0.2f.tar.gz
#fi
#tar zxvf openssl-1.0.2f.tar.gz
#cd openssl-1.0.2f

#./Configure darwin64-x86_64-cc \
#-Wl \
#--prefix=/opts zlib \
#--with-zlib-lib=$DEST/lib \
#--with-zlib-include=$DEST/include

#$MAKE
#make install INSTALLTOP=$DEST OPENSSLDIR=$DEST/ssl

############ #################################################################
# POLARSSL # #################################################################
############ #################################################################

mkdir -p $SRC/polarssl && cd $SRC/polarssl
if [ ! -f polarssl-1.3.9-gpl.tgz ]; then
    $WGET https://tls.mbed.org/download/polarssl-1.3.9-gpl.tgz 
fi
tar zxvf polarssl-1.3.9-gpl.tgz
cd polarssl-1.3.9
mkdir build
cd build
cmake ..
$MAKE
make install DESTDIR=$BASE

######## ####################################################################
# LZO2 # ####################################################################
######## ####################################################################

mkdir $SRC/lzo2 && cd $SRC/lzo2
if [ ! -f lzo-2.09.tar.gz ]; then
    $WGET http://www.oberhumer.com/opensource/lzo/download/lzo-2.09.tar.gz
fi
tar zxvf lzo-2.09.tar.gz
cd lzo-2.09

LDFLAGS=$LDFLAGS \
CPPFLAGS=$CPPFLAGS \
CFLAGS=$CFLAGS \
CXXFLAGS=$CXXFLAGS \
$CONFIGURE

$MAKE
make install DESTDIR=$BASE

########### #################################################################
# OPENVPN # #################################################################
########### #################################################################

mkdir $SRC/openvpn && cd $SRC/openvpn
if [ ! -f openvpn-2.3.10.tar.gz ]; then
    $WGET http://swupdate.openvpn.org/community/releases/openvpn-2.3.10.tar.gz
fi
tar zxvf openvpn-2.3.10.tar.gz
cd openvpn-2.3.10

# OPENSSL_SSL_LIBS=$DEST/lib/

POLARSSL_CFLAGS=-I$DEST/usr/local/include \
POLARSSL_LIBS=$DEST/lib/libpolarssl.a \
LDFLAGS=$LDFLAGS \
CPPFLAGS=$CPPFLAGS \
CFLAGS=$CFLAGS \
CXXFLAGS=$CXXFLAGS \
$CONFIGURE \
--disable-plugin-auth-pam \
--enable-password-save \
--with-crypto-library=polarssl

$MAKE LIBS="-all-static -lssl -lcrypto -lz -llzo2"
make install DESTDIR=$BASE/openvpn
