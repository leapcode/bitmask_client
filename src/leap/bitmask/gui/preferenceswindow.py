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
Preferences window
"""
import logging

from PySide import QtCore, QtGui

from leap.bitmask.config.leapsettings import LeapSettings

from leap.bitmask.gui.ui_preferences import Ui_Preferences

from leap.bitmask.gui.preferences_account_page import PreferencesAccountPage
from leap.bitmask.gui.preferences_vpn_page import PreferencesVpnPage
from leap.bitmask.gui.preferences_email_page import PreferencesEmailPage

from leap.bitmask.services import get_service_display_name, MX_SERVICE

logger = logging.getLogger(__name__)


class PreferencesWindow(QtGui.QDialog):
    """
    Window that displays the preferences.
    """
    preferences_saved = QtCore.Signal()

    def __init__(self, parent, username, domain, backend, soledad_started, leap_signaler):
        """
        :param parent: parent object of the PreferencesWindow.
        :parent type: QWidget
        :param username: the user set in the login widget
        :type username: unicode
        :param domain: the selected domain in the login widget
        :type domain: unicode
        :param backend: Backend being used
        :type backend: Backend
        :param soledad_started: whether soledad has started or not
        :type soledad_started: bool
        :param leap_signaler: signal server
        :type leap_signaler: LeapSignaler
        """
        QtGui.QDialog.__init__(self, parent)

        self._parent = parent
        self._username = username
        self._domain = domain
        self._leap_signaler = leap_signaler
        self._backend = backend
        self._soledad_started = soledad_started

        self._settings = LeapSettings()

        # Load UI
        self.ui = Ui_Preferences()
        self.ui.setupUi(self)

        self.ui.close_button.clicked.connect(self.close)

        self._add_icons()
        self._add_pages()

    def _add_icons(self):
        """
        Adds all the icons for the different configuration categories.
        Icons are QListWidgetItems added to the nav_widget on the side
        of the preferences window.

        A note on sizing of QListWidgetItems
          icon_width = list_widget.width - (2 x nav_widget.spacing) - 2
          icon_height = 56 seems to look ok
        """
        account_button = QtGui.QListWidgetItem(self.ui.nav_widget)
        account_button.setIcon(QtGui.QIcon(":/images/black/32/user.png"))
        account_button.setText(self.tr("Account"))
        account_button.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        account_button.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        account_button.setSizeHint(QtCore.QSize(98,56))

        vpn_button = QtGui.QListWidgetItem(self.ui.nav_widget)
        vpn_button.setIcon(QtGui.QIcon(":/images/black/32/earth.png"))
        vpn_button.setText(self.tr("VPN"))
        vpn_button.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        vpn_button.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        vpn_button.setSizeHint(QtCore.QSize(98,56))

        email_button = QtGui.QListWidgetItem(self.ui.nav_widget)
        email_button.setIcon(QtGui.QIcon(":/images/black/32/email.png"))
        email_button.setText(self.tr("Email"))
        email_button.setTextAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        email_button.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        email_button.setSizeHint(QtCore.QSize(98,56))

        self.ui.nav_widget.currentItemChanged.connect(self._change_page)
        self.ui.nav_widget.setCurrentRow(0)

    def _add_pages(self):
        """
        Adds the pages for the different configuration categories.
        """
        self.ui.pages_widget.addWidget(PreferencesAccountPage(self))
        self.ui.pages_widget.addWidget(PreferencesVpnPage(self, self._domain, self._backend, self._leap_signaler))
        self.ui.pages_widget.addWidget(PreferencesEmailPage(self))

    #
    # Slots
    #

    @QtCore.Slot()
    def close(self):
        """
        TRIGGERS:
            self.ui.close_button.clicked

        Close this dialog
        """
        self._parent.preferences = None
        self.hide()

    @QtCore.Slot()
    def _change_page(self, current, previous):
        """
        TRIGGERS:
            self.ui.nav_widget.currentItemChanged

        Changes what page is displayed.
        """
        if not current:
            current = previous
        self.ui.pages_widget.setCurrentIndex(self.ui.nav_widget.row(current))
