# ################################
# Makefile for compiling resources
# files.
# TODO move to setup scripts
# and implement it in python
# http://die-offenbachs.homelinux.org:48888/hg/eric5/file/5072605ad4dd/compileUiFiles.py
###### EDIT ###################### 
#Directory with ui and resource files
RESOURCE_DIR = data/resources
 
#Directory for compiled resources
COMPILED_DIR = src/leap/gui
 
#UI files to compile
# UI_FILES = foo.ui
UI_FILES = 
#Qt resource files to compile
#images.qrc
RESOURCES = mainwindow.qrc 
 
#pyuic4 and pyrcc4 binaries
PYUIC = pyuic4
PYRCC = pyrcc4
 
#################################
# DO NOT EDIT FOLLOWING
 
COMPILED_UI = $(UI_FILES:%.ui=$(COMPILED_DIR)/ui_%.py)
COMPILED_RESOURCES = $(RESOURCES:%.qrc=$(COMPILED_DIR)/%_rc.py)

DEBVER = $(shell dpkg-parsechangelog | sed -ne 's,Version: ,,p')

#
 
all : resources ui 
 
resources : $(COMPILED_RESOURCES) 
 
ui : $(COMPILED_UI)
 
$(COMPILED_DIR)/ui_%.py : $(RESOURCE_DIR)/%.ui
	$(PYUIC) $< -o $@
 
$(COMPILED_DIR)/%_rc.py : $(RESOURCE_DIR)/%.qrc
	$(PYRCC) $< -o $@

deb:
	#XXX finish this!
	#should tag upstream/VERSION in upstream branch...
	#@git tag -a upstream/$(DEBVER) -m "..."
	@git-buildpackage --git-ignore-new --git-builder="debuild -us -uc -i'.*|bin|share|lib|local|include|\.git'"  --git-upstream-branch=upstream --git-upstream-tree=branch --git-debian-branch=debian

manpages:
	rst2man docs/man/leap-client.1.rst docs/man/leap-client.1

apidocs:
	@sphinx-apidoc -o docs/api src/leap

clean : 
	$(RM) $(COMPILED_UI) $(COMPILED_RESOURCES) $(COMPILED_UI:.py=.pyc) $(COMPILED_RESOURCES:.py=.pyc)  
