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
import logging
import os

from PySide import QtCore
from zope.proxy import sameProxiedObjects

from leap.bitmask.gui import statemachines
from leap.bitmask.services.mail import imap
from leap.bitmask.services.mail import connection as mail_connection
from leap.bitmask.services.mail.smtpbootstrapper import SMTPBootstrapper
from leap.bitmask.services.mail.smtpconfig import SMTPConfig
from leap.bitmask.util import is_file

from leap.common.check import leap_assert

from leap.common.events import register as leap_register
from leap.common.events import events_pb2 as leap_events

logger = logging.getLogger(__name__)


class IMAPControl(object):
    """
    Methods related to IMAP control.
    """
    def __init__(self):
        """
        Initializes smtp variables.
        """
        self.imap_machine = None
        self.imap_service = None
        self.imap_port = None
        self.imap_factory = None
        self.imap_connection = None

        leap_register(signal=leap_events.IMAP_SERVICE_STARTED,
                      callback=self._handle_imap_events,
                      reqcbk=lambda req, resp: None)
        leap_register(signal=leap_events.IMAP_SERVICE_FAILED_TO_START,
                      callback=self._handle_imap_events,
                      reqcbk=lambda req, resp: None)

    def set_imap_connection(self, imap_connection):
        """
        Sets the imap connection to an initialized connection.

        :param imap_connection: an initialized imap connection
        :type imap_connection: IMAPConnection instance.
        """
        self.imap_connection = imap_connection

    def start_imap_service(self):
        """
        Starts imap service.
        """
        from leap.bitmask.config import flags

        logger.debug('Starting imap service')
        leap_assert(sameProxiedObjects(self._soledad, None)
                    is not True,
                    "We need a non-null soledad for initializing imap service")
        leap_assert(sameProxiedObjects(self._keymanager, None)
                    is not True,
                    "We need a non-null keymanager for initializing imap "
                    "service")

        offline = flags.OFFLINE
        self.imap_service, self.imap_port, \
            self.imap_factory = imap.start_imap_service(
                self._soledad,
                self._keymanager,
                userid=self.userid,
                offline=offline)

        if offline is False:
            logger.debug("Starting loop")
            self.imap_service.start_loop()

    def stop_imap_service(self, cv):
        """
        Stops imap service (fetcher, factory and port).

        :param cv: A condition variable to which we can signal when imap
                   indeed stops.
        :type cv: threading.Condition
        """
        self.imap_connection.qtsigs.disconnecting_signal.emit()
        # TODO We should homogenize both services.
        if self.imap_service is not None:
            logger.debug('Stopping imap service.')
            # Stop the loop call in the fetcher
            self.imap_service.stop()
            self.imap_service = None
            # Stop listening on the IMAP port
            self.imap_port.stopListening()
            # Stop the protocol
            self.imap_factory.theAccount.closed = True
            self.imap_factory.doStop(cv)
        else:
            # main window does not have to wait because there's no service to
            # be stopped, so we release the condition variable
            cv.acquire()
            cv.notify()
            cv.release()

    def fetch_incoming_mail(self):
        """
        Fetches incoming mail.
        """
        if self.imap_service:
            logger.debug('Client connected, fetching mail...')
            self.imap_service.fetch()

    # handle events

    def _handle_imap_events(self, req):
        """
        Callback handler for the IMAP events

        :param req: Request type
        :type req: leap.common.events.events_pb2.SignalRequest
        """
        if req.event == leap_events.IMAP_SERVICE_STARTED:
            self.on_imap_connected()
        elif req.event == leap_events.IMAP_SERVICE_FAILED_TO_START:
            self.on_imap_failed()

    # emit connection signals

    def on_imap_connecting(self):
        """
        Callback for IMAP connecting state.
        """
        self.imap_connection.qtsigs.connecting_signal.emit()

    def on_imap_connected(self):
        """
        Callback for IMAP connected state.
        """
        self.imap_connection.qtsigs.connected_signal.emit()

    def on_imap_failed(self):
        """
        Callback for IMAP failed state.
        """
        self.imap_connection.qtsigs.connetion_aborted_signal.emit()


