pyinst:
	echo "*********************************************"
	echo "MAKE SURE OF MANUALLY FREEZING VERSION FIRST!"
	echo "*********************************************"
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
	# TODO this *is* an ugly hack, See #7352
	mv $(DIST)libQtCore.so.4 $(DIST)libQtCore.so.4.orig
	mv $(DIST)libQtGui.so.4 $(DIST)libQtGui.so.4.orig
	mv $(DIST)libQtNetwork.so.4 $(DIST)libQtNetwork.so.4.orig
	mv $(DIST)libQtSvg.so.4 $(DIST)libQtSvg.so.4.orig
	mv $(DIST)libQtWebKit.so.4 $(DIST)libQtWebKit.so.4.orig
	mv $(DIST)libQtXmlPatterns.so.4 $(DIST)libQtXmlPatterns.so.4.orig
	mv $(DIST)libQtXml.so.4 $(DIST)libQtXml.so.4.orig
	mv $(DIST)bitmask $(DIST)bitmask-app
	cp pkg/linux/bitmask-launcher $(DIST)bitmask

pyinst-cleanup:
	rm -rf $(DIST)config
	mkdir -p $(DIST_VERSION)
	mv $(DIST) $(DIST_VERSION)libs
	cd pkg/launcher && make 
	mv pkg/launcher/bitmask $(DIST_VERSION)

pyinst-distribution-data:
	cp release-notes.rst $(DIST_VERSION)
	cp pkg/PixelatedWebmail.README $(DIST_VERSION)
	cp LICENSE $(DIST_VERSION)

pyinst-tar:
	cd dist/ && tar cvzf Bitmask.$(NEXT_VERSION).tar.gz bitmask-$(NEXT_VERSION)

pyinst-sign:
	# TODO ---- get LEAP_MAINTAINER from environment

pyinst-linux: pyinst pyinst-hacks pyinst-trim pyinst-wrapper pyinst-cleanup pyinst-distribution-data pyinst-tar

clean_pkg:
	rm -rf build dist
