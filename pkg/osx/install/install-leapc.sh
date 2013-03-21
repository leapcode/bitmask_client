#!/bin/bash

# LEAP CLient Installer Script.
#
# Copyright (C) 2013 LEAP Encryption Access Project
#
# This file is part of LEAP Client, as
# available from http://leap.se/. This file is free software;
# you can redistribute it and/or modify it under the terms of the GNU
# General Public License (GPL) as published by the Free Software
# Foundation, in version 2 as it comes in the "COPYING" file of the
# LEAP Client distribution. LEAP Client is distributed in the
# hope that it will be useful, but WITHOUT ANY WARRANTY of any kind.
#

set -e

destlibs=/opt/local/lib
leapdir=/Applications/LEAP\ Client.app
leaplibs=${leapdir}/Contents/MacOS
tunstartup=/Library/StartupItems/tun/tun

echo "Installing LEAP Client in /Applications..."
cp -r "LEAP Client.app" /Applications

echo "Copying openvpn binary..."
cp -r openvpn.leap /usr/bin 

echo "Installing tun/tap drivers..."
test -f $tunstartup && $tunstartup stop

test -d /Library/Extensions || mkdir -p /Library/Extensions
test -d /Library/StartupItems || mkdir -p /Library/StartupItems

cp -r Extensions/* /Library/Extensions
cp -r StartupItems/* /Library/StartupItems

echo "Loading tun/tap kernel extension..."

$tunstartup start

echo "Installation Finished!"
