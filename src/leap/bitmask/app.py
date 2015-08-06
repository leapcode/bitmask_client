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
import atexit
import commands
import multiprocessing
import os
import platform
import sys

if platform.system() == "Darwin":
    # We need to tune maximum number of files, due to zmq usage
    # we hit the limit.
    import resource
    resource.setrlimit(resource.RLIMIT_NOFILE, (4096, 10240))

from leap.bitmask import __version__ as VERSION
from leap.bitmask.backend.backend_proxy import BackendProxy
from leap.bitmask.backend_app import run_backend
from leap.bitmask.config import flags
from leap.bitmask.frontend_app import run_frontend
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.platform_init.locks import we_are_the_one_and_only
from leap.bitmask.services.mail import plumber
from leap.bitmask.util import leap_argparse, flags_to_dict, here
from leap.bitmask.util.requirement_checker import check_requirements

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

    children = None
    try:
        # for psutil 0.2.x
        children = parent.get_children(recursive=True)
    except:
        # for psutil 0.3.x
        children = parent.children(recursive=True)

    for child in children:
        try:
            child.terminate()
        except Exception as exc:
            print exc

# XXX This is currently broken, but we need to fix it to avoid
# orphaned processes in case of a crash.
atexit.register(kill_the_children)


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


def log_lsb_release_info(logger):
    """
    Attempt to log distribution info from the lsb_release utility
    """
    if commands.getoutput('which lsb_release'):
        distro_info = commands.getoutput('lsb_release -a').split('\n')[-4:]
        logger.info("LSB Release info:")
        for line in distro_info:
            logger.info(line)

def fix_qtplugins_path():
    # This is a small workaround for a bug in macholib, there is a slight typo
    # in the path for the qt plugins that is added to the dynamic loader path
    # in the libs.
    if sys.platform in ('win32', 'darwin'):
        from PySide import QtCore
        plugins_path = os.path.join(os.path.dirname(here(QtCore)), 'plugins')
        QtCore.QCoreApplication.setLibraryPaths([plugins_path])


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
    }

    flags.STANDALONE = opts.standalone
    flags.OFFLINE = opts.offline
    flags.MAIL_LOGFILE = opts.mail_log_file
    flags.APP_VERSION_CHECK = opts.app_version_check
    flags.API_VERSION_CHECK = opts.api_version_check
    flags.OPENVPN_VERBOSITY = opts.openvpn_verb
    flags.SKIP_WIZARD_CHECKS = opts.skip_wizard_checks

    flags.CA_CERT_FILE = opts.ca_cert_file

    flags.DEBUG = opts.debug

    logger = get_logger(perform_rollover=True)

    # NOTE: since we are not using this right now, the code that replaces the
    # stdout needs to be reviewed when we enable this again
    # replace_stdout = True

    # XXX mail repair commands disabled for now
    # if opts.repair or opts.import_maildir:
    #    We don't want too much clutter on the comand mode
    #    this could be more generic with a Command class.
    #    replace_stdout = False

    # ok, we got logging in place, we can satisfy mail plumbing requests
    # and show logs there. it normally will exit there if we got that path.
    # XXX mail repair commands disabled for now
    # do_mail_plumbing(opts)

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
    logger.info('Bitmask version %s' % VERSION)
    logger.info('leap.mail version %s' % MAIL_VERSION)
    log_lsb_release_info(logger)
    logger.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logger.info('Starting app')

    backend_running = BackendProxy().check_online()
    logger.debug("Backend online: {0}".format(backend_running))

    flags_dict = flags_to_dict()

    backend_pid = None
    if not backend_running:
        frontend_pid = os.getpid()
        backend = lambda: run_backend(opts.danger, flags_dict, frontend_pid)
        backend_process = multiprocessing.Process(target=backend,
                                                  name='Backend')
        # we don't set the 'daemon mode' since we need to start child processes
        # in the backend
        # backend_process.daemon = True
        backend_process.start()
        backend_pid = backend_process.pid

    fix_qtplugins_path()
    run_frontend(options, flags_dict, backend_pid=backend_pid)


if __name__ == "__main__":
    start_app()
