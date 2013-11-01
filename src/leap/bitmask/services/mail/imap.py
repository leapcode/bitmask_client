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
import logging
import os
#import sys

from leap.mail.imap.service import imap
#from twisted.python import log

logger = logging.getLogger(__name__)

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
    return period


def start_imap_service(*args, **kwargs):
    """
    Initializes and run imap service.

    :returns: twisted.internet.task.LoopingCall instance
    """
    logger.debug('Launching imap service')

    override_period = get_mail_check_period()
    if override_period:
        kwargs['check_period'] = override_period

    # Uncomment the next two lines to get a separate debugging log
    # TODO handle this by a separate flag.
    #log.startLogging(open('/tmp/leap-imap.log', 'w'))
    #log.startLogging(sys.stdout)

    return imap.run_service(*args, **kwargs)
