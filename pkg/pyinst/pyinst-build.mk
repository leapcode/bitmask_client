freeze-ver:
	cp pkg/version-template src/leap/bitmask/_version.py
	sed  -i 's/^version_version\(.*\)/version_version = "$(NEXT_VERSION)"/'  src/leap/bitmask/_version.py
	sed  -i 's/^full_revisionid\(.*\)/full_revisionid = "$(GIT_COMMIT)"/' src/leap/bitmask/_version.py

hash-binaries:
	# TODO get from a build dir
	OPENVPN_BIN=/usr/sbin/openvpn BITMASK_ROOT=pkg/linux/bitmask-root python setup.py hash_binaries

pyinst: freeze-ver hash-binaries
	pyinstaller -y pkg/pyinst/bitmask.spec

reset-ver:
	git checkout -- src/leap/bitmask/_version.py

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

pyinst-cleanup:
	rm -rf $(DIST)config
	mkdir -p $(DIST_VERSION)
	mv $(DIST) $(DIST_VERSION)lib
	cd pkg/launcher && make 
	mv pkg/launcher/bitmask $(DIST_VERSION)

pyinst-distribution-data:
	cp release-notes.rst $(DIST_VERSION)
	cp pkg/PixelatedWebmail.README $(DIST_VERSION)
	cp LICENSE $(DIST_VERSION)

pyinst-linux-helpers:
	mkdir -p $(DIST_VERSION)apps/eip/files
	# TODO compile static
	cp /usr/sbin/openvpn $(DIST_VERSION)apps/eip/files/leap-openvpn
	cp pkg/linux/bitmask-root $(DIST_VERSION)apps/eip/files/
	cp pkg/linux/leap-install-helper.sh $(DIST_VERSION)apps/eip/files/
	cp pkg/linux/polkit/se.leap.bitmask.bundle.policy $(DIST_VERSION)apps/eip/files/
	mkdir -p $(DIST_VERSION)apps/mail
	# TODO compile static
	cp /usr/bin/gpg $(DIST_VERSION)apps/mail

pyinst-tar:
	cd dist/ && tar cvzf Bitmask.$(NEXT_VERSION).tar.gz bitmask-$(NEXT_VERSION)

pyinst-sign:
	gpg2 -a --sign --detach-sign dist/Bitmask.$(NEXT_VERSION).tar.gz 

pyinst-upload:
	scp dist/Bitmask.$(NEXT_VERSION).* salmon.leap.se:./ 

pyinst-linux: pyinst reset-ver pyinst-hacks pyinst-trim pyinst-cleanup pyinst-distribution-data pyinst-linux-helpers pyinst-tar

clean_pkg:
	rm -rf build dist
