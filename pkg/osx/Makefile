pkg :  dist dmg

dist :
	~/pyinstaller/pyinstaller.py -w -s leap-client.spec
	cp -r /opt/local/Library/Frameworks/QtGui.framework/Versions/4/Resources/qt_menu.nib "dist/LEAP Client.app/Contents/Resources"
	cp Info.plist "dist/LEAP Client.app/Contents/Info.plist"
	cp ../../data/images/leap-client.icns "dist/LEAP Client.app/Contents/Resources/icon-windowed.icns"


dmg :
	#TODO: remove if already present
	#rm dist/LEAPClient.dmg
	hdiutil create -format UDBZ -srcfolder "dist/LEAP Client.app/" "dist/LEAP Client.dmg"

clean :
	rm -rf dist/ build/

