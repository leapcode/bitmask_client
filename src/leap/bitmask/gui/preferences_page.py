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
base class for preference pages
"""

from PySide import QtCore, QtGui

class PreferencesPage(QtGui.QWidget):

    def __init__(self, parent, account=None, app=None):
        """
        :param parent: parent object of the EIPPreferencesWindow.
        :type parent: QWidget

        :param account: the currently active account
        :type account: Account

        :param app: shared App instance
        :type app: App
        """
        QtGui.QWidget.__init__(self, parent)
        self.app = app
        self.account = account

    def setup_connections(self):
        """
        connect signals
        must be overridden by subclass
        """

    def teardown_connections(self):
        """
        disconnect signals
        must be overridden by subclass
        """

