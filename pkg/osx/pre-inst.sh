#!/bin/sh
# Bitmask Post-Instalation script
[[ -f /Library/LaunchDaemons/se.leap.bitmask-helper.plist ]] && launchctl unload /Library/LaunchDaemons/se.leap.bitmask-helper.plist
