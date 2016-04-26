# -*- coding: utf-8 -*-
# imapcontroller.py
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
IMAP service controller.
"""
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.services.mail import imap

logger = get_logger()


class IMAPController(object):
    """
    IMAP Controller.
    """

    def __init__(self, soledad, keymanager):
        """
        Initialize IMAP variables.

        :param soledad: a transparent proxy that eventually will point to a
                        Soledad Instance.
        :type soledad: zope.proxy.ProxyBase
        :param keymanager: a transparent proxy that eventually will point to a
                           Keymanager Instance.
        :type keymanager: zope.proxy.ProxyBase
        """
        self._soledad = soledad
        self._keymanager = keymanager

        # XXX: this should live in its own controller
        # or, better, just be managed by a composite Mail Service in
        # leap.mail.
        self.imap_port = None
        self.imap_factory = None
        self.incoming_mail_service = None

    def start_imap_service(self, userid, offline=False):
        """
        Start IMAP service.

        :param userid: user id, in the form "user@provider"
        :type userid: str
        :param offline: whether imap should start in offline mode or not.
        :type offline: bool
        """
        logger.debug('Starting imap service')

        soledad_sessions = {userid: self._soledad}
        self.imap_port, self.imap_factory = imap.start_imap_service(
            soledad_sessions)

        def start_and_assign_incoming_service(incoming_mail):
            # this returns a deferred that will be called when the looping call
            # is stopped, we could add any shutdown/cleanup callback to that
            # deferred, but unused by the moment.
            incoming_mail.startService()
            self.incoming_mail_service = incoming_mail
            return incoming_mail

        if offline is False:
            d = imap.start_incoming_mail_service(
                self._keymanager, self._soledad,
                userid)
            d.addCallback(start_and_assign_incoming_service)
            d.addErrback(lambda f: logger.error(f.printTraceback()))

    def stop_imap_service(self):
        """
        Stop IMAP service (fetcher, factory and port).
        """
        if self.incoming_mail_service is not None:
            # Stop the loop call in the fetcher

            # XXX BUG -- the deletion of the reference should be made
            # after stopService() triggers its deferred (ie, cleanup has been
            # made)
            self.incoming_mail_service.stopService()
            self.incoming_mail_service = None

        if self.imap_port is not None:
            # Stop listening on the IMAP port
            self.imap_port.stopListening()

            # Stop the protocol
            self.imap_factory.doStop()

    def fetch_incoming_mail(self):
        """
        Fetch incoming mail.
        """
        if self.incoming_mail_service is not None:
            logger.debug('Client connected, fetching mail...')
            self.incoming_mail_service.fetch()
