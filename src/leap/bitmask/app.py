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
#
# M:::::::MMMMMMMMMM~:::::::::::::::::::::::::::::::::::::~MMMMMMMMMM~:::::::M
# M:::::MMM$$$$$77$MMMMN~:::::::::::::::::::::::::::::~NMMMM$77$$$$$MMM::::::M
# M:::~MMZ$$$$$777777I8MMMM~:::::::::::::::::::::::~MMMMDI777777$$$$$$MM:::::M
# M:::MMZ$$$$$777777IIIIIZMMMM:::::::::::::::::::MMNMZIIIII777777$$$$$$MM::::M
# M::DMN$$$$$777777IIIIIII??7DDNM+:::::::::::=MDDD7???IIIIII777777$$$$$DMN:::M
# M::MM$$$$$7777777IIIIIII????+?88OOMMMMMMMOO88???????IIIIIII777777$$$$$MM:::M
# M::MM$$$$$777777IIIIIIII??????++++7ZZ$$ZI+++++??????IIIIIIII777777$$$$MM~::M
# M:~MM$$$$77777Z8OIIIIIIII??????++++++++++++++??????IIIIIIIO8Z77777$$$$NM+::M
# M::MM$$$777MMMMMMMMMMMZ?II???????+++++++++???????III$MMMMMMMMMMM7777$$DM$::M
# M:~MM$$77MMMI~::::::$MMMM$?I????????????????????I$MMMMZ~::::::+MMM77$$MM~::M
# M::MM$7777MM::::::::::::MMMMI?????????????????IMMMM:::::::::::~MM7777$MM:::M
# M::MM777777MM~:::::::::::::MMMD?I?????????IIDMMM,:::::::::::::MM777777MM:::M
# M::DMD7777IIMM$::::::::::::?MMM?I??????????IMMM$::::::::::::7MM7I77778MN:::M
# M:::MM777IIIIMMMN~:::::::MMMM?II???+++++????IIMMMM::::::::MMMMIIII777MM::::M
# M:::ZMM7IIIIIIIOMMMMMMMMMMZ?III???++++++++??III?$MMMMMMMMMMO?IIIIII7MMO::::M
# M::::MMDIIIIIIIIII?IIIII?IIIII???+++===++++??IIIIIIII?II?IIIIIIIIII7MM:::::M
# M:::::MM7IIIIIIIIIIIIIIIIIIIII??+++IZ$$I+++??IIIIIIIIIIIIIIIIIIIII7MM::::::M
# M::::::MMOIIIIIIIIIIIIIIIIIIII?D888MMMMM8O8D?IIIIIIIIIIIIIIIIIIII$MM:::::::M
# M:::::::MMM?IIIIIIIIIIIIIIII7MNMD:::::::::OMNM$IIIIIIIIIIIIIIII?MMM::::::::M
# M::::::::NMMI?IIIIIIIIIII?OMMM:::::::::::::::MMMO?IIIIIIIIIIIIIMMN:::::::::M
# M::::::::::MMMIIIIIIIII?8MMM:::::::::::::::::::MMM8IIIIIIIIIIMMM:::::::::::M
# M:::::::::::~NMMM7???7MMMM:::::::::::::::::::::::NMMMI??I7MMMM:::::::::::::M
# M::::::::::::::7MMMMMMM+:::::::::::::::::::::::::::?MMMMMMMZ:::::::::::::::M
#                (thanks to: http://www.glassgiant.com/ascii/)

import logging
import signal
import sys
import os

from functools import partial

from PySide import QtCore, QtGui

from leap.bitmask import __version__ as VERSION
from leap.bitmask.util import leap_argparse
from leap.bitmask.util import log_silencer
from leap.bitmask.util.leap_log_handler import LeapLogHandler
from leap.bitmask.util.streamtologger import StreamToLogger
from leap.common.events import server as event_server

import codecs
codecs.register(lambda name: codecs.lookup('utf-8')
                if name == 'cp65001' else None)


def sigint_handler(*args, **kwargs):
    """
    Signal handler for SIGINT
    """
    logger = kwargs.get('logger', None)
    if logger:
        logger.debug("SIGINT catched. shutting down...")
    mainwindow = args[0]
    mainwindow.quit()


def install_qtreactor(logger):
    import qt4reactor
    qt4reactor.install()
    logger.debug("Qt4 reactor installed")