class SMTPControl(object):

    PORT_KEY = "port"
    IP_KEY = "ip_address"

    def __init__(self):
        """
        Initializes smtp variables.
        """
        self.smtp_config = SMTPConfig()
        self.smtp_connection = None
        self.smtp_machine = None
        self._smtp_service = None
        self._smtp_port = None

        self.smtp_bootstrapper = SMTPBootstrapper()
        self.smtp_bootstrapper.download_config.connect(
            self.smtp_bootstrapped_stage)

        leap_register(signal=leap_events.SMTP_SERVICE_STARTED,
                      callback=self._handle_smtp_events,
                      reqcbk=lambda req, resp: None)
        leap_register(signal=leap_events.SMTP_SERVICE_FAILED_TO_START,
                      callback=self._handle_smtp_events,
                      reqcbk=lambda req, resp: None)

    def set_smtp_connection(self, smtp_connection):
        """
        Sets the smtp connection to an initialized connection.
        :param smtp_connection: an initialized smtp connection
        :type smtp_connection: SMTPConnection instance.
        """
        self.smtp_connection = smtp_connection

    def start_smtp_service(self, host, port, cert):
        """
        Starts the smtp service.

        :param host: the hostname of the remove SMTP server.
        :type host: str
        :param port: the port of the remote SMTP server
        :type port: str
        :param cert: the client certificate for authentication
        :type cert: str
        """
        # TODO Make the encrypted_only configurable
        # TODO pick local smtp port in a better way
        # TODO remove hard-coded port and let leap.mail set
        # the specific default.
        self.smtp_connection.qtsigs.connecting_signal.emit()
        from leap.mail.smtp import setup_smtp_gateway
        self._smtp_service, self._smtp_port = setup_smtp_gateway(
            port=2013,
            userid=self.userid,
            keymanager=self._keymanager,
            smtp_host=host,
            smtp_port=port,
            smtp_cert=cert,
            smtp_key=cert,
            encrypted_only=False)

    def stop_smtp_service(self):
        """
        Stops the smtp service (port and factory).
        """
        self.smtp_connection.qtsigs.disconnecting_signal.emit()
        # TODO We should homogenize both services.
        if self._smtp_service is not None:
            logger.debug('Stopping smtp service.')
            self._smtp_port.stopListening()
            self._smtp_service.doStop()

    @QtCore.Slot()
    def smtp_bootstrapped_stage(self, data):
        """
        SLOT
        TRIGGERS:
          self.smtp_bootstrapper.download_config

        If there was a problem, displays it, otherwise it does nothing.
        This is used for intermediate bootstrapping stages, in case
        they fail.

        :param data: result from the bootstrapping stage for Soledad
        :type data: dict
        """
        passed = data[self.smtp_bootstrapper.PASSED_KEY]
        if not passed:
            logger.error(data[self.smtp_bootstrapper.ERROR_KEY])
            return
        logger.debug("Done bootstrapping SMTP")
        self.check_smtp_config()

    def check_smtp_config(self):
        """
        Checks smtp config and tries to download smtp client cert if needed.
        Currently called when smtp_bootstrapped_stage has successfuly finished.
        """
        logger.debug("Checking SMTP config...")
        leap_assert(self.smtp_bootstrapper._provider_config,
                    "smtp bootstrapper does not have a provider_config")

        provider_config = self.smtp_bootstrapper._provider_config
        smtp_config = self.smtp_config
        hosts = smtp_config.get_hosts()
        # TODO handle more than one host and define how to choose
        if len(hosts) > 0:
            hostname = hosts.keys()[0]
            logger.debug("Using hostname %s for SMTP" % (hostname,))
            host = hosts[hostname][self.IP_KEY].encode("utf-8")
            port = hosts[hostname][self.PORT_KEY]

            client_cert = smtp_config.get_client_cert_path(
                provider_config,
                about_to_download=True)

            # XXX change this logic!
            # check_config should be called from within start_service,
            # and not the other way around.
            if not is_file(client_cert):
                self.smtp_bootstrapper._download_client_certificates()
            if os.path.isfile(client_cert):
                self.start_smtp_service(host, port, client_cert)
            else:
                logger.warning("Tried to download email client "
                               "certificate, but could not find any")

        else:
            logger.warning("No smtp hosts configured")

    # handle smtp events

    def _handle_smtp_events(self, req):
        """
        Callback handler for the SMTP events.

        :param req: Request type
        :type req: leap.common.events.events_pb2.SignalRequest
        """
        if req.event == leap_events.SMTP_SERVICE_STARTED:
            self.on_smtp_connected()
        elif req.event == leap_events.SMTP_SERVICE_FAILED_TO_START:
            self.on_smtp_failed()

    # emit connection signals

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

    def __init__(self, soledad, keymanager):
        """
        Initializes the mail conductor.

        :param soledad: a transparent proxy that eventually will point to a
                        Soledad Instance.
        :type soledad: zope.proxy.ProxyBase

        :param keymanager: a transparent proxy that eventually will point to a
                           Keymanager Instance.
        :type soledad: zope.proxy.ProxyBase
        """
        IMAPControl.__init__(self)
        SMTPControl.__init__(self)
        self._soledad = soledad
        self._keymanager = keymanager
        self._mail_machine = None
        self._mail_connection = mail_connection.MailConnection()

        self._userid = None

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
