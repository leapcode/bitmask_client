#!/usr/bin/env zsh
#
# Copyright (C) 2012 Denis Roio <jaromil@dyne.org>
#
# This source  code is free  software; you can redistribute  it and/or
# modify it under the terms of  the GNU Public License as published by
# the Free  Software Foundation; either  version 3 of the  License, or
# (at your option) any later version.
#
# This source code is distributed in  the hope that it will be useful,
# but  WITHOUT ANY  WARRANTY;  without even  the  implied warranty  of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# Please refer to the GNU Public License for more details.
#
# You should have received a copy of the GNU Public License along with
# this source code; if not, write to:
# Free Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.


REPO="http://files.dyne.org/leap/openvpn/sources"
TOPSRC=`pwd`
QUIET=0
DEBUG=0


autoload colors; colors
# standard output message routines
# it's always useful to wrap them, in case we change behaviour later
notice() { if [[ $QUIET == 0 ]]; then print "$fg_bold[green][*]$fg_no_bold[default] $1" >&2; fi }
error()  { if [[ $QUIET == 0 ]]; then print "$fg[red][!]$fg[default] $1" >&2; fi }
func()   { if [[ $DEBUG == 1 ]]; then print "$fg[blue][D]$fg[default] $1" >&2; fi }
act()    {
    if [[ $QUIET == 0 ]]; then
        if [ "$1" = "-n" ]; then
            print -n "$fg_bold[white] . $fg_no_bold[default] $2" >&2;
        else
            print "$fg_bold[white] . $fg_no_bold[default] $1" >&2;
        fi
    fi
}

notice "OpenVPN build in ${TOPSRC}"

prepare_sources() {
    notice "Preparing sources"
    # look for a file names "Sources", download and decompress entries
    # format of file: name version compression (complete filename when merged)
    { test -r Sources } || {
        error "Sources not found, nothing to build here"
        return 1
    }
    for src in `cat Sources | awk '
/^#/ {next}
/^./ { print $1 ";" $2 ";" $3 }'`; do
        name="${src[(ws:;:)1]}"
        ver="${src[(ws:;:)2]}"
        arch="${src[(ws:;:)3]}"
        file="${name}${ver}${arch}"
        func "preparing source for ${name}${ver}"
        # download the file
        { test -r ${file} } || {
            act "downloading ${file}"
            wget ${REPO}/${file}
        }
        # decompress the file
        { test -r ${name} } || {
            act "decompressing ${name}"
            case $arch in
                ## BARE SOURCE
                .tar.gz)  tar xfz ${file}; mv ${name}${ver} ${name} ;;
                .tar.bz2) tar xfj ${file}; mv ${name}${ver} ${name} ;;
                *) error "compression not supported: $arch"
            esac
        }
        act "${name} source ready"
    done
}

prepare_sources

# tap windows
{ test -r tap-windows } || { git clone https://github.com/OpenVPN/tap-windows.git }

{ test -r lzo/src/liblzo2.la } || { pushd lzo
	./configure --host=i586-mingw32msvc
	make; popd }
# openssl
{ test -r openssl/libssl.a } || {
    pushd openssl
    ./Configure --cross-compile-prefix=i586-mingw32msvc- mingw
    make; popd }

# openvpn
{ test -r openvpn } || { git clone https://github.com/OpenVPN/openvpn.git } 
pushd openvpn
{ test -r configure } || { autoreconf -i }
CFLAGS="-I/usr/i586-mingw32msvc/include/ddk -D_WIN32_WINNT=0x0501" \
LZO_LIBS="${TOPSRC}/lzo/src/liblzo2.la" \
LZO_CFLAGS="-I${TOPSRC}/lzo/include" \
TAP_CFLAGS="-I${TOPSRC}/tap-windows/src" \
OPENSSL_SSL_CFLAGS="-I${TOPSRC}/openssl/include" \
OPENSSL_CRYPTO_CFLAGS="-I${TOPSRC}/openssl/crypto" \
OPENSSL_SSL_LIBS="${TOPSRC}/openssl/libssl.a" \
OPENSSL_CRYPTO_LIBS="${TOPSRC}/openssl/libcrypto.a" \
./configure --host=i586-mingw32msvc
make
popd

