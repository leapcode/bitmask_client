# -*- coding: utf-8 -*-
# mail_status.py
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
Mail Status Panel widget implementation
"""
from PySide import QtCore, QtGui

from leap.bitmask.logs.utils import get_logger
from leap.bitmask.platform_init import IS_LINUX
from leap.bitmask.services import get_service_display_name, MX_SERVICE
from leap.common.check import leap_assert, leap_assert_type
from leap.common.events import register
from leap.common.events import catalog

from ui_mail_status import Ui_MailStatusWidget

logger = get_logger()


class MailStatusWidget(QtGui.QWidget):
    """
    Status widget that displays the state of the LEAP Mail service
    """
    _soledad_event = QtCore.Signal(object, object)
    _smtp_event = QtCore.Signal(object)
    _imap_event = QtCore.Signal(object, object)
    _keymanager_event = QtCore.Signal(object)

    def __init__(self, parent=None):
        """
        Constructor for MailStatusWidget

        :param parent: parent widget for this one.
        :type parent: QtGui.QWidget
        """
        QtGui.QWidget.__init__(self, parent)

        self._systray = None
        self._disabled = True
        self._started = False

        self._unread_mails = 0

        self.ui = Ui_MailStatusWidget()
        self.ui.setupUi(self)

        # set systray tooltip status
        self._mx_status = ""
        self._service_name = get_service_display_name(MX_SERVICE)

        # Set the Mail status icons
        self.CONNECTING_ICON = None
        self.CONNECTED_ICON = None
        self.ERROR_ICON = None
        self.CONNECTING_ICON_TRAY = None
        self.CONNECTED_ICON_TRAY = None
        self.ERROR_ICON_TRAY = None
        self._set_mail_icons()

        register(event=catalog.KEYMANAGER_LOOKING_FOR_KEY,
                 callback=self._mail_handle_keymanager_events)
        register(event=catalog.KEYMANAGER_KEY_FOUND,
                 callback=self._mail_handle_keymanager_events)
        register(event=catalog.KEYMANAGER_KEY_NOT_FOUND,
                 callback=self._mail_handle_keymanager_events)
        register(event=catalog.KEYMANAGER_STARTED_KEY_GENERATION,
                 callback=self._mail_handle_keymanager_events)
        register(event=catalog.KEYMANAGER_FINISHED_KEY_GENERATION,
                 callback=self._mail_handle_keymanager_events)
        register(event=catalog.KEYMANAGER_DONE_UPLOADING_KEYS,
                 callback=self._mail_handle_keymanager_events)

        register(event=catalog.SOLEDAD_DONE_DOWNLOADING_KEYS,
                 callback=self._mail_handle_soledad_events)
        register(event=catalog.SOLEDAD_DONE_UPLOADING_KEYS,
                 callback=self._mail_handle_soledad_events)
        register(event=catalog.SOLEDAD_SYNC_RECEIVE_STATUS,
                 callback=self._mail_handle_soledad_events)
        register(event=catalog.SOLEDAD_SYNC_SEND_STATUS,
                 callback=self._mail_handle_soledad_events)
        register(event=catalog.SOLEDAD_INVALID_AUTH_TOKEN,
                 callback=self.set_soledad_invalid_auth_token)
        register(event=catalog.SOLEDAD_DONE_DATA_SYNC,
                 callback=self._mail_handle_soledad_events)

        register(event=catalog.MAIL_UNREAD_MESSAGES,
                 callback=self._mail_handle_imap_events)
        register(event=catalog.IMAP_SERVICE_STARTED,
                 callback=self._mail_handle_imap_events)
        register(event=catalog.SMTP_SERVICE_STARTED,
                 callback=self._mail_handle_imap_events)

        self._soledad_event.connect(
            self._mail_handle_soledad_events_slot)
        self._imap_event.connect(
            self._mail_handle_imap_events_slot)
        self._smtp_event.connect(
            self._mail_handle_smtp_events_slot)
        self._keymanager_event.connect(
            self._mail_handle_keymanager_events_slot)

    def _set_mail_icons(self):
        """
        Sets the Mail status icons for the main window and for the tray

        MAC   : dark icons
        LINUX : dark icons in window, light icons in tray
        WIN   : light icons
        """
        EIP_ICONS = EIP_ICONS_TRAY = (
            ":/images/black/22/wait.png",
            ":/images/black/22/on.png",
            ":/images/black/22/off.png")

        if IS_LINUX:
            EIP_ICONS_TRAY = (
                ":/images/white/22/wait.png",
                ":/images/white/22/on.png",
                ":/images/white/22/off.png")

        self.CONNECTING_ICON = QtGui.QPixmap(EIP_ICONS[0])
        self.CONNECTED_ICON = QtGui.QPixmap(EIP_ICONS[1])
        self.ERROR_ICON = QtGui.QPixmap(EIP_ICONS[2])

        self.CONNECTING_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[0])
        self.CONNECTED_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[1])
        self.ERROR_ICON_TRAY = QtGui.QPixmap(EIP_ICONS_TRAY[2])

    # Systray and actions

    def set_systray(self, systray):
        """
        Sets the systray object to use and adds the service line for MX.

        :param systray: Systray object
        :type systray: QtGui.QSystemTrayIcon
        """
        leap_assert_type(systray, QtGui.QSystemTrayIcon)
        self._systray = systray
        mx_status = self.tr("{0}: OFF").format(self._service_name)
        self._systray.set_service_tooltip(MX_SERVICE, mx_status)

    def _update_systray_tooltip(self):
        """
        Updates the system tray tooltip using the mx status.
        """
        if self._systray is not None:
            mx_status = u"{0}: {1}".format(self._service_name, self._mx_status)
            self._systray.set_service_tooltip(MX_SERVICE, mx_status)

    def set_action_mail_status(self, action_mail_status):
        """
        Sets the action_mail_status to use.

        :param action_mail_status: action_mail_status to be used
        :type action_mail_status: QtGui.QAction
        """
        leap_assert_type(action_mail_status, QtGui.QAction)
        self._action_mail_status = action_mail_status

    def set_soledad_failed(self):
        """
        TRIGGERS:
            Signaler.soledad_bootstrap_failed

        This method is called whenever soledad has a failure.
        """
        msg = self.tr("There was an unexpected problem with Soledad.")
        self._set_mail_status(msg, ready=-1)

    def set_soledad_invalid_auth_token(self, event, content):
        """
        This method is called when the auth token is invalid

        :param event: The event that triggered the callback.
        :type event: str
        :param content: The content of the event.
        :type content: list
        """
        msg = self.tr("Invalid auth token, try logging in again.")
        self._set_mail_status(msg, ready=-1)

    def _set_mail_status(self, status, ready=0):
        """
        Sets the Mail status in the label and in the tray icon.

        :param status: the status text to display
        :type status: unicode
        :param ready: 2 or >2 if mx is ready, 0 if stopped, 1 if it's
                      starting, < 0 if disabled.
        :type ready: int
        """
        self.ui.lblMailStatus.setText(status)

        self._mx_status = self.tr('OFF')
        tray_status = self.tr('Mail is OFF')

        icon = self.ERROR_ICON
        if ready == 0:
            self.ui.lblMailStatus.setText(
                self.tr("You must be logged in to use {0}.").format(
                    self._service_name))
        elif ready == 1:
            icon = self.CONNECTING_ICON
            self._mx_status = self.tr('Starting...')
            tray_status = self.tr('Mail is starting')
        elif ready >= 2:
            icon = self.CONNECTED_ICON
            self._mx_status = self.tr('ON')
            tray_status = self.tr('Mail is ON')
        elif ready < 0:
            tray_status = self.tr("Mail is disabled")

        self.ui.lblMailStatusIcon.setPixmap(icon)
        self._action_mail_status.setText(tray_status)
        self._update_systray_tooltip()

    def _mail_handle_soledad_events(self, event, content):
        """
        Callback for handling events that are emitted from Soledad

        :param event: The event that triggered the callback.
        :type event: str
        :param content: The content of the event.
        :type content: dict
        """
        self._soledad_event.emit(event, content)

    def _mail_handle_soledad_events_slot(self, event, content):
        """
        TRIGGERS:
            _mail_handle_soledad_events

        Reacts to an Soledad event

        :param event: The event that triggered the callback.
        :type event: str
        :param content: The content of the event.
        :type content: dict
        """
        self._set_mail_status(self.tr("Starting..."), ready=1)

        ext_status = ""
        ready = None

        if event == catalog.SOLEDAD_DONE_UPLOADING_KEYS:
            ext_status = self.tr("Soledad has started...")
            ready = 1
        elif event == catalog.SOLEDAD_DONE_DOWNLOADING_KEYS:
            ext_status = self.tr("Soledad is starting, please wait...")
            ready = 1
        elif event == catalog.SOLEDAD_SYNC_RECEIVE_STATUS:
            sync_progress = content['received'] * 100 / content['total']
            if sync_progress < 100:
                ext_status = self.tr("Sync: downloading ({0:02}%)")
                ext_status = ext_status.format(sync_progress)
            else:
                ext_status = self.tr("Sync: download completed.")

            ready = 2
        elif event == catalog.SOLEDAD_SYNC_SEND_STATUS:
            sync_progress = content['sent'] * 100 / content['total']
            if sync_progress < 100:
                ext_status = self.tr("Sync: uploading ({0:02}%)")
                ext_status = ext_status.format(sync_progress)
            else:
                ext_status = self.tr("Sync: upload complete.")

            ready = 2
        elif event == catalog.SOLEDAD_DONE_DATA_SYNC:
            if self._unread_mails > 0:
                self._show_unread_mails()
                return
            else:
                ext_status = self.tr("Sync: completed.")

            ready = 2
        else:
            leap_assert(False,
                        "Don't know how to handle this state: %s"
                        % (event))

        self._set_mail_status(ext_status, ready=ready)

    def _mail_handle_keymanager_events(self, event, content):
        """
        Callback for the KeyManager events

        :param event: The event that triggered the callback.
        :type event: str
        :param content: The content of the event.
        :type content: list
        """
        self._keymanager_event.emit(event)

    def _mail_handle_keymanager_events_slot(self, event):
        """
        TRIGGERS:
            _mail_handle_keymanager_events

        Reacts to an KeyManager event

        :param event: The event that triggered the callback.
        :type event: str
        """
        # We want to ignore this kind of events once everything has
        # started
        if self._started:
            return

        ext_status = ""

        if event == catalog.KEYMANAGER_LOOKING_FOR_KEY:
            ext_status = self.tr("Initial sync in progress, please wait...")
        elif event == catalog.KEYMANAGER_KEY_FOUND:
            ext_status = self.tr("Found key! Starting mail...")
        elif event == catalog.KEYMANAGER_KEY_NOT_FOUND:
            ext_status = self.tr(
                "Key not found...")
        elif event == catalog.KEYMANAGER_STARTED_KEY_GENERATION:
            ext_status = self.tr(
                "Generating new key, this may take a few minutes.")
        elif event == catalog.KEYMANAGER_FINISHED_KEY_GENERATION:
            ext_status = self.tr("Finished generating key!")
        elif event == catalog.KEYMANAGER_DONE_UPLOADING_KEYS:
            ext_status = self.tr("Starting mail...")
        else:
            logger.warning("don't know to to handle %s" % (event,))
        self._set_mail_status(ext_status, ready=1)

    def _mail_handle_smtp_events(self, event):
        """
        Callback for the SMTP events

        :param event: The event that triggered the callback.
        :type event: str
        """
        self._smtp_event.emit(event)

    def _mail_handle_smtp_events_slot(self, event):
        """
        TRIGGERS:
            _mail_handle_smtp_events

        Reacts to an SMTP event

        :param event: The event that triggered the callback.
        :type event: str
        """
        ext_status = ""

        if event == catalog.SMTP_SERVICE_STARTED:
            self._smtp_started = True
        elif event == catalog.SMTP_SERVICE_FAILED_TO_START:
            ext_status = self.tr("SMTP failed to start, check the logs.")
        else:
            leap_assert(False,
                        "Don't know how to handle this state: %s"
                        % (event))

        self._set_mail_status(ext_status, ready=2)

    # ----- XXX deprecate (move to mail conductor)

    def _mail_handle_imap_events(self, event, content):
        """
        Callback for the IMAP events

        :param event: The event that triggered the callback.
        :type event: str
        :param content: The content of the event.
        :type content: list
        """
        self._imap_event.emit(event, content)

    def _mail_handle_imap_events_slot(self, event, content):
        """
        TRIGGERS:
            _mail_handle_imap_events

        Reacts to an IMAP event

        :param event: The event that triggered the callback.
        :type event: str
        :param content: The content of the event.
        :type content: list
        """
        ext_status = None

        if event == catalog.MAIL_UNREAD_MESSAGES:
            # By now, the semantics of the UNREAD_MAIL event are
            # limited to mails with the Unread flag *in the Inbox".
            # We could make this configurable to include all unread mail
            # or all unread mail in subscribed folders.
            if self._started:
                try:
                    self._unread_mails = int(content)
                except:
                    self._unread_mails = 0

                self._show_unread_mails()
        elif event == catalog.IMAP_SERVICE_STARTED:
            self._imap_started = True
        if ext_status is not None:
            self._set_mail_status(ext_status, ready=1)

    def _show_unread_mails(self):
        """
        Show the user the amount of unread emails.
        """
        count = self._unread_mails

        if count > 0:
            status = self.tr("{0} Unread Emails "
                             "in your Inbox").format(count)
            if count == 1:
                status = self.tr("1 Unread Email in your Inbox")

            self._set_mail_status(status, ready=2)
        else:
            self._set_mail_status("", ready=2)

    def about_to_start(self):
        """
        Display the correct UI for the point where mail components
        haven't really started, but they are about to in a second.
        """
        self._set_mail_status(self.tr("About to start, please wait..."),
                              ready=1)

    def set_disabled(self):
        """
        Display the correct UI for disabled mail.
        """
        self._set_mail_status(self.tr("Disabled"), -1)

    # statuses

    # XXX make the signal emit the label and state.

    def mail_state_disconnected(self):
        """
        Display the correct UI for the disconnected state.
        """
        # XXX this should handle the disabled state better.
        self._started = False
        if self._disabled:
            self.mail_state_disabled()
        else:
            self._set_mail_status(self.tr("OFF"), -1)

    def mail_state_connecting(self):
        """
        Display the correct UI for the connecting state.
        """
        self._disabled = False
        self._started = True
        self._set_mail_status(self.tr("Starting..."), 1)

    def mail_state_disconnecting(self):
        """
        Display the correct UI for the connecting state.
        """
        self._set_mail_status(self.tr("Disconnecting..."), 1)

    def mail_state_connected(self):
        """
        Display the correct UI for the connected state.
        """
        self._set_mail_status(self.tr("ON"), 2)

    def mail_state_disabled(self):
        """
        Display the correct UI for the disabled state.
        """
        self._disabled = True
        status = self.tr("You must be logged in to use {0}.").format(
            self._service_name)
        self._set_mail_status(status, -1)

    def soledad_invalid_auth_token(self):
        """
        Display the correct UI for the invalid token state
        """
        self._disabled = True
        status = self.tr("Invalid auth token, try logging in again.")
        self._set_mail_status(status, -1)
