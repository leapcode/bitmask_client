# -*- coding: utf-8 -*-
# app.py
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
import signal
import sys
import os

from functools import partial

from PySide import QtCore, QtGui

from leap.bitmask import __version__ as VERSION
from leap.bitmask.config import flags
from leap.bitmask.gui import locale_rc  # noqa - silence pylint
from leap.bitmask.gui.mainwindow import MainWindow
from leap.bitmask.logs.utils import create_logger
from leap.bitmask.platform_init.locks import we_are_the_one_and_only
from leap.bitmask.services.mail import plumber
from leap.bitmask.util import leap_argparse
from leap.bitmask.util.requirement_checker import check_requirements

from leap.common.events import server as event_server
from leap.mail import __version__ as MAIL_VERSION

from twisted.internet import reactor
from twisted.internet.task import LoopingCall

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


def sigterm_handler(*args, **kwargs):
    """
    Signal handler for SIGTERM.
    This handler is actually passed to twisted reactor
    """
    logger = kwargs.get('logger', None)
    if logger:
        logger.debug("SIGTERM catched. shutting down...")
    mainwindow = args[0]
    mainwindow.quit()


def do_display_version(opts):
    """
    Display version and exit.
    """
    # TODO move to a different module: commands?
    if opts.version:
        print "Bitmask version: %s" % (VERSION,)
        print "leap.mail version: %s" % (MAIL_VERSION,)
        sys.exit(0)


def do_mail_plumbing(opts):
    """
    Analize options and do mailbox plumbing if requested.
    """
    # TODO move to a different module: commands?
    if opts.repair:
        plumber.repair_account(opts.acct)
        sys.exit(0)
    if opts.import_maildir and opts.acct:
        plumber.import_maildir(opts.acct, opts.import_maildir)
        sys.exit(0)
    # XXX catch when import is used w/o acct


def main():
    """
    Starts the main event loop and launches the main window.
    """
    # Parse arguments and store them
    opts = leap_argparse.get_options()
    do_display_version(opts)

    bypass_checks = opts.danger
    start_hidden = opts.start_hidden

    flags.STANDALONE = opts.standalone
    flags.OFFLINE = opts.offline
    flags.MAIL_LOGFILE = opts.mail_log_file
    flags.APP_VERSION_CHECK = opts.app_version_check
    flags.API_VERSION_CHECK = opts.api_version_check
    flags.OPENVPN_VERBOSITY = opts.openvpn_verb
    flags.SKIP_WIZARD_CHECKS = opts.skip_wizard_checks

    flags.CA_CERT_FILE = opts.ca_cert_file

    replace_stdout = True
    if opts.repair or opts.import_maildir:
        # We don't want too much clutter on the comand mode
        # this could be more generic with a Command class.
        replace_stdout = False

    logger = create_logger(opts.debug, opts.log_file, replace_stdout)

    # ok, we got logging in place, we can satisfy mail plumbing requests
    # and show logs there. it normally will exit there if we got that path.
    do_mail_plumbing(opts)

    try:
        event_server.ensure_server(event_server.SERVER_PORT)
    except Exception as e:
        # We don't even have logger configured in here
        print "Could not ensure server: %r" % (e,)

    PLAY_NICE = os.environ.get("LEAP_NICE")
    if PLAY_NICE and PLAY_NICE.isdigit():
        nice = os.nice(int(PLAY_NICE))
        logger.info("Setting NICE: %s" % nice)

    # TODO move to a different module: commands?
    if not we_are_the_one_and_only():
        # Bitmask is already running
        logger.warning("Tried to launch more than one instance "
                       "of Bitmask. Raising the existing "
                       "one instead.")
        sys.exit(1)

    check_requirements()

    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logger.info('Bitmask version %s', VERSION)
    logger.info('leap.mail version %s', MAIL_VERSION)
    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    logger.info('Starting app')

    # We force the style if on KDE so that it doesn't load all the kde
    # libs, which causes a compatibility issue in some systems.
    # For more info, see issue #3194
    if flags.STANDALONE and os.environ.get("KDE_SESSION_UID") is not None:
        sys.argv.append("-style")
        sys.argv.append("Cleanlooks")

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

    # XXX ---------------------------------------------------------
    # In quarantine, looks like we don't need it anymore.
    # This dummy timer ensures that control is given to the outside
    # loop, so we can hook our sigint handler.
    #timer = QtCore.QTimer()
    #timer.start(500)
    #timer.timeout.connect(lambda: None)
    # XXX ---------------------------------------------------------

    window = MainWindow(bypass_checks=bypass_checks,
                        start_hidden=start_hidden)

    sigint_window = partial(sigint_handler, window, logger=logger)
    signal.signal(signal.SIGINT, sigint_window)

    # callable used in addSystemEventTrigger to handle SIGTERM
    sigterm_window = partial(sigterm_handler, window, logger=logger)

    l = LoopingCall(QtCore.QCoreApplication.processEvents, 0, 10)
    l.start(0.01)

    # SIGTERM can't be handled the same way SIGINT is, since it's
    # caught by twisted. See _handleSignals method in
    # twisted/internet/base.py#L1150. So, addSystemEventTrigger
    # reactor's method is used.
    reactor.addSystemEventTrigger('before', 'shutdown', sigterm_window)
    reactor.run()

if __name__ == "__main__":
    main()
