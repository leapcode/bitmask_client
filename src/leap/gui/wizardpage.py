# -*- coding: utf-8 -*-
# wizardpage.py
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

from PySide import QtGui


class WizardPage(QtGui.QWizardPage):
    """
    Simple wizard page helper
    """

    def __init__(self):
        QtGui.QWizardPage.__init__(self)
        self._completed = False

    def set_completed(self):
        self._completed = True
        self.completeChanged.emit()

    def isComplete(self):
        return self._completed

    def cleanupPage(self):
        self._completed = False
        QtGui.QWizardPage.cleanupPage(self)
