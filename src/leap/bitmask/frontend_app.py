# -*- coding: utf-8 -*-
# frontend_app.py
# Copyright (C) 2013, 2014 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import signal
import sys
import os

from PySide import QtCore, QtGui

from leap.bitmask.config import flags
from leap.bitmask.gui import locale_rc  # noqa - silence pylint
from leap.bitmask.gui.mainwindow import MainWindow

import logging
logger = logging.getLogger(__name__)


def sigint_handler(*args, **kwargs):
    """
    Signal handler for SIGINT
    """
    logger = kwargs.get('logger', None)
    if logger:
        logger.debug("SIGINT catched. shutting down...")
    mainwindow = args[0]
    mainwindow.quit()


def run_frontend(options):
    """
    Run the GUI for the application.

    :param options: a dict of options parsed from the command line.
    :type options: dict
    """
    start_hidden = options["start_hidden"]

    # We force the style if on KDE so that it doesn't load all the kde
    # libs, which causes a compatibility issue in some systems.
    # For more info, see issue #3194
    if flags.STANDALONE and os.environ.get("KDE_SESSION_UID") is not None:
        sys.argv.append("-style")
        sys.argv.append("Cleanlooks")

    qApp = QtGui.QApplication(sys.argv)

    # To test:
    # $ LANG=es ./app.py
    locale = QtCore.QLocale.system().name()
    qtTranslator = QtCore.QTranslator()
    if qtTranslator.load("qt_%s" % locale, ":/translations"):
        qApp.installTranslator(qtTranslator)
    appTranslator = QtCore.QTranslator()
    if appTranslator.load("%s.qm" % locale[:2], ":/translations"):
        qApp.installTranslator(appTranslator)

    # Needed for initializing qsettings it will write
    # .config/leap/leap.conf top level app settings in a platform
    # independent way
    qApp.setOrganizationName("leap")
    qApp.setApplicationName("leap")
    qApp.setOrganizationDomain("leap.se")

    MainWindow(start_hidden=start_hidden)

    # sigint_window = partial(sigint_handler, window, logger=logger)
    # signal.signal(signal.SIGINT, sigint_window)
    # Ensure that the application quits using CTRL-C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    sys.exit(qApp.exec_())


if __name__ == '__main__':
    run_frontend()
