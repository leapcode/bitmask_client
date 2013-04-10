# -*- coding: utf-8 -*-
# app.py
# Copyright (C) 2013 LEAP
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

import logging
import signal
import sys

from functools import partial
from PySide import QtCore, QtGui

from leap.common.events import server
from leap.util import __version__ as VERSION
from leap.util import leap_argparse
from leap.gui import locale_rc
from leap.gui.mainwindow import MainWindow

import codecs
codecs.register(lambda name: codecs.lookup('utf-8')
                if name == 'cp65001' else None)


def sigint_handler(*args, **kwargs):
    logger = kwargs.get('logger', None)
    logger.debug('SIGINT catched. shutting down...')
    mainwindow = args[0]
    mainwindow.quit()


def main():
    """
    Launches the main event loop
    """

    server.ensure_server(port=8090)

    _, opts = leap_argparse.init_leapc_args()
    debug = opts.debug
    standalone = opts.standalone

    # TODO: get severity from command line args
    if debug:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logger = logging.getLogger(name='leap')
    logger.setLevel(level)
    console = logging.StreamHandler()
    console.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s '
        '- %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logger.info('LEAP client version %s', VERSION)
    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logfile = opts.log_file
    if logfile is not None:
        logger.debug('Setting logfile to %s ', logfile)
        fileh = logging.FileHandler(logfile)
        fileh.setLevel(logging.DEBUG)
        fileh.setFormatter(formatter)
        logger.addHandler(fileh)

    logger.info('Starting app')
    app = QtGui.QApplication(sys.argv)

    # To test:
    # $ LANG=es ./app.py
    locale = QtCore.QLocale.system().name()
    qtTranslator = QtCore.QTranslator()
    if qtTranslator.load("qt_%s" % locale, ":/translations"):
        app.installTranslator(qtTranslator)
    appTranslator = QtCore.QTranslator()
    if appTranslator.load("%s.qm" % locale[:2], ":/translations"):
        app.installTranslator(appTranslator)

    # Needed for initializing qsettings it will write
    # .config/leap/leap.conf top level app settings in a platform
    # independent way
    app.setOrganizationName("leap")
    app.setApplicationName("leap")
    app.setOrganizationDomain("leap.se")

    # TODO: check if the leap-client is already running and quit
    # gracefully in that case.

    window = MainWindow(standalone)
    window.show()

    # This dummy timer ensures that control is given to the outside
    # loop, so we can hook our sigint handler.
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    sigint_window = partial(sigint_handler, window, logger=logger)
    signal.signal(signal.SIGINT, sigint_window)

    if sys.platform == "darwin":
        window.raise_()

    # Run main loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
