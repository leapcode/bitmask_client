# -*- coding: utf-8 -*-
# qt_browser.py
# Copyright (C) 2016 LEAP
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
QtWebKit-based browser to display Pixelated User Agent
"""

from PySide import QtCore, QtWebKit, QtGui

PIXELATED_URI = 'http://localhost:9090'


class PixelatedWindow(QtGui.QDialog):

    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.web = QtWebKit.QWebView(self)
        self.web.load(QtCore.QUrl(PIXELATED_URI))
        self.setWindowTitle('Bitmask/Pixelated WebMail')
        self.web.show()
