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

from functools import partial
from PySide import QtGui

from leap.bitmask.gui.ui_preferences import Ui_Preferences
from leap.soledad.client import NoStorageSecret
from leap.bitmask.crypto.srpauth import SRPAuthBadPassword
from leap.bitmask.util.password import basic_password_checks

logger = logging.getLogger(__name__)


class PreferencesWindow(QtGui.QDialog):
    """
    Window that displays the preferences.
    """

    WEAK_PASSWORDS = ("123456", "qweasd", "qwerty", "password")

    def __init__(self, parent, srp_auth, soledad):
        """
        :param parent: parent object of the PreferencesWindow.
        :parent type: QWidget
        :param srp_auth: SRPAuth object configured in the main app.
        :type srp_auth: SRPAuth
        :param soledad: Soledad object configured in the main app.
        :type soledad: Soledad
        """
        QtGui.QDialog.__init__(self, parent)

        self._srp_auth = srp_auth
        self._soledad = soledad

        # Load UI
        self.ui = Ui_Preferences()
        self.ui.setupUi(self)
        self.ui.lblPasswordChangeStatus.setVisible(False)

        # Connections
        self.ui.pbChangePassword.clicked.connect(self._change_password)

    def _set_password_change_status(self, status, error=False, success=False):
        """
        Sets the status label for the password change.

        :param status: status message to display, can be HTML
        :type status: str
        """
        if error:
            status = "<font color='red'><b>%s</b></font>" % (status,)
        elif success:
            status = "<font color='green'><b>%s</b></font>" % (status,)

        self.ui.lblPasswordChangeStatus.setVisible(True)
        self.ui.lblPasswordChangeStatus.setText(status)

    def _set_changing_password(self, disable):
        """
        Enables or disables the widgets in the password change group box.

        :param disable: True if the widgets should be disabled and
                        it displays the status label that shows that is
                        changing the password.
                        False if they should be enabled.
        :type disable: bool
        """
        if disable:
            self._set_password_change_disable(self.tr("Changing password..."))

        self.ui.leCurrentPassword.setEnabled(not disable)
        self.ui.leNewPassword.setEnabled(not disable)
        self.ui.leNewPassword2.setEnabled(not disable)
        self.ui.pbChangePassword.setEnabled(not disable)

    def _change_password(self):
        """
        Changes the user's password if the inputboxes are correctly filled.
        """
        username = self._srp_auth.get_username()
        current_password = self.ui.leCurrentPassword.text()
        new_password = self.ui.leNewPassword.text()
        new_password2 = self.ui.leNewPassword2.text()

        ok, msg = basic_password_checks(username, new_password, new_password2)

        if not ok:
            self._set_changing_password(False)
            self._set_password_change_status(msg, error=True)
            self.ui.leNewPassword.setFocus()
            return

        self._set_changing_password(True)
        d = self._srp_auth.change_password(current_password, new_password)
        d.addCallback(partial(self._change_password_success, new_password))
        d.addErrback(self._change_password_problem)

    def _change_password_success(self, new_password, _):
        """
        Callback used to display a successfully performed action.

        :param new_password: the new password for the user.
        :type new_password: str.
        :param _: the returned data from self._srp_auth.change_password
                  Ignored
        """
        logger.debug("SRP password changed successfully.")
        try:
            self._soledad.change_passphrase(str(new_password))
            logger.debug("Soledad password changed successfully.")
        except NoStorageSecret:
            logger.debug(
                "No storage secret for password change in Soledad.")

        self._set_password_change_status(
            self.tr("Password changed successfully."), success=True)
        self._clear_inputs()
        self._set_changing_password(False)

    def _change_password_problem(self, failure):
        """
        Errback called if there was a problem with the deferred.
        Also is used to display an error message.

        :param failure: the cause of the method failed.
        :type failure: twisted.python.Failure
        """
        logger.error("Error changing password: %s", (failure, ))
        problem = self.tr("There was a problem changing the password.")

        if failure.check(SRPAuthBadPassword):
            problem = self.tr("You did not enter a correct current password.")

        self._set_password_change_status(problem, error=True)

        self._set_changing_password(False)
        failure.trap(Exception)

    def _clear_inputs(self):
        """
        Clear the contents of the inputs.
        """
        self.ui.leCurrentPassword.setText("")
        self.ui.leNewPassword.setText("")
        self.ui.leNewPassword2.setText("")
