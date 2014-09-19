# -*- coding: utf-8 -*-
# passwordwindow.py
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
Change password dialog window
"""

from PySide import QtCore, QtGui
from leap.bitmask.util.credentials import password_checks

from leap.bitmask.gui.ui_password_change import Ui_PasswordChange
from leap.bitmask.gui.flashable import Flashable

import logging
logger = logging.getLogger(__name__)


class PasswordWindow(QtGui.QDialog, Flashable):

    _current_window = None  # currently visible password window

    def __init__(self, parent, account, app):
        """
        :param parent: parent object of the PreferencesWindow.
        :parent type: QWidget

        :param account: the user set in the login widget
        :type account: Account

        :param app: App instance
        :type app: App
        """
        QtGui.QDialog.__init__(self, parent)

        self.account = account
        self.app = app
        self._backend_connect()

        self.ui = Ui_PasswordChange()
        self.ui.setupUi(self)

        self.hide_flash()
        self.ui.ok_button.clicked.connect(self._change_password)
        self.ui.cancel_button.clicked.connect(self.close)
        self.ui.username_lineedit.setText(account.address)

        if PasswordWindow._current_window is not None:
            PasswordWindow._current_window.close()
        PasswordWindow._current_window = self

        self._disabled = False  # if set to True, never again enable widgets.

        if account.username is None:
            # should not ever happen, but just in case
            self._disabled = True
            self._enable_password_widgets(False)
            self.ui.cancel_button.setEnabled(True)
            self.flash_error(self.tr("Please log in to change your password."))

        if self.is_soledad_needed() and not self._soledad_ready:
            self._enable_password_widgets(False)
            self.ui.cancel_button.setEnabled(True)
            self.flash_message(
                self.tr("Please wait for data storage to be ready."))

    def is_soledad_needed(self):
        """
        Returns true if the current account needs to change the soledad
        password as well as the SRP password.
        """
        return self.account.is_email_enabled()

    #
    # MANAGE WIDGETS
    #

    def _enable_password_widgets(self, enabled):
        """
        Enables or disables the widgets in the password change group box.

        :param enabled: True if the widgets should be enabled.
                        False if widgets should be disabled and
                        display the status label that shows that is
                        changing the password.
        :type enabled: bool
        """
        if self._disabled:
            return

        if enabled:
            self.hide_flash()
        else:
            self.flash_message(self.tr("Changing password..."))

        self.ui.current_password_lineedit.setEnabled(enabled)
        self.ui.new_password_lineedit.setEnabled(enabled)
        self.ui.new_password_confirmation_lineedit.setEnabled(enabled)
        self.ui.ok_button.setEnabled(enabled)
        self.ui.cancel_button.setEnabled(enabled)

    def _change_password_success(self):
        """
        Callback used to display a successfully changed password.
        """
        logger.debug("Password changed successfully.")
        self._clear_password_inputs()
        self._enable_password_widgets(True)
        self.flash_success(self.tr("Password changed successfully."))

    def _clear_password_inputs(self):
        """
        Clear the contents of the inputs.
        """
        self.ui.current_password_lineedit.setText("")
        self.ui.new_password_lineedit.setText("")
        self.ui.new_password_confirmation_lineedit.setText("")

    #
    # SLOTS
    #

    def _backend_connect(self):
        """
        Helper to connect to backend signals
        """
        sig = self.app.signaler
        sig.srp_password_change_ok.connect(self._srp_change_password_ok)
        sig.srp_password_change_error.connect(self._srp_password_change_error)
        sig.srp_password_change_badpw.connect(self._srp_password_change_badpw)
        sig.soledad_password_change_ok.connect(
            self._soledad_change_password_ok)
        sig.soledad_password_change_error.connect(
            self._soledad_change_password_problem)

        self._soledad_ready = False
        sig.soledad_bootstrap_finished.connect(self._on_soledad_ready)

    @QtCore.Slot()
    def _change_password(self):
        """
        TRIGGERS:
            self.ui.buttonBox.accepted

        Changes the user's password if the inputboxes are correctly filled.
        """
        current_password = self.ui.current_password_lineedit.text()
        new_password = self.ui.new_password_lineedit.text()
        new_password2 = self.ui.new_password_confirmation_lineedit.text()

        self._enable_password_widgets(True)

        if len(current_password) == 0:
            self.flash_error(self.tr("Password is empty."))
            self.ui.current_password_lineedit.setFocus()
            return

        ok, msg, field = password_checks(self.account.username, new_password,
                                         new_password2)
        if not ok:
            self.flash_error(msg)
            if field == 'new_password':
                self.ui.new_password_lineedit.setFocus()
            elif field == 'new_password_confirmation':
                self.ui.new_password_confirmation_lineedit.setFocus()
            return

        self._enable_password_widgets(False)
        self.app.backend.user_change_password(
            current_password=current_password,
            new_password=new_password)

    def closeEvent(self, event=None):
        """
        TRIGGERS:
            cancel_button (indirectly via self.close())
            or when window is closed

        Close this dialog & delete ourselves to clean up signals.
        """
        PasswordWindow._current_window = None
        self.deleteLater()

    @QtCore.Slot()
    def _srp_change_password_ok(self):
        """
        TRIGGERS:
            self._backend.signaler.srp_password_change_ok

        Callback used to display a successfully changed password.
        """
        new_password = self.ui.new_password_lineedit.text()
        logger.debug("SRP password changed successfully.")

        if self.is_soledad_needed():
            self._backend.soledad_change_password(new_password=new_password)
        else:
            self._change_password_success()

    @QtCore.Slot()
    def _srp_password_change_error(self):
        """
        TRIGGERS:
            self._backend.signaler.srp_password_change_error

        Unknown problem changing password
        """
        msg = self.tr("There was a problem changing the password.")
        logger.error(msg)
        self._enable_password_widgets(True)
        self.flash_error(msg)

    @QtCore.Slot()
    def _srp_password_change_badpw(self):
        """
        TRIGGERS:
            self._backend.signaler.srp_password_change_badpw

        The password the user entered was wrong.
        """
        msg = self.tr("You did not enter a correct current password.")
        logger.error(msg)
        self._enable_password_widgets(True)
        self.flash_error(msg)
        self.ui.current_password_lineedit.setFocus()

    @QtCore.Slot()
    def _soledad_change_password_ok(self):
        """
        TRIGGERS:
            Signaler.soledad_password_change_ok

        Soledad password change went OK.
        """
        logger.debug("Soledad password changed successfully.")
        self._change_password_success()

    @QtCore.Slot(unicode)
    def _soledad_change_password_problem(self, msg):
        """
        TRIGGERS:
            Signaler.soledad_password_change_error

        Callback used to display an error on changing password.

        :param msg: the message to show to the user.
        :type msg: unicode
        """
        logger.error("Error changing soledad password: %s" % (msg,))
        self._enable_password_widgets(True)
        self.flash_error(msg)

    @QtCore.Slot()
    def _on_soledad_ready(self):
        """
        TRIGGERS:
            Signaler.soledad_bootstrap_finished
        """
        self._enable_password_widgets(True)
        self._soledad_ready = True
