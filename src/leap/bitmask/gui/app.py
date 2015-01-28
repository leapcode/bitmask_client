# -*- coding: utf-8 -*-
# Copyright (C) 2014 LEAP
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
A single App instances holds the signals that are shared among different
frontend UI components. The App also keeps a reference to the backend object
and the signaler get signals from the backend.
"""
import logging

from PySide import QtCore, QtGui

from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.backend.backend_proxy import BackendProxy
from leap.bitmask.backend.leapsignaler import LeapSignaler

logger = logging.getLogger(__name__)


class App(QtGui.QWidget):

    # the user has changed which services are enabled for a particular account
    # args: account (Account), active services (list of str)
    service_selection_changed = QtCore.Signal(object, list)

    def __init__(self):
        QtGui.QWidget.__init__(self)

        self.settings = LeapSettings()
        self.backend = BackendProxy()
        self.backend.start()
        self.signaler = LeapSignaler()
        self.signaler.start()

        # periodically check if the backend is alive
        self._backend_checker = QtCore.QTimer(self)
        self._backend_checker.timeout.connect(self._check_backend_status)
        self._backend_checker.start(2000)

    def _check_backend_status(self):
        """
        TRIGGERS:
            self._backend_checker.timeout

        Check that the backend is running. Otherwise show an error to the user.
        """
        if not self.backend.online:
            logger.critical("Backend is not online.")
            QtGui.QMessageBox.critical(
                self, self.tr("Application error"),
                self.tr("There is a problem contacting the backend, please "
                        "restart Bitmask."))
            self._backend_checker.stop()
