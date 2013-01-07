#!/bin/sh
echo "Installing LEAP Client in /Applications"
cp -r "LEAP Client.app" "/Applications"

echo "Copying openvpn binary"
cp -r openvpn.leap /usr/bin 


echo "Installing tun/tap drivers"
cp -r Extensions/* /Library/Extensions
cp -r StartupItems/* /Library/StartupItems

echo "Loading tun/tap kernel extension"
/Library/StartupItems/tun/tun start

echo "Installation Finished!"
