# -*- coding: utf-8 -*-
# checkerthread.py
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
Checker thread
"""

import logging

from PySide import QtCore

from leap.common.check import leap_assert_type

logger = logging.getLogger(__name__)


class CheckerThread(QtCore.QThread):
    """
    Generic checker thread that can perform any type of operation as
    long as it returns a boolean value that identifies how the
    execution went.
    """

    IDLE_SLEEP_INTERVAL = 1

    def __init__(self):
        QtCore.QThread.__init__(self)

        self._checks = []
        self._checks_lock = QtCore.QMutex()

        self._should_quit = False
        self._should_quit_lock = QtCore.QMutex()

    def get_should_quit(self):
        """
        Returns whether this thread should quit

        :return: True if the thread should terminate itself, Flase otherwise
        :rtype: bool
        """

        QtCore.QMutexLocker(self._should_quit_lock)
        return self._should_quit

    def set_should_quit(self):
        """
        Sets the should_quit flag to True so that this thread
        terminates the first chance it gets
        """
        QtCore.QMutexLocker(self._should_quit_lock)
        self._should_quit = True

    def start(self):
        """
        Starts the thread and resets the should_quit flag
        """
        with QtCore.QMutexLocker(self._should_quit_lock):
            self._should_quit = False

        QtCore.QThread.start(self)

    def add_checks(self, checks):
        """
        Adds a list of checks to the ones being executed

        :param checks: check functions to perform
        :type checkes: list
        """
        with QtCore.QMutexLocker(self._checks_lock):
            self._checks += checks

    def run(self):
        """
        Main run loop for this thread. Executes the checks.
        """
        shouldContinue = False
        while True:
            if self.get_should_quit():
                logger.debug("Quitting checker thread")
                return
            checkSomething = False
            with QtCore.QMutexLocker(self._checks_lock):
                if len(self._checks) > 0:
                    check = self._checks.pop(0)
                    shouldContinue = check()
                    leap_assert_type(shouldContinue, bool)
                    checkSomething = True
                    if not shouldContinue:
                        logger.debug("Something went wrong with the checks, "
                                     "clearing...")
                        self._checks = []
                        checkSomething = False
            if not checkSomething:
                self.sleep(self.IDLE_SLEEP_INTERVAL)
