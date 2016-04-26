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

from leap.bitmask.logs.utils import get_logger
from leap.bitmask.gui.ui_preferences import Ui_Preferences
from leap.bitmask.gui.preferences_page import PreferencesPage
from leap.bitmask.gui.preferences_account_page import PreferencesAccountPage
from leap.bitmask.gui.preferences_vpn_page import PreferencesVpnPage
from leap.bitmask.gui.preferences_email_page import PreferencesEmailPage

logger = get_logger()


class PreferencesWindow(QtGui.QDialog):

    """
    Window that displays the preferences.
    """

    _current_window = None  # currently visible preferences window

    def __init__(self, parent, app):
        """
        :param parent: parent object of the PreferencesWindow.
        :parent type: QWidget

        :param app: the current App object
        :type app: App
        """
        QtGui.QDialog.__init__(self, parent)

        self.app = app

        self.ui = Ui_Preferences()
        self.ui.setupUi(self)

        self._account_page = None
        self._vpn_page = None
        self._email_page = None

        self._add_icons()
        self._set_account(app.current_account())
        self._setup_connections()

        # only allow a single preferences window at a time.
        if PreferencesWindow._current_window is not None:
            PreferencesWindow._current_window.close()
        PreferencesWindow._current_window = self

    def _set_account(self, account):
        """
        Initially sets, or resets, the currently viewed account.
        The account might not represent an authenticated user, but
        just a domain.
        """
        self.ui.account_label.setText(account.address)
        self._add_pages(account)
        self._update_icons(account)
        self.ui.pages_widget.setCurrentIndex(0)
        self.ui.nav_widget.setCurrentRow(0)

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

    def _add_pages(self, account):
        """
        Adds the pages for the different configuration categories.
        """
        self._remove_pages()  # in case different account was loaded.

        # load placeholder widgets if the page should not be loaded.
        # the order of the pages is important, and must match the order
        # of the nav_widget icons.
        self._account_page = PreferencesAccountPage(self, account, self.app)
        if account.has_eip():
            self._vpn_page = PreferencesVpnPage(self, account, self.app)
        else:
            self._vpn_page = PreferencesPage(self)
        if account.has_email():
            self._email_page = PreferencesEmailPage(self, account, self.app)
        else:
            self._email_page = PreferencesPage(self)
        self.ui.pages_widget.addWidget(self._account_page)
        self.ui.pages_widget.addWidget(self._vpn_page)
        self.ui.pages_widget.addWidget(self._email_page)

    def _remove_pages(self):
        # deleteLater does not seem to cascade to items in stackLayout
        # (even with QtCore.Qt.WA_DeleteOnClose attribute).
        # so, here we call deleteLater() explicitly.
        if self._account_page is not None:
            self.ui.pages_widget.removeWidget(self._account_page)
            self._account_page.teardown_connections()
            self._account_page.deleteLater()
        if self._vpn_page is not None:
            self.ui.pages_widget.removeWidget(self._vpn_page)
            self._vpn_page.teardown_connections()
            self._vpn_page.deleteLater()
        if self._email_page is not None:
            self.ui.pages_widget.removeWidget(self._email_page)
            self._email_page.teardown_connections()
            self._email_page.deleteLater()

    def _setup_connections(self):
        """
        setup signal connections
        """
        self.ui.nav_widget.currentItemChanged.connect(self._change_page)
        self.ui.close_button.clicked.connect(self.close)
        self.app.service_selection_changed.connect(self._update_icons)
        sig = self.app.signaler
        sig.srp_auth_ok.connect(self._login_status_changed)
        sig.srp_logout_ok.connect(self._login_status_changed)
        sig.srp_status_logged_in.connect(self._update_account)
        sig.srp_status_not_logged_in.connect(self._update_account)

    def _teardown_connections(self):
        """
        clean up signal connections
        """
        self.ui.nav_widget.currentItemChanged.disconnect(self._change_page)
        self.ui.close_button.clicked.disconnect(self.close)
        self.app.service_selection_changed.disconnect(self._update_icons)
        sig = self.app.signaler
        sig.srp_auth_ok.disconnect(self._login_status_changed)
        sig.srp_logout_ok.disconnect(self._login_status_changed)
        sig.srp_status_logged_in.disconnect(self._update_account)
        sig.srp_status_not_logged_in.disconnect(self._update_account)

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
        self._teardown_connections()
        self._remove_pages()
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

    def _update_icons(self, account):
        """
        TRIGGERS:
            self.app.service_selection_changed

        Change which icons are visible.
        """
        self._vpn_item.setHidden(not account.has_eip())
        self._email_item.setHidden(not account.has_email())

    def _login_status_changed(self):
        """
        Triggered by signal srp_auth_ok, srp_logout_ok
        """
        self.app.backend.user_get_logged_in_status()

    def _update_account(self):
        """
        Triggered by get srp_status_logged_in, srp_status_not_logged_in
        """
        self._set_account(self.app.current_account())
