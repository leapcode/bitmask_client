#WARNING: You need to run this with an activated VIRTUALENV.

OSX = dist/LEAP\ Client.app/Contents/MacOS/
GITC = `git rev-parse --short HEAD`
DMG = "dist/leap-client-$(GITC).dmg"
INST = "dist/LEAP Client installer.app"
INSTR = "dist/LEAP Client installer.app/Contents/Resources"

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
	platypus -P install/leap-installer.platypus -y $(INST)
	#XXX should build tuntap extensions ourselves
	mkdir $(INSTR)/StartupItems
	mkdir $(INSTR)/Extensions
	cp -r /opt/local/Library/StartupItems/tun $(INSTR)/StartupItems
	cp -r /opt/local/Library/StartupItems/tap $(INSTR)/StartupItems
	cp -r /opt/local/Library/Extensions/tun.kext $(INSTR)/Extensions
	cp -r /opt/local/Library/Extensions/tap.kext $(INSTR)/Extensions
	#copy the binary that we have previously built
	#XXX not building it yet...
	cp ../../openvpn/build/openvpn.leap $(INSTR)
	#copy startup scripts
	cp install/client.up.sh $(INSTR) 
	cp install/client.down.sh $(INSTR)
	cp install/ProcessNetworkChanges.plist.template $(INSTR) 
	#Finally, copy application bundle...
	cp -r "dist/LEAP Client.app" $(INSTR) 

dmg :
	rm -f $(DMG)
	hdiutil create -format UDBZ -srcfolder $(INST) $(DMG)

clean :
	rm -rf dist/ build/
