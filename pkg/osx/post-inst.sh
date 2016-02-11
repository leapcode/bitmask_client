#!/bin/sh

# Bitmask Post-Instalation script

cp se.leap.bitmask-helper.plist /Library/LaunchDaemons/
launchctl load /Library/LaunchDaemons/se.leap.bitmask-helper.plist
cp tuntap_20150118.pkg /tmp/ 
open /tmp/tuntap_20150118.pkg
