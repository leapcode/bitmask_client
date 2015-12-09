# -*- coding: utf-8 -*-
# imap.py
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
"""
Initialization of imap service
"""
import os
import sys

from twisted.python import log

from leap.bitmask.logs.utils import get_logger
from leap.mail.constants import INBOX_NAME
from leap.mail.imap.service import imap
from leap.mail.incoming.service import IncomingMail, INCOMING_CHECK_PERIOD
from leap.mail.mail import Account


logger = get_logger()

# The name of the environment variable that has to be
# set to override the default time value, in seconds.
INCOMING_CHECK_PERIOD_ENV = "BITMASK_MAILCHECK_PERIOD"


def get_mail_check_period():
    """
    Tries to get the value of the environment variable for
    overriding the period for incoming mail fetch.
    """
    period = None
    period_str = os.environ.get(INCOMING_CHECK_PERIOD_ENV, None)
    try:
        period = int(period_str)
    except (ValueError, TypeError):
        if period is not None:
            logger.warning("BAD value found for %s: %s" % (
                INCOMING_CHECK_PERIOD_ENV,
                period_str))
    except Exception as exc:
        logger.warning("Unhandled error while getting %s: %r" % (
            INCOMING_CHECK_PERIOD_ENV,
            exc))

    if period is None:
        period = INCOMING_CHECK_PERIOD
    return period


def start_imap_service(soledad_sessions):
    """
    Initializes and run imap service.

    :returns: the port as returned by the reactor when starts listening, and
              the factory for the protocol.
    :rtype: tuple
    """
    from leap.bitmask.config import flags
    logger.debug('Launching imap service')

    if flags.MAIL_LOGFILE:
        log.startLogging(open(flags.MAIL_LOGFILE, 'w'))
        log.startLogging(sys.stdout)

    return imap.run_service(soledad_sessions)


def start_incoming_mail_service(keymanager, soledad, userid):
    """
    Initalizes and starts the incomming mail service.

    :returns: a Deferred that will be fired with the IncomingMail instance
    """
    def setUpIncomingMail(inbox):
        incoming_mail = IncomingMail(
            keymanager, soledad,
            inbox, userid,
            check_period=get_mail_check_period())
        return incoming_mail

    acc = Account(soledad)
    d = acc.callWhenReady(lambda _: acc.get_collection_by_mailbox(INBOX_NAME))
    d.addCallback(setUpIncomingMail)
    d.addErrback(log.err)
    return d
