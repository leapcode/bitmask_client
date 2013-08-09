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
import sys

from leap.mail.imap.service import imap
from twisted.python import log

logger = logging.getLogger(__name__)


def start_imap_service(*args, **kwargs):
    """
    Initializes and run imap service.

    :returns: twisted.internet.task.LoopingCall instance
    """
    logger.debug('Launching imap service')

    # Uncomment the next two lines to get a separate debugging log
    # TODO handle this by a separate flag.
    #log.startLogging(open('/tmp/leap-imap.log', 'w'))
    #log.startLogging(sys.stdout)

    return imap.run_service(*args, **kwargs)
