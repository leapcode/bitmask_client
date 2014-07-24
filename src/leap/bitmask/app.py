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
import multiprocessing
import os
import sys


from leap.bitmask.backend.utils import generate_certificates

from leap.bitmask import __version__ as VERSION
from leap.bitmask.config import flags
from leap.bitmask.frontend_app import run_frontend
from leap.bitmask.backend_app import run_backend
from leap.bitmask.logs.utils import create_logger
from leap.bitmask.platform_init.locks import we_are_the_one_and_only
from leap.bitmask.services.mail import plumber
from leap.bitmask.util import leap_argparse, flags_to_dict
from leap.bitmask.util.requirement_checker import check_requirements

from leap.common.events import server as event_server
from leap.mail import __version__ as MAIL_VERSION

import codecs
codecs.register(lambda name: codecs.lookup('utf-8')
                if name == 'cp65001' else None)

import psutil


def kill_the_children():
    """
    Make sure no lingering subprocesses are left in case of a bad termination.
    """
    me = os.getpid()
    parent = psutil.Process(me)
    print "Killing all the children processes..."
    for child in parent.get_children(recursive=True):
        try:
            child.terminate()
        except Exception as exc:
            print exc

# XXX This is currently broken, but we need to fix it to avoid
# orphaned processes in case of a crash.
# atexit.register(kill_the_children)


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


def start_app():
    """
    Starts the main event loop and launches the main window.
    """
    # Ignore the signals since we handle them in the subprocesses
    # signal.signal(signal.SIGINT, signal.SIG_IGN)

    # Parse arguments and store them
    opts = leap_argparse.get_options()
    do_display_version(opts)

    options = {
        'start_hidden': opts.start_hidden,
        'debug': opts.debug,
        'log_file': opts.log_file,
    }

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

    generate_certificates()

    flags_dict = flags_to_dict()

    backend = lambda: run_backend(opts.danger, flags_dict)
    backend_process = multiprocessing.Process(target=backend, name='Backend')
    backend_process.daemon = True
    backend_process.start()

    run_frontend(options, flags_dict, backend_pid=backend_process.pid)


if __name__ == "__main__":
    start_app()
