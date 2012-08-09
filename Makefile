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
	@git tag -a debian/$(DEBVER) -m "..."
	@debuild -us -uc -i.git

clean : 
	$(RM) $(COMPILED_UI) $(COMPILED_RESOURCES) $(COMPILED_UI:.py=.pyc) $(COMPILED_RESOURCES:.py=.pyc)  
