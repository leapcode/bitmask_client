# -*- coding: utf-8 -*-
# advanced_key_management.py
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
Advanced Key Management
"""
import logging

from PySide import QtCore, QtGui

from leap.bitmask.services import get_service_display_name, MX_SERVICE
from ui_advanced_key_management import Ui_AdvancedKeyManagement

logger = logging.getLogger(__name__)


class AdvancedKeyManagement(QtGui.QDialog):
    """
    Advanced Key Management
    """
    def __init__(self, parent, has_mx, user, backend, soledad_started):
        """
        :param parent: parent object of AdvancedKeyManagement.
        :parent type: QWidget
        :param has_mx: defines whether the current provider provides email or
                       not.
        :type has_mx: bool
        :param user: the current logged in user.
        :type user: unicode
        :param backend: Backend being used
        :type backend: Backend
        :param soledad_started: whether soledad has started or not
        :type soledad_started: bool
        """
        QtGui.QDialog.__init__(self, parent)

        self.ui = Ui_AdvancedKeyManagement()
        self.ui.setupUi(self)

        # XXX: Temporarily disable the key import.
        self.ui.pbImportKeys.setVisible(False)

        if not has_mx:
            msg = self.tr("The provider that you are using "
                          "does not support {0}.")
            msg = msg.format(get_service_display_name(MX_SERVICE))
            self._disable_ui(msg)
            return

        if not soledad_started:
            msg = self.tr("To use this, you need to enable/start {0}.")
            msg = msg.format(get_service_display_name(MX_SERVICE))
            self._disable_ui(msg)
            return
        # XXX: since import is disabled this is no longer a dangerous feature.
        # else:
        #     msg = self.tr(
        #         "<span style='color:#ff0000;'>WARNING</span>:<br>"
        #         "This is an experimental feature, you can lose access to "
        #         "existing e-mails.")
        #     self.ui.lblStatus.setText(msg)

        self._user = user
        self._backend = backend
        self._backend_connect()

        # show current key information
        self.ui.leUser.setText(user)

        # set up connections
        self.ui.pbImportKeys.clicked.connect(self._import_keys)
        self.ui.pbExportKeys.clicked.connect(self._export_keys)

        # Stretch columns to content
        self.ui.twPublicKeys.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)

        self._backend.keymanager_get_key_details(user)
        self._backend.keymanager_list_keys()

    def _keymanager_key_details(self, details):
        """
        Set the current user's key details into the gui.
        """
        self.ui.leKeyID.setText(details[0])
        self.ui.leFingerprint.setText(details[1])

    def _disable_ui(self, msg):
        """
        Disable the UI and set a note in the status bar.

        :param msg: note to display in the status bar.
        :type msg: unicode
        """
        self.ui.gbMyKeyPair.setEnabled(False)
        self.ui.gbStoredPublicKeys.setEnabled(False)
        msg = self.tr("<span style='color:#0000FF;'>NOTE</span>: ") + msg
        self.ui.lblStatus.setText(msg)

    def _import_keys(self):
        """
        Imports the user's key pair.
        Those keys need to be ascii armored.
        """
        file_name, filtr = QtGui.QFileDialog.getOpenFileName(
            self, self.tr("Open keys file"),
            options=QtGui.QFileDialog.DontUseNativeDialog)

        if file_name:
            question = self.tr("Are you sure that you want to replace "
                               "the current key pair with the imported?")
            res = QtGui.QMessageBox.question(
                None, "Change key pair", question,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No)  # default No

            if res == QtGui.QMessageBox.Yes:
                self._backend.keymanager_import_keys(self._user, file_name)
        else:
            logger.debug('Import canceled by the user.')

    @QtCore.Slot()
    def _keymanager_import_ok(self):
        """
        TRIGGERS:
            Signaler.keymanager_import_ok

        Notify the user that the key import went OK.
        """
        QtGui.QMessageBox.information(
            self, self.tr("Import Successful"),
            self.tr("The key pair was imported successfully."))

    @QtCore.Slot()
    def _import_ioerror(self):
        """
        TRIGGERS:
            Signaler.keymanager_import_ioerror

        Notify the user that the key import had an IOError problem.
        """
        QtGui.QMessageBox.critical(
            self, self.tr("Input/Output error"),
            self.tr("There was an error accessing the file.\n"
                    "Import canceled."))

    @QtCore.Slot()
    def _import_datamismatch(self):
        """
        TRIGGERS:
            Signaler.keymanager_import_datamismatch

        Notify the user that the key import had an data mismatch problem.
        """
        QtGui.QMessageBox.warning(
            self, self.tr("Data mismatch"),
            self.tr("The public and private key should have the "
                    "same address and fingerprint.\n"
                    "Import canceled."))

    @QtCore.Slot()
    def _import_missingkey(self):
        """
        TRIGGERS:
            Signaler.keymanager_import_missingkey

        Notify the user that the key import failed due a missing key.
        """
        QtGui.QMessageBox.warning(
            self, self.tr("Missing key"),
            self.tr("You need to provide the public AND private "
                    "key in the same file.\n"
                    "Import canceled."))

    @QtCore.Slot()
    def _import_addressmismatch(self):
        """
        TRIGGERS:
            Signaler.keymanager_import_addressmismatch

        Notify the user that the key import failed due an address mismatch.
        """
        QtGui.QMessageBox.warning(
            self, self.tr("Address mismatch"),
            self.tr("The identity for the key needs to be the same "
                    "as your user address.\n"
                    "Import canceled."))

    def _export_keys(self):
        """
        Exports the user's key pair.
        """
        file_name, filtr = QtGui.QFileDialog.getSaveFileName(
            self, self.tr("Save keys file"),
            options=QtGui.QFileDialog.DontUseNativeDialog)

        if file_name:
            self._backend.keymanager_export_keys(self._user, file_name)
        else:
            logger.debug('Export canceled by the user.')

    @QtCore.Slot()
    def _keymanager_export_ok(self):
        """
        TRIGGERS:
            Signaler.keymanager_export_ok

        Notify the user that the key export went OK.
        """
        QtGui.QMessageBox.information(
            self, self.tr("Export Successful"),
            self.tr("The key pair was exported successfully.\n"
                    "Please, store your private key in a safe place."))

    @QtCore.Slot()
    def _keymanager_export_error(self):
        """
        TRIGGERS:
            Signaler.keymanager_export_error

        Notify the user that the key export didn't go well.
        """
        QtGui.QMessageBox.critical(
            self, self.tr("Input/Output error"),
            self.tr("There was an error accessing the file.\n"
                    "Export canceled."))

    @QtCore.Slot()
    def _keymanager_keys_list(self, keys):
        """
        TRIGGERS:
            Signaler.keymanager_keys_list

        Load the keys given as parameter in the table.

        :param keys: the list of keys to load.
        :type keys: list
        """
        keys_table = self.ui.twPublicKeys

        for key in keys:
            row = keys_table.rowCount()
            keys_table.insertRow(row)
            keys_table.setItem(row, 0, QtGui.QTableWidgetItem(key.address))
            keys_table.setItem(row, 1, QtGui.QTableWidgetItem(key.key_id))

    def _backend_connect(self):
        """
        Connect to backend signals.
        """
        sig = self._backend.signaler

        sig.keymanager_export_ok.connect(self._keymanager_export_ok)
        sig.keymanager_export_error.connect(self._keymanager_export_error)
        sig.keymanager_keys_list.connect(self._keymanager_keys_list)

        sig.keymanager_key_details.connect(self._keymanager_key_details)

        sig.keymanager_import_ok.connect(self._keymanager_import_ok)

        sig.keymanager_import_ioerror.connect(self._import_ioerror)
        sig.keymanager_import_datamismatch.connect(self._import_datamismatch)
        sig.keymanager_import_missingkey.connect(self._import_missingkey)
        sig.keymanager_import_addressmismatch.connect(
            self._import_addressmismatch)
