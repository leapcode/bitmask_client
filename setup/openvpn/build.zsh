#!/bin/zsh
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

{ test "$1" = "clean" } && {
	notice "Cleaning up all build in ${TOPSRC}"
	for src in `cat Sources | awk '
/^#/ {next}
/^./ { print $1 }'`; do
		{ test "$src" != "" } && { rm -rf "${src}" }
	done
	act "Done."
	return 0
}

os="`uname -s`"
target="$1"
notice "OpenVPN build on $os for $target in ${TOPSRC}"

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

	{ test "$1" != "" } && {
	    test "$1" != "$name" } && {
	    continue }

	# download the file
	{ test -r ${file} } || {
	    act "downloading ${file}"
	    curl ${REPO}/${file} -o ${file}
	}
	# decompress the file
	{ test -r ${name} } || {
	    act "decompressing ${name}"
	    case $arch in
		## BARE SOURCE
		.tar.gz)  tar xfz ${file}; mv ${name}${ver} ${name} ;;
		.tar.bz2) tar xfj ${file}; mv ${name}${ver} ${name} ;;
		.tgz) tar xfz ${file}; mv ${name}${ver} ${name} ;;
		*) error "compression not supported: $arch"
	    esac
	}
	act "${name} source ready"
    done
}

act "Downloading sources"

# git clone latest openvpn
{ test -r openvpn } || { git clone https://github.com/OpenVPN/openvpn.git }

case "$os" in
    Darwin)
	prepare_sources lzo
	prepare_sources polarssl
	;;
    Linux) # Cross-compile for Win32
	prepare_sources lzo
	prepare_sources opensc
	prepare_sources openssl
	# tap windows
	{ test -r tap-windows } || { git clone https://github.com/OpenVPN/tap-windows.git }
	;;
esac

notice "Sources ready, now compiling..."
LOG="`pwd`/build.log"; touch ${LOG}
act "logs saved in build.log"

case "$target" in
    osx)
	{ test -r polarssl/library/libpolarssl.a } || {
	    act "building PolarSSL..."
	    pushd polarssl
	    CC=clang cmake . >> ${LOG}
	    make -C library clean
	    cat CMakeCache.txt | awk '
/^CMAKE_C_COMPILER/ { print "CMAKE_C_COMPILER:FILEPATH=/usr/bin/clang"; next }
/^CMAKE_BUILD_TYPE/ { print $1 "Release"; next }
/^CMAKE_C_FLAGS:STRING/ { print "CMAKE_C_FLAGS:STRING=-arch x86_64 -arch i386"; next }
{ print $0 }
' > CMakeCache.leap
	    cp CMakeCache.leap CMakeCache.txt
	    make -C library >> ${LOG}
	    popd
	    act "done."
	}

	act "building OpenVPN"
	pushd openvpn
	CC=clang CFLAGS="-arch x86_64 -arch i386" \
	    LZO_LIBS="/opt/local/lib/liblzo2.a" LZO_CFLAGS="-I/opt/local/include" \
	    POLARSSL_CFLAGS="-I${TOPSRC}/polarssl/include" \
	    POLARSSL_LIBS="${TOPSRC}/polarssl/library/libpolarssl.a" \
	    ./configure --with-crypto-library=polarssl >> ${LOG}
	make src/openvpn/openvpn
	popd
	act "done."
	;;

    win32)
	{ test -r lzo/src/liblzo2.la } || { pushd lzo
	    act "building LZO lib"
	    ./configure --host=i586-mingw32msvc >> ${LOG}
	    make >> ${LOG}; popd }
	# openssl
	{ test -r openssl/libssl.a } || {
	    act "building OpenSSL lib"
	    pushd openssl
	    ./Configure --cross-compile-prefix=i586-mingw32msvc- mingw >> ${LOG}
	    make ${LOG}; popd }

	pushd openvpn
	act "building latest OpenVPN"
	{ test -r configure } || {
	    sed -i -e 's/-municode//' src/openvpn/Makefile.am
	    autoreconf -i >> ${LOG}
	}
	CFLAGS="-I/usr/i586-mingw32msvc/include/ddk -D_WIN32_WINNT=0x0501" \
	    LZO_LIBS="${TOPSRC}/lzo/src/liblzo2.la" \
	    LZO_CFLAGS="-I${TOPSRC}/lzo/include" \
	    TAP_CFLAGS="-I${TOPSRC}/tap-windows/src" \
	    OPENSSL_SSL_CFLAGS="-I${TOPSRC}/openssl/include" \
	    OPENSSL_CRYPTO_CFLAGS="-I${TOPSRC}/openssl/crypto" \
	    OPENSSL_SSL_LIBS="${TOPSRC}/openssl/libssl.a" \
	    OPENSSL_CRYPTO_LIBS="${TOPSRC}/openssl/libcrypto.a" \
	    ./configure --host=i586-mingw32msvc >> ${LOG}
	make >> ${LOG}
	popd

	act "If OpenVPN build reports a final error on linkage, it might be due to a libtool bug"
	act "(something like undefined reference to _WinMain@16)"
	act "You need to go inside openvpn/src/openvpn and issue the last compile line manually"
	act "adding an flat '-shared' at the end of it, then do 'cp .libs/openvpn.exe .'"
	act "Happy hacking."
	;;
    *)
	error "Unknown target: $target"
	;;
esac