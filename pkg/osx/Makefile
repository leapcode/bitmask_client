OSX = dist/LEAP\ Client.app/Contents/MacOS/
GITC = `git rev-parse --short HEAD`
DMG = "dist/leap-client-$(GITC).dmg"
INST = "dist/LEAP Client installer.app"
INSTR = "dist/LEAP Client installer.app/Contents/Resources"

pkg :  check-env dist tuntap installer dmg

dist :
	~/pyinstaller/pyinstaller.py -w -s leap-client.spec
	cp -r /opt/local/Library/Frameworks/QtGui.framework/Versions/4/Resources/qt_menu.nib "dist/LEAP Client.app/Contents/Resources"
	cp Info.plist "dist/LEAP Client.app/Contents/Info.plist"
	cp ../../data/images/leap-client.icns "dist/LEAP Client.app/Contents/Resources/icon-windowed.icns"

trim:
	#XXX this should go properly in pyinstaller spec excludes, but going quick'n'dirty
	#XXX adapt to PySide
	rm $(OSX)QtSvg $(OSX)QtXml $(OSX)QtNetwork $(OSX)QtOpenGL $(OSX)Qt3Support $(OSX)QtSql

tuntap:
	./build_tuntaposx clean && ./build_tuntaposx

installer:
	#XXX need to fix some paths there (binary, etc)
	platypus -P install/leap-installer.platypus -y $(INST)
	# build tuntaposx kernel extension
	mkdir $(INSTR)/StartupItems
	mkdir $(INSTR)/Extensions
	cp -r dist/tun.kext $(INSTR)/Extensions
	cp -r dist/tuntaposx/StartupItems/* $(INSTR)/StartupItems
	cp install/tun.kext/Info.plist $(INSTR)/Extensions/tun.kext/Contents/
	#copy the binary that we have previously built (not yet)
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

check-env:
ifndef VIRTUAL_ENV
    $(error WHAT DO YOU THINK VIRTUALENV IS FOR??!! Please go get into one..)
endif

clean :
	rm -rf dist/ build/
