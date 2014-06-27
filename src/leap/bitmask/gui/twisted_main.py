# -*- coding: utf-8 -*-
# twisted_main.py
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
Main functions for integration of twisted reactor
"""
import logging

from twisted.internet import error, reactor
from PySide import QtCore

logger = logging.getLogger(__name__)


def stop():
    QtCore.QCoreApplication.sendPostedEvents()
    QtCore.QCoreApplication.flush()
    try:
        reactor.stop()
        logger.debug('Twisted reactor stopped')
    except error.ReactorNotRunning:
        logger.debug('Twisted reactor not running')
    logger.debug("Done stopping all the things.")


def quit():
    """
    Stop the mainloop.
    """
    reactor.callLater(0, stop)
