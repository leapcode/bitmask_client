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

from PySide import QtGui

from leap.keymanager import openpgp
from leap.keymanager.errors import KeyAddressMismatch, KeyFingerprintMismatch
from leap.bitmask.services import get_service_display_name, MX_SERVICE
from ui_advanced_key_management import Ui_AdvancedKeyManagement

logger = logging.getLogger(__name__)


class AdvancedKeyManagement(QtGui.QDialog):
    """
    Advanced Key Management
    """
    def __init__(self, parent, has_mx, user, keymanager, soledad_started):
        """
        :param parent: parent object of AdvancedKeyManagement.
        :parent type: QWidget
        :param has_mx: defines whether the current provider provides email or
                       not.
        :type has_mx: bool
        :param user: the current logged in user.
        :type user: unicode
        :param keymanager: the existing keymanager instance
        :type keymanager: KeyManager
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

        self._keymanager = keymanager

        self._key = keymanager.get_key(user, openpgp.OpenPGPKey)
        self._key_priv = keymanager.get_key(
            user, openpgp.OpenPGPKey, private=True)

        # show current key information
        self.ui.leUser.setText(user)
        self.ui.leKeyID.setText(self._key.key_id)
        self.ui.leFingerprint.setText(self._key.fingerprint)

        # set up connections
        self.ui.pbImportKeys.clicked.connect(self._import_keys)
        self.ui.pbExportKeys.clicked.connect(self._export_keys)

        # Stretch columns to content
        self.ui.twPublicKeys.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)

        self._list_keys()

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
        fileName, filtr = QtGui.QFileDialog.getOpenFileName(
            self, self.tr("Open keys file"),
            options=QtGui.QFileDialog.DontUseNativeDialog)

        if fileName:
            new_key = ''
            try:
                with open(fileName, 'r') as keys_file:
                    new_key = keys_file.read()
            except IOError as e:
                logger.error("IOError importing key. {0!r}".format(e))
                QtGui.QMessageBox.critical(
                    self, self.tr("Input/Output error"),
                    self.tr("There was an error accessing the file.\n"
                            "Import canceled."))
                return

            keymanager = self._keymanager
            try:
                public_key, private_key = keymanager.parse_openpgp_ascii_key(
                    new_key)
            except (KeyAddressMismatch, KeyFingerprintMismatch) as e:
                logger.error(repr(e))
                QtGui.QMessageBox.warning(
                    self, self.tr("Data mismatch"),
                    self.tr("The public and private key should have the "
                            "same address and fingerprint.\n"
                            "Import canceled."))
                return

            if public_key is None or private_key is None:
                QtGui.QMessageBox.warning(
                    self, self.tr("Missing key"),
                    self.tr("You need to provide the public AND private "
                            "key in the same file.\n"
                            "Import canceled."))
                return

            if public_key.address != self._key.address:
                logger.error("The key does not match the ID")
                QtGui.QMessageBox.warning(
                    self, self.tr("Address mismatch"),
                    self.tr("The identity for the key needs to be the same "
                            "as your user address.\n"
                            "Import canceled."))
                return

            question = self.tr("Are you sure that you want to replace "
                               "the current key pair whith the imported?")
            res = QtGui.QMessageBox.question(
                None, "Change key pair", question,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                QtGui.QMessageBox.No)  # default No

            if res == QtGui.QMessageBox.No:
                return

            keymanager.delete_key(self._key)
            keymanager.delete_key(self._key_priv)
            keymanager.put_key(public_key)
            keymanager.put_key(private_key)
            keymanager.send_key(openpgp.OpenPGPKey)

            logger.debug('Import ok')

            QtGui.QMessageBox.information(
                self, self.tr("Import Successful"),
                self.tr("The key pair was imported successfully."))
        else:
            logger.debug('Import canceled by the user.')

    def _export_keys(self):
        """
        Exports the user's key pair.
        """
        fileName, filtr = QtGui.QFileDialog.getSaveFileName(
            self, self.tr("Save keys file"),
            options=QtGui.QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                with open(fileName, 'w') as keys_file:
                    keys_file.write(self._key.key_data)
                    keys_file.write(self._key_priv.key_data)

                logger.debug('Export ok')
                QtGui.QMessageBox.information(
                    self, self.tr("Export Successful"),
                    self.tr("The key pair was exported successfully.\n"
                            "Please, store your private key in a safe place."))
            except IOError as e:
                logger.error("IOError exporting key. {0!r}".format(e))
                QtGui.QMessageBox.critical(
                    self, self.tr("Input/Output error"),
                    self.tr("There was an error accessing the file.\n"
                            "Export canceled."))
                return
        else:
            logger.debug('Export canceled by the user.')

    def _list_keys(self):
        """
        Loads all the public keys stored in the local db to the keys table.
        """
        keys = self._keymanager.get_all_keys_in_local_db()

        keys_table = self.ui.twPublicKeys
        for key in keys:
            row = keys_table.rowCount()
            keys_table.insertRow(row)
            keys_table.setItem(row, 0, QtGui.QTableWidgetItem(key.address))
            keys_table.setItem(row, 1, QtGui.QTableWidgetItem(key.key_id))
