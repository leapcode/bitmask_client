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
from PySide import QtCore, QtGui

from leap.bitmask.services import EIP_SERVICE
from leap.bitmask._components import HAS_EIP

from leap.bitmask.logs.utils import get_logger
from leap.bitmask.gui.ui_preferences import Ui_Preferences
from leap.bitmask.gui.preferences_account_page import PreferencesAccountPage
from leap.bitmask.gui.preferences_vpn_page import PreferencesVpnPage
from leap.bitmask.gui.preferences_email_page import PreferencesEmailPage

logger = get_logger()


class PreferencesWindow(QtGui.QDialog):

    """
    Window that displays the preferences.
    """

    _current_window = None  # currently visible preferences window

    def __init__(self, parent, account, app):
        """
        :param parent: parent object of the PreferencesWindow.
        :parent type: QWidget

        :param account: the user or provider
        :type account: Account

        :param app: the current App object
        :type app: App
        """
        QtGui.QDialog.__init__(self, parent)

        self.account = account
        self.app = app

        self.ui = Ui_Preferences()
        self.ui.setupUi(self)

        self.ui.close_button.clicked.connect(self.close)
        self.ui.account_label.setText(account.address)

        self.app.service_selection_changed.connect(self._update_icons)

        self._add_icons()
        self._add_pages()
        self._update_icons(self.account, self.account.services())

        # only allow a single preferences window at a time.
        if PreferencesWindow._current_window is not None:
            PreferencesWindow._current_window.close()
        PreferencesWindow._current_window = self

    def _add_icons(self):
        """
        Adds all the icons for the different configuration categories.
        Icons are QListWidgetItems added to the nav_widget on the side
        of the preferences window.

        A note on sizing of QListWidgetItems
          icon_width = list_widget.width - (2 x nav_widget.spacing) - 2
          icon_height = 56 seems to look ok
        """
        account_item = QtGui.QListWidgetItem(self.ui.nav_widget)
        account_item.setIcon(QtGui.QIcon(":/images/black/32/user.png"))
        account_item.setText(self.tr("Account"))
        account_item.setTextAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        account_item.setFlags(
            QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        account_item.setSizeHint(QtCore.QSize(98, 56))
        self._account_item = account_item

        vpn_item = QtGui.QListWidgetItem(self.ui.nav_widget)
        vpn_item.setHidden(True)
        vpn_item.setIcon(QtGui.QIcon(":/images/black/32/earth.png"))
        vpn_item.setText(self.tr("VPN"))
        vpn_item.setTextAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        vpn_item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        vpn_item.setSizeHint(QtCore.QSize(98, 56))
        self._vpn_item = vpn_item

        email_item = QtGui.QListWidgetItem(self.ui.nav_widget)
        email_item.setHidden(True)
        email_item.setIcon(QtGui.QIcon(":/images/black/32/email.png"))
        email_item.setText(self.tr("Email"))
        email_item.setTextAlignment(
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        email_item.setFlags(
            QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        email_item.setSizeHint(QtCore.QSize(98, 56))
        self._email_item = email_item

        self.ui.nav_widget.currentItemChanged.connect(self._change_page)
        self.ui.nav_widget.setCurrentRow(0)

    def _add_pages(self):
        """
        Adds the pages for the different configuration categories.
        """
        self._account_page = PreferencesAccountPage(
            self, self.account, self.app)
        self._vpn_page = PreferencesVpnPage(self, self.account, self.app)
        self._email_page = PreferencesEmailPage(self, self.account, self.app)

        self.ui.pages_widget.addWidget(self._account_page)
        self.ui.pages_widget.addWidget(self._vpn_page)
        self.ui.pages_widget.addWidget(self._email_page)

    #
    # Slots
    #

    def closeEvent(self, e):
        """
        TRIGGERS:
            self.ui.close_button.clicked
              (since self.close() will trigger closeEvent)
            whenever the window is closed

        Close this dialog and destroy it.
        """
        PreferencesWindow._current_window = None

        # deleteLater does not seem to cascade to items in stackLayout
        # (even with QtCore.Qt.WA_DeleteOnClose attribute).
        # so, here we call deleteLater() explicitly:
        self._account_page.deleteLater()
        self._vpn_page.deleteLater()
        self._email_page.deleteLater()
        self.deleteLater()

    def _change_page(self, current, previous):
        """
        TRIGGERS:
            self.ui.nav_widget.currentItemChanged

        Changes what page is displayed.

        :param current: the currently selected item (might be None?)
        :type current: PySide.QtGui.QListWidgetItem

        :param previous: the previously selected item (might be None)
        :type previous: PySide.QtGui.QListWidgetItem
        """
        if not current:
            current = previous
        self.ui.pages_widget.setCurrentIndex(self.ui.nav_widget.row(current))

    def _update_icons(self, account, services):
        """
        TRIGGERS:
            self.app.service_selection_changed

        Change which icons are visible.
        """
        if account != self.account:
            return

        if HAS_EIP:
            self._vpn_item.setHidden(EIP_SERVICE not in services)
        # self._email_item.setHidden(not MX_SERVICE in services)
        # ^^ disable email for now, there is nothing there yet.
