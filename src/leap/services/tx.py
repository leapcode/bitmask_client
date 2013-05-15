# -*- coding: utf-8 -*-
# twisted.py
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
Twisted services launched by the client
"""
import logging

from twisted.application.service import Application
from twisted.internet.task import LoopingCall

logger = logging.getLogger(__name__)


def task():
    """
    stub periodic task, mainly for tests.
    DELETE-ME when there's real meat here :)
    """
    from datetime import datetime
    logger.debug("hi there %s", datetime.now())


def leap_services():
    """
    Check which twisted services are enabled and
    register them.
    """
    logger.debug('starting leap services')
    application = Application("LEAP Client Local Services")
    #lc = LoopingCall(task)
    #lc.start(5)
    return application
