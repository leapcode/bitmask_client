# -*- coding: utf-8 -*-
# smtpbootstrapper.py
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
SMTP bootstrapping
"""
import os
import warnings

from requests.exceptions import HTTPError

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.certs import download_client_cert
from leap.bitmask.logs.utils import get_logger
from leap.bitmask.services import download_service_config
from leap.bitmask.services.abstractbootstrapper import AbstractBootstrapper
from leap.bitmask.services.mail.smtpconfig import SMTPConfig
from leap.bitmask.util import is_file

from leap.common import certs as leap_certs
from leap.common.check import leap_assert
from leap.common.files import check_and_fix_urw_only

logger = get_logger()


class NoSMTPHosts(Exception):
    """This is raised when there is no SMTP host to use."""


class MalformedUserId(Exception):
    """This is raised when an userid does not have the form user@provider."""


class SMTPBootstrapper(AbstractBootstrapper):
    """
    SMTP init procedure
    """

    PORT_KEY = "port"
    IP_KEY = "ip_address"

    def __init__(self):
        AbstractBootstrapper.__init__(self)

        self._provider_config = None
        self._smtp_config = None
        self._userid = None
        self._download_if_needed = False

        self._smtp_service = None
        self._smtp_port = None

    def _download_config_and_cert(self):
        """
        Downloads the SMTP config and cert for the given provider.
        """
        leap_assert(self._provider_config,
                    "We need a provider configuration!")

        logger.debug("Downloading SMTP config for %s" %
                     (self._provider_config.get_domain(),))

        download_service_config(
            self._provider_config,
            self._smtp_config,
            self._session,
            self._download_if_needed)

        hosts = self._smtp_config.get_hosts()

        if len(hosts) == 0:
            raise NoSMTPHosts()

        # TODO handle more than one host and define how to choose
        hostname = hosts.keys()[0]
        logger.debug("Using hostname %s for SMTP" % (hostname,))

        client_cert_path = self._smtp_config.get_client_cert_path(
            self._userid, self._provider_config, about_to_download=True)

        if not is_file(client_cert_path):
            # For re-download if something is wrong with the cert
            self._download_if_needed = (
                self._download_if_needed and
                not leap_certs.should_redownload(client_cert_path))

            if self._download_if_needed and os.path.isfile(client_cert_path):
                check_and_fix_urw_only(client_cert_path)
                return

            try:
                download_client_cert(self._provider_config,
                                     client_cert_path,
                                     self._session, kind="smtp")
            except HTTPError as exc:
                if exc.message.startswith('403 Client Error'):
                    logger.debug(
                        'Auth problem downloading smtp certificate... '
                        'It might be a provider problem, will try '
                        'fetching from vpn pool')
                    warnings.warn(
                        'Compatibility hack for platform 0.7 not fully '
                        'supporting smtp certificates. Will be deprecated in '
                        'bitmask 0.10')
                    download_client_cert(self._provider_config,
                                         client_cert_path,
                                         self._session, kind="vpn")
                else:
                    raise

    def _start_smtp_service(self):
        """
        Start the smtp service using the downloaded configurations.
        """
        # TODO Make the encrypted_only configurable
        # TODO pick local smtp port in a better way
        # TODO remove hard-coded port and let leap.mail set
        # the specific default.
        # TODO handle more than one host and define how to choose
        hosts = self._smtp_config.get_hosts()
        hostname = hosts.keys()[0]
        host = hosts[hostname][self.IP_KEY].encode("utf-8")
        port = hosts[hostname][self.PORT_KEY]
        client_cert_path = self._smtp_config.get_client_cert_path(
            self._userid, self._provider_config, about_to_download=True)

        from leap.mail.smtp import setup_smtp_gateway

        self._smtp_service, self._smtp_port = setup_smtp_gateway(
            port=2013,
            userid=self._userid,
            keymanager=self._keymanager,
            smtp_host=host,
            smtp_port=port,
            smtp_cert=client_cert_path,
            smtp_key=client_cert_path,
            encrypted_only=False)

    def start_smtp_service(self, keymanager, userid, download_if_needed=False):
        """
        Starts the SMTP service.

        :param keymanager: a transparent proxy that eventually will point to a
                           Keymanager Instance.
        :type keymanager: zope.proxy.ProxyBase
        :param userid: the user id, in the form "user@provider"
        :type userid: str
        :param download_if_needed: True if it should check for mtime
                                   for the file
        :type download_if_needed: bool
        """
        try:
            username, domain = userid.split('@')
        except ValueError:
            logger.critical("Malformed userid parameter!")
            raise MalformedUserId()

        self._provider_config = ProviderConfig.get_provider_config(domain)
        self._keymanager = keymanager
        self._smtp_config = SMTPConfig()
        self._userid = str(userid)
        self._download_if_needed = download_if_needed

        try:
            self._download_config_and_cert()
            logger.debug("Starting SMTP service.")
            self._start_smtp_service()
        except NoSMTPHosts:
            logger.warning("There is no SMTP host to use.")
        except Exception as e:
            # TODO: we should handle more specific exceptions in here
            logger.exception("Error while bootstrapping SMTP: %r" % (e, ))

    def stop_smtp_service(self):
        """
        Stops the smtp service (port and factory).
        """
        if self._smtp_service is not None:
            logger.debug('Stopping SMTP service.')
            self._smtp_port.stopListening()
            self._smtp_service.doStop()
        else:
            logger.debug('SMTP service not running.')
