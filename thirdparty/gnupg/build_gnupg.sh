#!/usr/bin/env sh

# ----------------------------------------------------------
# Compile gnupg binary, to distribute with Bitmask bundles.
# ----------------------------------------------------------
# You will need to import the keys for the gnupg developers into your keyring,
# see https://www.gnupg.org/download/integrity_check.html
# and https://www.gnupg.org/signature_key.html

# For osx specific details, see:
# http://macgpg.sourceforge.net/docs/howto-build-gpg-osx.txt.asc
# osx doesn't allow to build static binaries, see:
# http://stackoverflow.com/questions/5259249/creating-static-mac-os-x-c-build

set -e
set -x

gnupg_version="gnupg-1.4.20"
url="ftp://ftp.gnupg.org/gcrypt/gnupg/$gnupg_version.tar.bz2"

platform='unknown'
unamestr=`uname`
if [[ "$unamestr" == 'Linux' ]]; then
   platform='linux'
elif [[ "$unamestr" == 'Darwin' ]]; then
   platform='osx'
fi

function prepare_source()
{
    wget -c $url -O $gnupg_version.tar.bz2;
    wget -c $url.sig -O $gnupg_version.tar.bz2.sig;
    #gpg --verify $gnupg_version.tar.bz2.sig $gnupg_version.tar.bz2;
    tar -xjf $gnupg_version.tar.bz2;
    cd $gnupg_version;
}


function build_static_gpg()
{
    ./configure CFLAGS="-static";
    make;
}

function build_gpg()
{
    ./configure;
    make;
}

function copy_to_builddir()
{
    mkdir -p ~/leap_thirdparty_build
    cp g10/gpg ~/leap_thirdparty_build
}

function main()
{
    if [[ $platform == 'linux' ]]; then
        (prepare_source; build_static_gpg; copy_to_builddir)
    elif [[ $platform == 'osx' ]]; then
        (prepare_source; build_gpg; copy_to_builddir)
    fi

}

main "$@"