def add_logger_handlers(debug=False, logfile=None):
    """
    Create the logger and attach the handlers.

    :param debug: the level of the messages that we should log
    :type debug: bool
    :param logfile: the file name of where we should to save the logs
    :type logfile: str
    :return: the new logger with the attached handlers.
    :rtype: logging.Logger
    """
    # TODO: get severity from command line args
    if debug:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    # Create logger and formatter
    logger = logging.getLogger(name='leap')
    logger.setLevel(level)

    log_format = '%(asctime)s - %(name)s:%(funcName)s:L#%(lineno)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)

    silencer = log_silencer.SelectiveSilencerFilter()
    console.addFilter(silencer)
    logger.addHandler(console)
    logger.debug('Console handler plugged!')

    # LEAP custom handler
    leap_handler = LeapLogHandler()
    leap_handler.setLevel(level)
    leap_handler.addFilter(silencer)
    logger.addHandler(leap_handler)
    logger.debug('Leap handler plugged!')

    # File handler
    if logfile is not None:
        logger.debug('Setting logfile to %s ', logfile)
        fileh = logging.FileHandler(logfile)
        fileh.setLevel(logging.DEBUG)
        fileh.setFormatter(formatter)
        fileh.addFilter(silencer)
        logger.addHandler(fileh)
        logger.debug('File handler plugged!')

    return logger


def replace_stdout_stderr_with_logging(logger):
    """
    Replace:
        - the standard output
        - the standard error
        - the twisted log output
    with a custom one that writes to the logger.
    """
    sys.stdout = StreamToLogger(logger, logging.DEBUG)
    sys.stderr = StreamToLogger(logger, logging.ERROR)

    # Replace twisted's logger to use our custom output.
    from twisted.python import log
    log.startLogging(sys.stdout)


def main():
    """
    Starts the main event loop and launches the main window.
    """
    _, opts = leap_argparse.init_leapc_args()

    if opts.version:
        print "Bitmask version: %s" % (VERSION,)
        sys.exit(0)

    standalone = opts.standalone
    bypass_checks = getattr(opts, 'danger', False)
    debug = opts.debug
    logfile = opts.log_file
    openvpn_verb = opts.openvpn_verb

    try:
        event_server.ensure_server(event_server.SERVER_PORT)
    except Exception as e:
        # We don't even have logger configured in here
        print "Could not ensure server: %r" % (e,)

    #############################################################
    # Given how paths and bundling works, we need to delay the imports
    # of certain parts that depend on this path settings.
    # So first we set all the places where standalone might be queried.
    from leap.bitmask.config import flags
    from leap.common.config.baseconfig import BaseConfig
    flags.STANDALONE = standalone
    BaseConfig.standalone = standalone

    logger = add_logger_handlers(debug, logfile)
    replace_stdout_stderr_with_logging(logger)

    # And then we import all the other stuff
    from leap.bitmask.gui import locale_rc
    from leap.bitmask.gui import twisted_main
    from leap.bitmask.gui.mainwindow import MainWindow
    from leap.bitmask.platform_init import IS_MAC
    from leap.bitmask.platform_init.locks import we_are_the_one_and_only
    from leap.bitmask.util.requirement_checker import check_requirements

    # pylint: avoid unused import
    assert(locale_rc)

    if not we_are_the_one_and_only():
        # Bitmask is already running
        logger.warning("Tried to launch more than one instance "
                       "of Bitmask. Raising the existing "
                       "one instead.")
        sys.exit(1)

    check_requirements()

    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logger.info('Bitmask version %s', VERSION)
    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    logger.info('Starting app')

    # We force the style if on KDE so that it doesn't load all the kde
    # libs, which causes a compatibility issue in some systems.
    # For more info, see issue #3194
    if flags.STANDALONE and os.environ.get("KDE_SESSION_UID") is not None:
        sys.argv.append("-style")
        sys.argv.append("Cleanlooks")

    app = QtGui.QApplication(sys.argv)

    # install the qt4reactor.
    install_qtreactor(logger)

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

    # XXX ---------------------------------------------------------
    # In quarantine, looks like we don't need it anymore.
    # This dummy timer ensures that control is given to the outside
    # loop, so we can hook our sigint handler.
    #timer = QtCore.QTimer()
    #timer.start(500)
    #timer.timeout.connect(lambda: None)
    # XXX ---------------------------------------------------------

    window = MainWindow(
        lambda: twisted_main.quit(app),
        openvpn_verb=openvpn_verb,
        bypass_checks=bypass_checks)

    sigint_window = partial(sigint_handler, window, logger=logger)
    signal.signal(signal.SIGINT, sigint_window)

    if IS_MAC:
        window.raise_()

    # This was a good idea, but for this to work as intended we
    # should centralize the start of all services in there.
    #tx_app = leap_services()
    #assert(tx_app)

    # Run main loop
    twisted_main.start(app)

if __name__ == "__main__":
    main()
