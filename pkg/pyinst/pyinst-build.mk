pyinst:
	echo "MAKE SURE OF FREEZING VERSION FIRST!"
	pyinstaller -y pkg/pyinst/bitmask.spec

pyinst-hacks:
	cp ../leap_common/src/leap/common/cacert.pem $(DIST)
	mkdir -p $(DIST)pysqlcipher
	cp $(VIRTUAL_ENV)/lib/python2.7/site-packages/pysqlcipher/_sqlite.so $(DIST)pysqlcipher 
	cp -r $(VIRTUAL_ENV)/lib/python2.7/site-packages/pixelated_www $(DIST)

pyinst-trim:
	rm -f $(DIST)libQtOpenGL.so.4
	rm -f $(DIST)libQtSql.so.4
	rm -f $(DIST)libQt3Support.so.4
	rm -f $(DIST)libaudio.so.2
	rm -f $(DIST)libnvidia-*
	#rm -f dist/bitmask/libgstvideo-1.0.so.0
	#rm -f dist/bitmask/libgstaudio0.0.so.0
	#rm -f dist/bitmask/libgstreamer-1.0.so.0

pyinst-wrapper:
	mv $(DIST)libQtCore.so.4 $(DIST)libQtCore.so.4.orig
	mv $(DIST)libQtGui.so.4 $(DIST)libQtGui.so.4.orig
	mv $(DIST)libQtNetwork.so.4 $(DIST)libQtNetwork.so.4.orig
	mv $(DIST)libQtSvg.so.4 $(DIST)libQtSvg.so.4.orig
	mv $(DIST)libQtWebKit.so.4 $(DIST)libQtWebKit.so.4.orig
	mv $(DIST)libQtXmlPatterns.so.4 $(DIST)libQtXmlPatterns.so.4.orig
	mv $(DIST)libQtXml.so.4 $(DIST)libQtXml.so.4.orig
	mv $(DIST)bitmask $(DIST)bitmask-app
	cp pkg/linux/bitmask-launcher $(DIST)bitmask
	cp pkg/PixelatedWebmail.README $(DIST)


pyinst-dist:
	rm -rf $(DIST)config
	cd dist/ && tar cvzf Bitmask.0.9.2.alpha2.tar.gz bitmask

clean_pkg:
	rm -rf build dist
