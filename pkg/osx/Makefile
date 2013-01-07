#WARNING: You need to run this with an activated VIRTUALENV.

OSX = dist/LEAP\ Client.app/Contents/MacOS/

pkg :  dist trim installer dmg

dist :
	~/pyinstaller/pyinstaller.py -w -s leap-client.spec
	cp -r /opt/local/Library/Frameworks/QtGui.framework/Versions/4/Resources/qt_menu.nib "dist/LEAP Client.app/Contents/Resources"
	cp Info.plist "dist/LEAP Client.app/Contents/Info.plist"
	cp ../../data/images/leap-client.icns "dist/LEAP Client.app/Contents/Resources/icon-windowed.icns"

trim:
	#XXX this should go properly in pyinstaller spec excludes, but going quick'n'dirty
	rm $(OSX)QtSvg $(OSX)QtXml $(OSX)QtNetwork $(OSX)QtOpenGL $(OSX)Qt3Support $(OSX)QtSql

installer:
	#XXX need to fix some paths there (binary, etc)
	platypus -P install/leap-installer.platypus -y dist/LEAPClient_installer.app
	#XXX should build tuntap extensions ourselves
	mkdir "dist/LEAPClient_installer.app/Contents/Resources/StartupItems"
	mkdir "dist/LEAPClient_installer.app/Contents/Resources/Extensions/"
	cp -r /opt/local/Library/StartupItems/tun "dist/LEAPClient_installer.app/Contents/Resources/StartupItems/"
	cp -r /opt/local/Library/StartupItems/tap "dist/LEAPClient_installer.app/Contents/Resources/StartupItems/"
	cp -r /opt/local/Library/Extensions/tun.kext "dist/LEAPClient_installer.app/Contents/Resources/Extensions/"
	cp -r /opt/local/Library/Extensions/tap.kext "dist/LEAPClient_installer.app/Contents/Resources/Extensions/"
	#copy the binary that we have previously built
	#XXX not building it yet...
	cp ../../openvpn/build/openvpn.leap "dist/LEAPClient_installer.app/Contents/Resources/"
	#copy startup scripts
	cp install/client.up.sh "dist/LEAP Client.app/Contents/Resources"
	cp install/client.down.sh "dist/LEAP Client.app/Contents/Resources"
	cp install/ProcessNetworkChanges.plist.template "dist/LEAP Client.app/Contents/Resources"
	#Finally, copy application bundle...
	cp -r "dist/LEAP Client.app" "dist/LEAPClient_installer.app/Contents/Resources/"

dmg :
	#TODO: remove if already present
	#rm dist/LEAPClient.dmg
	hdiutil create -format UDBZ -srcfolder "dist/LEAPClient_installer.app/" "dist/LEAP Client Installer.dmg"

clean :
	rm -rf dist/ build/
