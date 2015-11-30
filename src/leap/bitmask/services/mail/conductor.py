# -*- coding: utf-8 -*-
# conductor.py
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
Mail Services Conductor
"""
from leap.bitmask.config import flags
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.gui import statemachines
from leap.bitmask.services.mail import connection as mail_connection
from leap.bitmask.services.mail.emailfirewall import get_email_firewall

from leap.common.events import catalog
from leap.common.events import register as leap_register


logger = get_logger()


class IMAPControl(object):
    """
    Methods related to IMAP control.
    """
    def __init__(self):
        """
        Initializes smtp variables.
        """
        self.imap_machine = None
        self.imap_connection = None

        leap_register(event=catalog.IMAP_SERVICE_STARTED,
                      callback=self._handle_imap_events)
        leap_register(event=catalog.IMAP_SERVICE_FAILED_TO_START,
                      callback=self._handle_imap_events)
        leap_register(event=catalog.IMAP_CLIENT_LOGIN,
                      callback=self._handle_imap_events)

    def set_imap_connection(self, imap_connection):
        """
        Set the imap connection to an initialized connection.

        :param imap_connection: an initialized imap connection
        :type imap_connection: IMAPConnection instance.
        """
        self.imap_connection = imap_connection

    def start_imap_service(self):
        """
        Start imap service.
        """
        self._backend.imap_start_service(full_user_id=self.userid,
                                         offline=flags.OFFLINE)

    def stop_imap_service(self):
        """
        Stop imap service.
        """
        self.imap_connection.qtsigs.disconnecting_signal.emit()
        logger.debug('Stopping imap service.')

        self._backend.imap_stop_service()

    def _handle_imap_events(self, event, userid=None, content=None):
        """
        Callback handler for the IMAP events

        :param event: The event that triggered the callback.
        :type event: str
        :param userid: The user id of the logged in user. Ignored.
        :param content: The content of the event.
        :type content: list
        """
        if event == catalog.IMAP_SERVICE_STARTED:
            self._on_imap_connected()
        elif event == catalog.IMAP_SERVICE_FAILED_TO_START:
            self._on_imap_failed()
        elif event == catalog.IMAP_CLIENT_LOGIN:
            self._on_mail_client_logged_in()

    def _on_mail_client_logged_in(self):
        """
        On mail client logged in, fetch incoming mail.
        """
        # XXX needs to be adapted to the new-ish incoming mail service.
        # Doing nothing for now, this could be moved to mail package itself.
        logger.debug("A MUA has logged in, should react by forcing a fetch.")

    def _on_imap_connecting(self):
        """
        Callback for IMAP connecting state.
        """
        self.imap_connection.qtsigs.connecting_signal.emit()

    def _on_imap_connected(self):
        """
        Callback for IMAP connected state.
        """
        self.imap_connection.qtsigs.connected_signal.emit()

    def _on_imap_failed(self):
        """
        Callback for IMAP failed state.
        """
        self.imap_connection.qtsigs.connection_aborted_signal.emit()


class SMTPControl(object):
    def __init__(self):
        """
        Initializes smtp variables.
        """
        self.smtp_connection = None
        self.smtp_machine = None

        leap_register(event=catalog.SMTP_SERVICE_STARTED,
                      callback=self._handle_smtp_events)
        leap_register(event=catalog.SMTP_SERVICE_FAILED_TO_START,
                      callback=self._handle_smtp_events)

    def set_smtp_connection(self, smtp_connection):
        """
        Sets the smtp connection to an initialized connection.
        :param smtp_connection: an initialized smtp connection
        :type smtp_connection: SMTPConnection instance.
        """
        self.smtp_connection = smtp_connection

    def start_smtp_service(self, download_if_needed=False):
        """
        Starts the SMTP service.

        :param download_if_needed: True if it should check for mtime
                                   for the file
        :type download_if_needed: bool
        """
        self.smtp_connection.qtsigs.connecting_signal.emit()
        self._backend.smtp_start_service(full_user_id=self.userid,
                                         download_if_needed=download_if_needed)

    def stop_smtp_service(self):
        """
        Stops the SMTP service.
        """
        self.smtp_connection.qtsigs.disconnecting_signal.emit()
        self._backend.smtp_stop_service()

    def _handle_smtp_events(self, event, content):
        """
        Callback handler for the SMTP events.

        :param event: The event that triggered the callback.
        :type event: str
        :param content: The content of the event.
        :type content: list
        """
        if event == catalog.SMTP_SERVICE_STARTED:
            self.on_smtp_connected()
        elif event == catalog.SMTP_SERVICE_FAILED_TO_START:
            self.on_smtp_failed()

    def on_smtp_connecting(self):
        """
        Callback for SMTP connecting state.
        """
        self.smtp_connection.qtsigs.connecting_signal.emit()

    def on_smtp_connected(self):
        """
        Callback for SMTP connected state.
        """
        self.smtp_connection.qtsigs.connected_signal.emit()

    def on_smtp_failed(self):
        """
        Callback for SMTP failed state.
        """
        self.smtp_connection.qtsigs.connection_aborted_signal.emit()


class MailConductor(IMAPControl, SMTPControl):
    """
    This class encapsulates everything related to the initialization and
    process control for the mail services.
    Currently, it initializes IMAPConnection and SMPTConnection.
    """
    # XXX We could consider to use composition instead of inheritance here.

    def __init__(self, backend):
        """
        Initializes the mail conductor.

        :param backend: Backend being used
        :type backend: Backend
        """
        IMAPControl.__init__(self)
        SMTPControl.__init__(self)

        self._mail_services_started = False

        self._backend = backend
        self._mail_machine = None
        self._mail_connection = mail_connection.MailConnection()

        self._userid = None
        try:
            self._firewall = get_email_firewall()
        except NotImplementedError:
            self._firewall = None
            logger.info("Email firewall is not implemented in this platform")

    @property
    def userid(self):
        return self._userid

    @userid.setter
    def userid(self, userid):
        """
        Sets the user id this conductor is configured for.

        :param userid: the user id, in the form "user@provider"
        :type userid: str
        """
        self._userid = userid

    def start_mail_machine(self, **kwargs):
        """
        Starts mail machine.
        """
        logger.debug("Starting mail state machine...")
        builder = statemachines.ConnectionMachineBuilder(self._mail_connection)
        (mail, (imap, smtp)) = builder.make_machine(**kwargs)

        # we have instantiated the connections while building the composite
        # machines, and we have to use the qtsigs instantiated there.
        self.set_imap_connection(imap.conn)
        self.set_smtp_connection(smtp.conn)

        self._mail_machine = mail
        self._mail_machine.start()

        self._imap_machine = imap
        self._imap_machine.start()
        self._smtp_machine = smtp
        self._smtp_machine.start()

    def start_mail_service(self, download_if_needed=False, offline=False):
        """
        Start the IMAP and SMTP servcies.
        """
        if self._firewall is not None:
            self._firewall.start()
        if not offline:
            logger.debug("Starting smtp service...")
            self.start_smtp_service(download_if_needed=download_if_needed)
        self.start_imap_service()

        self._mail_services_started = True

    def stop_mail_services(self):
        """
        Stop the IMAP and SMTP services.
        """
        if not self._mail_services_started:
            logger.debug("Mail services not started.")
            return

        self.stop_imap_service()
        self.stop_smtp_service()
        if self._firewall is not None:
            self._firewall.stop()

    def connect_mail_signals(self, widget):
        """
        Connects the mail signals to the mail_status widget slots.

        :param widget: the widget containing the slots.
        :type widget: QtCore.QWidget
        """
        qtsigs = self._mail_connection.qtsigs
        qtsigs.connected_signal.connect(widget.mail_state_connected)
        qtsigs.connecting_signal.connect(widget.mail_state_connecting)
        qtsigs.disconnecting_signal.connect(widget.mail_state_disconnecting)
        qtsigs.disconnected_signal.connect(widget.mail_state_disconnected)
        qtsigs.soledad_invalid_auth_token.connect(
            widget.soledad_invalid_auth_token)
