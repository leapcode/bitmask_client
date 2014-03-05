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
UI_FILES = loggerwindow.ui mainwindow.ui wizard.ui login.ui preferences.ui eip_status.ui mail_status.ui eippreferences.ui advanced_key_management.ui
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

ifndef EDITOR
	export EDITOR=vim
endif

ifndef RESOURCE_TIME
	export RESOURCE_TIME=10
endif

#

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

mailprofile:
	gprof2dot -f pstats /tmp/leap_mail_profile.pstats -n 0.2 -e 0.2 | dot -Tpdf -o /tmp/leap_mail_profile.pdf

do_lineprof:
	LEAP_PROFILE_IMAPCMD=1 LEAP_MAIL_MANHOLE=1 kernprof.py -l src/leap/bitmask/app.py --offline --debug

view_lineprof:
	@python -m line_profiler app.py.lprof | $(EDITOR) -

resource_graph:
	./pkg/scripts/monitor_resource.zsh `pgrep bitmask` $(RESOURCE_TIME)
	display bitmask-resources.png

clean :
	$(RM) $(COMPILED_UI) $(COMPILED_RESOURCES) $(COMPILED_UI:.py=.pyc) $(COMPILED_RESOURCES:.py=.pyc)
