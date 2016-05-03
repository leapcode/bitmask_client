# -*- coding: utf-8 -*-
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
Widget for "email" preferences
"""
from PySide import QtCore, QtGui

from leap.bitmask.config.leapsettings import LeapSettings
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.gui.ui_preferences_email_page import Ui_PreferencesEmailPage
from leap.bitmask.gui.preferences_page import PreferencesPage
from leap.bitmask.pix import HAS_PIXELATED
from leap.mail.imap.service.imap import IMAP_PORT


logger = get_logger()


class PreferencesEmailPage(PreferencesPage):

    def __init__(self, parent, account, app):
        """
        :param parent: parent object of the PreferencesWindow.
        :parent type: QWidget

        :param account: user account (user + provider or just provider)
        :type account: Account

        :param app: the current App object
        :type app: App
        """
        PreferencesPage.__init__(self, parent, account, app)
        self.settings = LeapSettings()
        self.ui = Ui_PreferencesEmailPage()
        self.ui.setupUi(self)

        # the only way to set the tab titles is to re-add them:
        self.ui.email_tabs.addTab(self.ui.config_tab,
                                  self.tr("Mail Client"))
        self.ui.email_tabs.addTab(self.ui.my_key_tab,
                                  self.tr("My Key"))
        self.ui.email_tabs.addTab(self.ui.other_keys_tab,
                                  self.tr("Other Keys"))

        # set mail client configuration help text
        lang = QtCore.QLocale.system().name().replace('_', '-')
        thunderbird_extension_url = \
            "https://addons.mozilla.org/{0}/" \
            "thunderbird/addon/bitmask/".format(lang)
        self.ui.thunderbird_label.setText(self.tr(
            "For Thunderbird, you can use the Bitmask extension. "
            "Search for \"Bitmask\" in the add-on manager or "
            "download it from <a href='{0}'>addons.mozilla.org</a>.".format(
                thunderbird_extension_url)))

        self.ui.mail_client_label.setText(self.tr(
            "Alternatively, you can manually configure your mail client to "
            "use Bitmask with these options:"))

        self.ui.webmail_label.setText(self.tr(
            "Bitmask Mail is an integrated mail client based "
            "on <a href='https://pixelated-project.org/'>Pixelated "
            "User Agent</a>. If enabled, any user on your device "
            "can read your mail by opening http://localhost:9090"))

        self.ui.keys_table.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)

        self.setup_connections()

    def setup_connections(self):
        """
        connect signals
        """
        self.app.signaler.keymanager_key_details.connect(self._key_details)
        self.app.signaler.keymanager_keys_list.connect(
            self._keymanager_keys_list)
        self.app.signaler.keymanager_export_ok.connect(
            self._keymanager_export_ok)
        self.app.signaler.keymanager_export_error.connect(
            self._keymanager_export_error)
        self.ui.import_button.clicked.connect(self._import_keys)
        self.ui.export_button.clicked.connect(self._export_keys)
        self.ui.webmail_checkbox.stateChanged.connect(self._toggle_webmail)

    def teardown_connections(self):
        """
        disconnect signals
        """
        self.app.signaler.keymanager_key_details.disconnect(self._key_details)
        self.app.signaler.keymanager_export_ok.disconnect(
            self._keymanager_export_ok)
        self.app.signaler.keymanager_export_error.disconnect(
            self._keymanager_export_error)

    def showEvent(self, event):
        """
        called whenever this widget is shown
        """
        self.ui.keys_table.clearContents()

        if self.account.username is None:
            self.ui.email_tabs.setVisible(False)
            self.ui.message_label.setVisible(True)
            self.ui.message_label.setText(
                self.tr('You must be logged in to edit email settings.'))
        else:
            webmail_enabled = self.settings.get_pixelmail_enabled()
            self.ui.webmail_checkbox.setChecked(webmail_enabled)
            if not HAS_PIXELATED:
                self.ui.webmail_box.setVisible(False)
            self.ui.import_button.setVisible(False)  # hide this until working
            self.ui.message_label.setVisible(False)
            self.ui.email_tabs.setVisible(True)
            smtp_port = 2013
            self.ui.imap_port_edit.setText(str(IMAP_PORT))
            self.ui.imap_host_edit.setText("127.0.0.1")
            self.ui.smtp_port_edit.setText(str(smtp_port))
            self.ui.smtp_host_edit.setText("127.0.0.1")
            self.ui.username_edit.setText(self.account.address)
            self.ui.password_edit.setText(
                self.app.service_tokens.get('mail_auth', ''))

            self.app.backend.keymanager_list_keys()
            self.app.backend.keymanager_get_key_details(
                username=self.account.address)

    def _key_details(self, details):
        """
        Trigger by signal: keymanager_key_details
        Set the current user's key details into the gui.
        """
        self.ui.fingerprint_edit.setPlainText(
            self._format_fingerprint(details["fingerprint"]))
        self.ui.expiration_edit.setText(details["expiry_date"])
        self.ui.uid_edit.setText(" ".join(details["uids"]))
        self.ui.public_key_edit.setPlainText(details["key_data"])

    def _format_fingerprint(self, fingerprint):
        """
        formats an openpgp fingerprint in a manner similar to what gpg
        produces, wrapped to two lines.
        """
        fp = fingerprint.upper()
        fp_list = [fp[i:i + 4] for i in range(0, len(fp), 4)]
        fp_wrapped = " ".join(fp_list[0:5]) + "\n" + " ".join(fp_list[5:10])
        return fp_wrapped

    def _export_keys(self):
        """
        Exports the user's key pair.
        """
        file_name, filtr = QtGui.QFileDialog.getSaveFileName(
            self, self.tr("Save private key file"),
            filter="*.pem",
            options=QtGui.QFileDialog.DontUseNativeDialog)

        if file_name:
            if not file_name.endswith('.pem'):
                file_name += '.pem'
            self.app.backend.keymanager_export_keys(
                username=self.account.address,
                filename=file_name)
        else:
            logger.debug('Export canceled by the user.')

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

    def _import_keys(self):
        """
        not yet supported
        """

    def _keymanager_keys_list(self, keys):
        """
        TRIGGERS:
            Signaler.keymanager_keys_list

        Load the keys given as parameter in the table.

        :param keys: the list of keys to load.
        :type keys: list
        """
        for key in keys:
            row = self.ui.keys_table.rowCount()
            self.ui.keys_table.insertRow(row)
            address = key["address"]
            if not address:  # can be None if it's not active
                address = "--"
            self.ui.keys_table.setItem(
                row, 0, QtGui.QTableWidgetItem(address))
            self.ui.keys_table.setItem(
                row, 1, QtGui.QTableWidgetItem(key["fingerprint"]))

    def _toggle_webmail(self, state):
        value = True if state == QtCore.Qt.Checked else False
        self.settings.set_pixelmail_enabled(value)
