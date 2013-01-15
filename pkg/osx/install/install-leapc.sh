#!/bin/sh
echo "Installing LEAP Client in /Applications"
cp -r "LEAP Client.app" "/Applications"

echo "Copying openvpn binary"
cp -r openvpn.leap /usr/bin 

echo "Installing gnutls"
mkdir -p /opt/local/lib
mv -f "/Applications/LEAP Client.app/Contents/MacOS/libgnutls.26.dylib" /opt/local/lib
mv -f "/Applications/LEAP Client.app/Contents/MacOS/libgnutls-extra.26.dylib" /opt/local/lib
ln -sf /opt/local/lib/libgnutls.26.dylib /opt/local/lib/libgnutls.dylib
ln -sf /opt/local/lib/libgnutls-extra.26.dylib /opt/local/lib/libgnutls-extra.dylib


echo "Installing tun/tap drivers"
cp -r Extensions/* /Library/Extensions
cp -r StartupItems/* /Library/StartupItems

echo "Loading tun/tap kernel extension"
/Library/StartupItems/tun/tun start

echo "Installation Finished!"

ln -s /Applications/LEAP\ Client.app/ /Volumes/LEAP\ Client\ installer/
