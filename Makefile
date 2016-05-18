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

# UI files to compile
UI_FILES = \
  loggerwindow.ui \
  wizard.ui \
  mainwindow.ui login.ui eip_status.ui mail_status.ui \
  preferences.ui \
    preferences_account_page.ui \
    preferences_vpn_page.ui \
    preferences_email_page.ui \
    password_change.ui \
    advanced_key_management.ui

# Qt resource files to compile
RESOURCES = icons.qrc flags.qrc locale.qrc loggerwindow.qrc

#pyuic4 and pyrcc4 binaries
PYUIC = pyside-uic
PYRCC = pyside-rcc
PYLUP = pyside-lupdate
LRELE = lrelease

# pyinst dist dir

DIST = dist/bitmask/
DIST_OSX = dist/Bitmask.app/
DIST_OSX_RES = dist/Bitmask.app/Contents/Resources/
NEXT_VERSION = $(shell cat pkg/next-version)
DIST_VERSION = dist/bitmask-$(NEXT_VERSION)/
GIT_COMMIT = $(shell git rev-parse HEAD)
LEAP_BUILD_DIR = leap_thirdparty_build/


#################################
# DO NOT EDIT FOLLOWING

LEAP_REPOS = leap_pycommon keymanager leap_mail soledad

COMPILED_UI = $(UI_FILES:%.ui=$(COMPILED_DIR)/ui_%.py)
COMPILED_RESOURCES = $(RESOURCES:%.qrc=$(COMPILED_DIR)/%_rc.py)

DEBVER = $(shell dpkg-parsechangelog | sed -ne 's,Version: ,,p')

ifndef EDITOR
	export EDITOR=vim
endif

ifndef RESOURCE_TIME
	export RESOURCE_TIME=10
endif

CURDIR = $(shell pwd)

###########################################

all : resources ui

resources : $(COMPILED_RESOURCES)

ui : $(COMPILED_UI)

translations:
	data/make_project_file.py
	$(PYLUP) $(PROJFILE)
	$(LRELE) $(TRANSLAT_DIR)/*.ts

$(COMPILED_DIR)/ui_%.py : $(UI_DIR)/%.ui
	$(PYUIC) $< -o $@

$(COMPILED_DIR)/%_rc.py : $(RESOURCE_DIR)/%.qrc
	$(PYRCC) $< -o $@


manpages:
	rst2man docs/man/bitmask.1.rst docs/man/bitmask.1

apidocs:
	@sphinx-apidoc -o docs/api src/leap/bitmask

include pkg/deps.mk
include pkg/tools/profile.mk
include pkg/sumo-tarballs.mk
include pkg/pyinst/pyinst-build.mk
include pkg/branding/branding.mk

clean :
	$(RM) $(COMPILED_UI) $(COMPILED_RESOURCES) $(COMPILED_UI:.py=.pyc) $(COMPILED_RESOURCES:.py=.pyc)
