# -*- coding: utf-8 -*-
# preferenceswindow.py
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
Preferences log window
"""
import logging

from PySide import QtGui

from leap.bitmask.gui.ui_preferences import Ui_Preferences
from leap.bitmask.crypto.srpauth import SRPAuthBadPassword

logger = logging.getLogger(__name__)


class PreferencesWindow(QtGui.QDialog):
    """
    Window that displays the preferences.
    """
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)

        # Load UI
        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
