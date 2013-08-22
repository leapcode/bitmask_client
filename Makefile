# ################################
# Makefile for compiling resources
# files.
# TODO move to setup scripts
# and implement it in python
# http://die-offenbachs.homelinux.org:48888/hg/eric5/file/5072605ad4dd/compileUiFiles.py
###### EDIT ###################### 
#Directory with ui and resource files
RESOURCE_DIR = data/resources
UI_DIR = src/leap/bitmask/gui/ui

#Directory for compiled resources
COMPILED_DIR = src/leap/bitmask/gui

#Directory for (finished) translations
TRANSLAT_DIR = data/translations

#Project file, used for translations
PROJFILE = data/bitmask.pro

#UI files to compile
UI_FILES = loggerwindow.ui mainwindow.ui wizard.ui login.ui statuspanel.ui
#Qt resource files to compile
RESOURCES = locale.qrc loggerwindow.qrc mainwindow.qrc icons.qrc

#pyuic4 and pyrcc4 binaries
PYUIC = pyside-uic
PYRCC = pyside-rcc
PYLUP = pyside-lupdate
LRELE = lrelease


#################################
# DO NOT EDIT FOLLOWING

COMPILED_UI = $(UI_FILES:%.ui=$(COMPILED_DIR)/ui_%.py)
COMPILED_RESOURCES = $(RESOURCES:%.qrc=$(COMPILED_DIR)/%_rc.py)

DEBVER = $(shell dpkg-parsechangelog | sed -ne 's,Version: ,,p')

#

all : resources ui

resources : $(COMPILED_RESOURCES)

ui : $(COMPILED_UI)

translations:
	$(PYLUP) $(PROJFILE)
	$(LRELE) $(TRANSLAT_DIR)/*.ts

$(COMPILED_DIR)/ui_%.py : $(UI_DIR)/%.ui
	$(PYUIC) $< -o $@

$(COMPILED_DIR)/%_rc.py : $(RESOURCE_DIR)/%.qrc
	$(PYRCC) $< -o $@

deb:
	#XXX finish this!
	#should tag upstream/VERSION in upstream branch...
	#@git tag -a upstream/$(DEBVER) -m "..."
	@git-buildpackage --git-ignore-new --git-builder="debuild -us -uc -i'.*|bin|share|lib|local|include|\.git'"  --git-upstream-branch=upstream --git-upstream-tree=branch --git-debian-branch=debian

manpages:
	rst2man docs/man/bitmask.1.rst docs/man/bitmask.1

apidocs:
	@sphinx-apidoc -o docs/api src/leap/bitmask

clean :
	$(RM) $(COMPILED_UI) $(COMPILED_RESOURCES) $(COMPILED_UI:.py=.pyc) $(COMPILED_RESOURCES:.py=.pyc)
