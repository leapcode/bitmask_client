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

from twisted.internet import error

# Resist the temptation of putting the import reactor here,
# it will raise an "reactor already imported" error.

logger = logging.getLogger(__name__)


def quit(app):
    """
    Stop the mainloop.

    :param app: the main qt QApplication instance.
    :type app: QtCore.QApplication
    """
    from twisted.internet import reactor
    logger.debug('Stopping twisted reactor')
    try:
        reactor.callLater(0, reactor.stop)
    except error.ReactorNotRunning:
        logger.debug('Reactor not running')
