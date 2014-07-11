# -*- coding: utf-8 -*-
# leapbackend.py
# Copyright (C) 2013, 2014 LEAP
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
Backend for everything
"""
import logging

import zope.interface
import zope.proxy

from leap.bitmask.backend import components
from leap.bitmask.backend.backend import Backend
from leap.bitmask.backend.settings import Settings

logger = logging.getLogger(__name__)

ERROR_KEY = "error"
PASSED_KEY = "passed"


class LeapBackend(Backend):
    """
    Backend server subclass, used to implement the API methods.
    """
    def __init__(self, bypass_checks=False):
        """
        Constructor for the backend.
        """
        Backend.__init__(self)

        self._settings = Settings()

        # Objects needed by several components, so we make a proxy and pass
        # them around
        self._soledad_proxy = zope.proxy.ProxyBase(None)
        self._keymanager_proxy = zope.proxy.ProxyBase(None)

        # Component instances creation
        self._provider = components.Provider(self._signaler, bypass_checks)
        self._register = components.Register(self._signaler)
        self._authenticate = components.Authenticate(self._signaler)
        self._eip = components.EIP(self._signaler)
        self._soledad = components.Soledad(self._soledad_proxy,
                                           self._keymanager_proxy,
                                           self._signaler)
        self._keymanager = components.Keymanager(self._keymanager_proxy,
                                                 self._signaler)
        self._mail = components.Mail(self._soledad_proxy,
                                     self._keymanager_proxy,
                                     self._signaler)

    def _check_type(self, obj, expected_type):
        """
        Check the type of a parameter.

        :param obj: object to check its type.
        :type obj: any type
        :param expected_type: the expected type of the object.
        :type expected_type: type
        """
        if not isinstance(obj, expected_type):
            raise TypeError("The parameter type is incorrect.")

    def provider_setup(self, provider):
        """
        Initiate the setup for a provider.

        :param provider: URL for the provider
        :type provider: unicode

        Signals:
            prov_unsupported_client
            prov_unsupported_api
            prov_name_resolution        -> { PASSED_KEY: bool, ERROR_KEY: str }
            prov_https_connection       -> { PASSED_KEY: bool, ERROR_KEY: str }
            prov_download_provider_info -> { PASSED_KEY: bool, ERROR_KEY: str }
        """
        self._provider.setup_provider(provider)

    def provider_cancel_setup(self):
        """
        Cancel the ongoing setup provider (if any).
        """
        self._provider.cancel_setup_provider()

    def provider_bootstrap(self, provider):
        """
        Second stage of bootstrapping for a provider.

        :param provider: URL for the provider
        :type provider: unicode

        Signals:
            prov_problem_with_provider
            prov_download_ca_cert      -> {PASSED_KEY: bool, ERROR_KEY: str}
            prov_check_ca_fingerprint  -> {PASSED_KEY: bool, ERROR_KEY: str}
            prov_check_api_certificate -> {PASSED_KEY: bool, ERROR_KEY: str}
        """
        self._provider.bootstrap(provider)

    def provider_get_supported_services(self, domain):
        """
        Signal a list of supported services provided by the given provider.

        :param domain: the provider to get the services from.
        :type domain: str

        Signals:
            prov_get_supported_services -> list of unicode
        """
        self._provider.get_supported_services(domain)

    def provider_get_all_services(self, providers):
        """
        Signal a list of services provided by all the configured providers.

        :param providers: the list of providers to get the services.
        :type providers: list

        Signals:
            prov_get_all_services -> list of unicode
        """
        self._provider.get_all_services(providers)

    def provider_get_details(self, domain, lang):
        """
        Signal a dict with the current ProviderConfig settings.

        :param domain: the domain name of the provider.
        :type domain: str
        :param lang: the language to use for localized strings.
        :type lang: str

        Signals:
            prov_get_details -> dict
        """
        self._provider.get_details(domain, lang)

    def provider_get_pinned_providers(self):
        """
        Signal the pinned providers.

        Signals:
            prov_get_pinned_providers -> list of provider domains
        """
        self._provider.get_pinned_providers()

    def user_register(self, provider, username, password):
        """
        Register a user using the domain and password given as parameters.

        :param domain: the domain we need to register the user.
        :type domain: unicode
        :param username: the user name
        :type username: unicode
        :param password: the password for the username
        :type password: unicode

        Signals:
            srp_registration_finished
            srp_registration_taken
            srp_registration_failed
        """
        self._register.register_user(provider, username, password)

    def eip_setup(self, provider, skip_network=False):
        """
        Initiate the setup for a provider

        :param provider: URL for the provider
        :type provider: unicode
        :param skip_network: Whether checks that involve network should be done
                             or not
        :type skip_network: bool

        Signals:
            eip_config_ready             -> {PASSED_KEY: bool, ERROR_KEY: str}
            eip_client_certificate_ready -> {PASSED_KEY: bool, ERROR_KEY: str}
            eip_cancelled_setup
        """
        self._eip.setup_eip(provider, skip_network)

    def eip_cancel_setup(self):
        """
        Cancel the ongoing setup EIP (if any).
        """
        self._eip.cancel_setup_eip()

    def eip_start(self, restart=False):
        """
        Start the EIP service.

        Signals:
            backend_bad_call
            eip_alien_openvpn_already_running
            eip_connected
            eip_connection_aborted
            eip_network_unreachable
            eip_no_pkexec_error
            eip_no_polkit_agent_error
            eip_no_tun_kext_error
            eip_openvpn_already_running
            eip_openvpn_not_found_error
            eip_process_finished
            eip_process_restart_ping
            eip_process_restart_tls
            eip_state_changed -> str
            eip_status_changed -> tuple of str (download, upload)
            eip_vpn_launcher_exception

        :param restart: whether is is a restart.
        :type restart: bool
        """
        self._eip.start(restart)

    def eip_stop(self, shutdown=False, restart=False, failed=False):
        """
        Stop the EIP service.

        :param shutdown: whether this is the final shutdown.
        :type shutdown: bool

        :param restart: whether this is part of a restart.
        :type restart: bool
        """
        self._eip.stop(shutdown, restart)

    def eip_terminate(self):
        """
        Terminate the EIP service, not necessarily in a nice way.
        """
        self._eip.terminate()

    def eip_get_gateways_list(self, domain):
        """
        Signal a list of gateways for the given provider.

        :param domain: the domain to get the gateways.
        :type domain: str

        Signals:
            eip_get_gateways_list -> list of unicode
            eip_get_gateways_list_error
            eip_uninitialized_provider
        """
        self._eip.get_gateways_list(domain)

    def eip_get_gateway_country_code(self, domain):
        """
        Signal a list of gateways for the given provider.

        :param domain: the domain to get the gateways.
        :type domain: str

        Signals:
            eip_get_gateways_list -> str
            eip_no_gateway
        """
        self._eip.get_gateway_country_code(domain)

    def eip_get_initialized_providers(self, domains):
        """
        Signal a list of the given domains and if they are initialized or not.

        :param domains: the list of domains to check.
        :type domain: list of str

        Signals:
            eip_get_initialized_providers -> list of tuple(unicode, bool)

        """
        self._eip.get_initialized_providers(domains)

    def eip_can_start(self, domain):
        """
        Signal whether it has everything that is needed to run EIP or not

        :param domain: the domain for the provider to check
        :type domain: str

        Signals:
            eip_can_start
            eip_cannot_start
        """
        self._eip.can_start(domain)

    def eip_check_dns(self, domain):
        """
        Check if we can resolve the given domain name.

        :param domain: the domain for the provider to check
        :type domain: str

        Signals:
            eip_dns_ok
            eip_dns_error
        """
        self._eip.check_dns(domain)

    def tear_fw_down(self):
        """
        Signal the need to tear the fw down.
        """
        self._eip.tear_fw_down()

    def user_login(self, provider, username, password):
        """
        Execute the whole authentication process for a user

        :param domain: the domain where we need to authenticate.
        :type domain: unicode
        :param username: username for this session
        :type username: str
        :param password: password for this user
        :type password: str

        Signals:
            srp_auth_error
            srp_auth_ok
            srp_auth_bad_user_or_password
            srp_auth_server_error
            srp_auth_connection_error
            srp_auth_error
        """
        self._authenticate.login(provider, username, password)

    def user_logout(self):
        """
        Log out the current session.

        Signals:
            srp_logout_ok
            srp_logout_error
            srp_not_logged_in_error
        """
        self._authenticate.logout()

    def user_cancel_login(self):
        """
        Cancel the ongoing login (if any).
        """
        self._authenticate.cancel_login()

    def user_change_password(self, current_password, new_password):
        """
        Change the user's password.

        :param current_password: the current password of the user.
        :type current_password: str
        :param new_password: the new password for the user.
        :type new_password: str

        Signals:
            srp_not_logged_in_error
            srp_password_change_ok
            srp_password_change_badpw
            srp_password_change_error
        """
        self._authenticate.change_password(current_password, new_password)

    def soledad_change_password(self, new_password):
        """
        Change the database's password.

        :param new_password: the new password for the user.
        :type new_password: unicode

        Signals:
            srp_not_logged_in_error
            srp_password_change_ok
            srp_password_change_badpw
            srp_password_change_error
        """
        self._soledad.change_password(new_password)

    def user_get_logged_in_status(self):
        """
        Signal if the user is currently logged in or not.

        Signals:
            srp_status_logged_in
            srp_status_not_logged_in
        """
        self._authenticate.get_logged_in_status()

    def soledad_bootstrap(self, username, domain, password):
        """
        Bootstrap the soledad database.

        :param username: the user name
        :type username: unicode
        :param domain: the domain that we are using.
        :type domain: unicode
        :param password: the password for the username
        :type password: unicode

        Signals:
            soledad_bootstrap_finished
            soledad_bootstrap_failed
            soledad_invalid_auth_token
        """
        self._check_type(username, unicode)
        self._check_type(domain, unicode)
        self._check_type(password, unicode)
        self._soledad.bootstrap(username, domain, password)

    def soledad_load_offline(self, username, password, uuid):
        """
        Load the soledad database in offline mode.

        :param username: full user id (user@provider)
        :type username: str or unicode
        :param password: the soledad passphrase
        :type password: unicode
        :param uuid: the user uuid
        :type uuid: str or unicode

        Signals:
        """
        self._soledad.load_offline(username, password, uuid)

    def soledad_cancel_bootstrap(self):
        """
        Cancel the ongoing soledad bootstrapping process (if any).
        """
        self._soledad.cancel_bootstrap()

    def soledad_close(self):
        """
        Close soledad database.
        """
        self._soledad.close()

    def keymanager_list_keys(self):
        """
        Signal a list of public keys locally stored.

        Signals:
            keymanager_keys_list -> list
        """
        self._keymanager.list_keys()

    def keymanager_export_keys(self, username, filename):
        """
        Export the given username's keys to a file.

        :param username: the username whos keys we need to export.
        :type username: str
        :param filename: the name of the file where we want to save the keys.
        :type filename: str

        Signals:
            keymanager_export_ok
            keymanager_export_error
        """
        self._keymanager.export_keys(username, filename)

    def keymanager_get_key_details(self, username):
        """
        Signal the given username's key details.

        :param username: the username whos keys we need to get details.
        :type username: str

        Signals:
            keymanager_key_details
        """
        self._keymanager.get_key_details(username)

    def smtp_start_service(self, full_user_id, download_if_needed=False):
        """
        Start the SMTP service.

        :param full_user_id: user id, in the form "user@provider"
        :type full_user_id: str
        :param download_if_needed: True if it should check for mtime
                                   for the file
        :type download_if_needed: bool
        """
        self._mail.start_smtp_service(full_user_id, download_if_needed)

    def imap_start_service(self, full_user_id, offline=False):
        """
        Start the IMAP service.

        :param full_user_id: user id, in the form "user@provider"
        :type full_user_id: str
        :param offline: whether imap should start in offline mode or not.
        :type offline: bool
        """
        self._mail.start_imap_service(full_user_id, offline)

    def smtp_stop_service(self):
        """
        Stop the SMTP service.
        """
        self._mail.stop_smtp_service()

    def imap_stop_service(self):
        """
        Stop imap service.

        Signals:
            imap_stopped
        """
        self._mail.stop_imap_service()

    def settings_set_selected_gateway(self, provider, gateway):
        """
        Set the selected gateway for a given provider.

        :param provider: provider domain
        :type provider: str
        :param gateway: gateway to use as default
        :type gateway: str
        """
        self._settings.set_selected_gateway(provider, gateway)
