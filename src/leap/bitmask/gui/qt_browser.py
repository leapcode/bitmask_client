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
import os
import urlparse

from PySide import QtCore, QtWebKit, QtGui, QtNetwork

PIXELATED_URI = 'http://localhost:9090'


class PixelatedWindow(QtGui.QDialog):

    def __init__(self, parent):
        super(PixelatedWindow, self).__init__(parent)
        self.view = QtWebKit.QWebView(self)

        layout = QtGui.QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)
        self.setWindowTitle('Bitmask Mail')

    def load_app(self):
        self.view.load(QtCore.QUrl(PIXELATED_URI))
        self.view.page().setForwardUnsupportedContent(True)
        self.view.page().unsupportedContent.connect(self.download)

        self.manager = QtNetwork.QNetworkAccessManager()
        self.manager.finished.connect(self.finished)

    def download(self, reply):
        self.request = QtNetwork.QNetworkRequest(reply.url())
        self.reply = self.manager.get(self.request)

    def finished(self):
        url = self.reply.url().toString()

        filename = urlparse.parse_qs(url).get('filename', None)
        if filename:
            filename = filename[0]
        name = filename or url

        path = os.path.expanduser(os.path.join(
            '~', unicode(name).split('/')[-1]))
        destination = QtGui.QFileDialog.getSaveFileName(self, "Save", path)
        if destination:
            filename = destination[0]
            with open(filename, 'wb') as f:
                f.write(str(self.reply.readAll()))
                f.close()
