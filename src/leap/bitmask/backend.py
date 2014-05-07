# -*- coding: utf-8 -*-
# backend.py
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
Backend for everything
"""
import logging
import os

from functools import partial
from Queue import Queue, Empty

from twisted.internet import threads, defer
from twisted.internet.task import LoopingCall
from twisted.python import log

import zope.interface

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask.crypto.srpregister import SRPRegister
from leap.bitmask.provider import get_provider_path
from leap.bitmask.provider.providerbootstrapper import ProviderBootstrapper
from leap.bitmask.services.eip import eipconfig
from leap.bitmask.services.eip import get_openvpn_management
from leap.bitmask.services.eip.eipbootstrapper import EIPBootstrapper

from leap.bitmask.services.eip import vpnlauncher, vpnprocess
from leap.bitmask.services.eip import linuxvpnlauncher, darwinvpnlauncher

# Frontend side
from PySide import QtCore

logger = logging.getLogger(__name__)


def get_provider_config(config, domain):
    """
    Return the ProviderConfig object for the given domain.
    If it is already loaded in `config`, then don't reload.

    :param config: a ProviderConfig object
    :type conig: ProviderConfig
    :param domain: the domain which config is required.
    :type domain: unicode

    :returns: True if the config was loaded successfully, False otherwise.
    :rtype: bool
    """
    # TODO: see ProviderConfig.get_provider_config
    if (not config.loaded() or config.get_domain() != domain):
        config.load(get_provider_path(domain))

    return config.loaded()


class ILEAPComponent(zope.interface.Interface):
    """
    Interface that every component for the backend should comply to
    """

    key = zope.interface.Attribute("Key id for this component")


class ILEAPService(ILEAPComponent):
    """
    Interface that every Service needs to implement
    """

    def start(self):
        """
        Start the service.
        """
        pass

    def stop(self):
        """
        Stops the service.
        """
        pass

    def terminate(self):
        """
        Terminate the service, not necessarily in a nice way.
        """
        pass

    def status(self):
        """
        Return a json object with the current status for the service.

        :rtype: object (list, str, dict)
        """
        # XXX: Use a namedtuple or a specific object instead of a json
        # object, since parsing it will be problematic otherwise.
        # It has to be something easily serializable though.
        pass

    def set_configs(self, keyval):
        """
        Set the config parameters for this Service.

        :param keyval: values to configure
        :type keyval: dict, {str: str}
        """
        pass

    def get_configs(self, keys):
        """
        Return the configuration values for the list of keys.

        :param keys: keys to retrieve
        :type keys: list of str

        :rtype: dict, {str: str}
        """
        pass


class Provider(object):
    """
    Interfaces with setup and bootstrapping operations for a provider
    """

    zope.interface.implements(ILEAPComponent)

    def __init__(self, signaler=None, bypass_checks=False):
        """
        Constructor for the Provider component

        :param signaler: Object in charge of handling communication
                         back to the frontend
        :type signaler: Signaler
        :param bypass_checks: Set to true if the app should bypass
                              first round of checks for CA
                              certificates at bootstrap
        :type bypass_checks: bool
        """
        self.key = "provider"
        self._provider_bootstrapper = ProviderBootstrapper(signaler,
                                                           bypass_checks)
        self._download_provider_defer = None
        self._provider_config = ProviderConfig()

    def setup_provider(self, provider):
        """
        Initiate the setup for a provider

        :param provider: URL for the provider
        :type provider: unicode

        :returns: the defer for the operation running in a thread.
        :rtype: twisted.internet.defer.Deferred
        """
        log.msg("Setting up provider %s..." % (provider.encode("idna"),))
        pb = self._provider_bootstrapper
        d = pb.run_provider_select_checks(provider, download_if_needed=True)
        self._download_provider_defer = d
        return d

    def cancel_setup_provider(self):
        """
        Cancel the ongoing setup provider defer (if any).
        """
        d = self._download_provider_defer
        if d is not None:
            d.cancel()

    def bootstrap(self, provider):
        """
        Second stage of bootstrapping for a provider.

        :param provider: URL for the provider
        :type provider: unicode

        :returns: the defer for the operation running in a thread.
        :rtype: twisted.internet.defer.Deferred
        """
        d = None

        config = self._provider_config
        if get_provider_config(config, provider):
            d = self._provider_bootstrapper.run_provider_setup_checks(
                self._provider_config,
                download_if_needed=True)
        else:
            if self._signaler is not None:
                self._signaler.signal(
                    self._signaler.PROV_PROBLEM_WITH_PROVIDER_KEY)
            logger.error("Could not load provider configuration.")
            self._login_widget.set_enabled(True)

        if d is None:
            d = defer.Deferred()
        return d


class Register(object):
    """
    Interfaces with setup and bootstrapping operations for a provider
    """

    zope.interface.implements(ILEAPComponent)

    def __init__(self, signaler=None):
        """
        Constructor for the Register component

        :param signaler: Object in charge of handling communication
                         back to the frontend
        :type signaler: Signaler
        """
        self.key = "register"
        self._signaler = signaler

    def register_user(self, domain, username, password):
        """
        Register a user using the domain and password given as parameters.

        :param domain: the domain we need to register the user.
        :type domain: unicode
        :param username: the user name
        :type username: unicode
        :param password: the password for the username
        :type password: unicode

        :returns: the defer for the operation running in a thread.
        :rtype: twisted.internet.defer.Deferred
        """
        config = ProviderConfig()
        if get_provider_config(config, domain):
            srpregister = SRPRegister(signaler=self._signaler,
                                      provider_config=config)
            return threads.deferToThread(
                partial(srpregister.register_user, username, password))
        else:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.SRP_REGISTRATION_FAILED)
            logger.error("Could not load provider configuration.")


class EIP(object):
    """
    Interfaces with setup and launch of EIP
    """

    zope.interface.implements(ILEAPService)

    def __init__(self, signaler=None):
        """
        Constructor for the EIP component

        :param signaler: Object in charge of handling communication
                         back to the frontend
        :type signaler: Signaler
        """
        self.key = "eip"
        self._signaler = signaler
        self._eip_bootstrapper = EIPBootstrapper(signaler)
        self._eip_setup_defer = None
        self._provider_config = ProviderConfig()

        self._vpn = vpnprocess.VPN(signaler=signaler)

    def setup_eip(self, domain):
        """
        Initiate the setup for a provider

        :param domain: URL for the provider
        :type domain: unicode

        :returns: the defer for the operation running in a thread.
        :rtype: twisted.internet.defer.Deferred
        """
        config = self._provider_config
        if get_provider_config(config, domain):
            eb = self._eip_bootstrapper
            d = eb.run_eip_setup_checks(self._provider_config,
                                        download_if_needed=True)
            self._eip_setup_defer = d
            return d
        else:
            raise Exception("No provider setup loaded")

    def cancel_setup_eip(self):
        """
        Cancel the ongoing setup eip defer (if any).
        """
        d = self._eip_setup_defer
        if d is not None:
            d.cancel()

    def _start_eip(self):
        """
        Start EIP
        """
        provider_config = self._provider_config
        eip_config = eipconfig.EIPConfig()
        domain = provider_config.get_domain()

        loaded = eipconfig.load_eipconfig_if_needed(
            provider_config, eip_config, domain)

        if not loaded:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.EIP_CONNECTION_ABORTED)
            logger.error("Tried to start EIP but cannot find any "
                         "available provider!")
            return

        host, port = get_openvpn_management()
        self._vpn.start(eipconfig=eip_config,
                        providerconfig=provider_config,
                        socket_host=host, socket_port=port)

    def start(self):
        """
        Start the service.
        """
        signaler = self._signaler

        if not self._provider_config.loaded():
            # This means that the user didn't call setup_eip first.
            self._signaler.signal(signaler.BACKEND_BAD_CALL)
            return

        try:
            self._start_eip()
        except vpnprocess.OpenVPNAlreadyRunning:
            signaler.signal(signaler.EIP_OPENVPN_ALREADY_RUNNING)
        except vpnprocess.AlienOpenVPNAlreadyRunning:
            signaler.signal(signaler.EIP_ALIEN_OPENVPN_ALREADY_RUNNING)
        except vpnlauncher.OpenVPNNotFoundException:
            signaler.signal(signaler.EIP_OPENVPN_NOT_FOUND_ERROR)
        except vpnlauncher.VPNLauncherException:
            # TODO: this seems to be used for 'gateway not found' only.
            #       see vpnlauncher.py
            signaler.signal(signaler.EIP_VPN_LAUNCHER_EXCEPTION)
        except linuxvpnlauncher.EIPNoPolkitAuthAgentAvailable:
            signaler.signal(signaler.EIP_NO_POLKIT_AGENT_ERROR)
        except linuxvpnlauncher.EIPNoPkexecAvailable:
            signaler.signal(signaler.EIP_NO_PKEXEC_ERROR)
        except darwinvpnlauncher.EIPNoTunKextLoaded:
            signaler.signal(signaler.EIP_NO_TUN_KEXT_ERROR)
        except Exception as e:
            logger.error("Unexpected problem: {0!r}".format(e))
        else:
            # TODO: are we connected here?
            signaler.signal(signaler.EIP_CONNECTED)

    def stop(self, shutdown=False):
        """
        Stop the service.
        """
        self._vpn.terminate(shutdown)

    def terminate(self):
        """
        Terminate the service, not necessarily in a nice way.
        """
        self._vpn.killit()

    def status(self):
        """
        Return a json object with the current status for the service.

        :rtype: object (list, str, dict)
        """
        # XXX: Use a namedtuple or a specific object instead of a json
        # object, since parsing it will be problematic otherwise.
        # It has to be something easily serializable though.
        pass

    def _provider_is_initialized(self, domain):
        """
        Return whether the given domain is initialized or not.

        :param domain: the domain to check
        :type domain: str

        :returns: True if is initialized, False otherwise.
        :rtype: bool
        """
        eipconfig_path = eipconfig.get_eipconfig_path(domain, relative=False)
        if os.path.isfile(eipconfig_path):
            return True
        else:
            return False

    def get_initialized_providers(self, domains):
        """
        Signal a list of the given domains and if they are initialized or not.

        :param domains: the list of domains to check.
        :type domain: list of str

        Signals:
            eip_get_initialized_providers -> list of tuple(unicode, bool)
        """
        filtered_domains = []
        for domain in domains:
            is_initialized = self._provider_is_initialized(domain)
            filtered_domains.append((domain, is_initialized))

        if self._signaler is not None:
            self._signaler.signal(self._signaler.EIP_GET_INITIALIZED_PROVIDERS,
                                  filtered_domains)

    def get_gateways_list(self, domain):
        """
        Signal a list of gateways for the given provider.

        :param domain: the domain to get the gateways.
        :type domain: str

        Signals:
            eip_get_gateways_list -> list of unicode
            eip_get_gateways_list_error
            eip_uninitialized_provider
        """
        if not self._provider_is_initialized(domain):
            if self._signaler is not None:
                self._signaler.signal(
                    self._signaler.EIP_UNINITIALIZED_PROVIDER)
            return

        eip_config = eipconfig.EIPConfig()
        provider_config = ProviderConfig.get_provider_config(domain)

        api_version = provider_config.get_api_version()
        eip_config.set_api_version(api_version)
        eip_loaded = eip_config.load(eipconfig.get_eipconfig_path(domain))

        # check for other problems
        if not eip_loaded or provider_config is None:
            if self._signaler is not None:
                self._signaler.signal(
                    self._signaler.EIP_GET_GATEWAYS_LIST_ERROR)
            return

        gateways = eipconfig.VPNGatewaySelector(eip_config).get_gateways_list()

        if self._signaler is not None:
            self._signaler.signal(
                self._signaler.EIP_GET_GATEWAYS_LIST, gateways)


class Authenticate(object):
    """
    Interfaces with setup and bootstrapping operations for a provider
    """

    zope.interface.implements(ILEAPComponent)

    def __init__(self, signaler=None):
        """
        Constructor for the Authenticate component

        :param signaler: Object in charge of handling communication
                         back to the frontend
        :type signaler: Signaler
        """
        self.key = "authenticate"
        self._signaler = signaler
        self._srp_auth = SRPAuth(ProviderConfig(), self._signaler)

    def login(self, domain, username, password):
        """
        Execute the whole authentication process for a user

        :param domain: the domain where we need to authenticate.
        :type domain: unicode
        :param username: username for this session
        :type username: str
        :param password: password for this user
        :type password: str

        :returns: the defer for the operation running in a thread.
        :rtype: twisted.internet.defer.Deferred
        """
        config = ProviderConfig()
        if get_provider_config(config, domain):
            self._srp_auth = SRPAuth(config, self._signaler)
            self._login_defer = self._srp_auth.authenticate(username, password)
            return self._login_defer
        else:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.SRP_AUTH_ERROR)
            logger.error("Could not load provider configuration.")

    def cancel_login(self):
        """
        Cancel the ongoing login defer (if any).
        """
        d = self._login_defer
        if d is not None:
            d.cancel()

    def change_password(self, current_password, new_password):
        """
        Change the user's password.

        :param current_password: the current password of the user.
        :type current_password: str
        :param new_password: the new password for the user.
        :type new_password: str

        :returns: a defer to interact with.
        :rtype: twisted.internet.defer.Deferred
        """
        if not self._is_logged_in():
            if self._signaler is not None:
                self._signaler.signal(self._signaler.SRP_NOT_LOGGED_IN_ERROR)
            return

        return self._srp_auth.change_password(current_password, new_password)

    def logout(self):
        """
        Log out the current session.
        Expects a session_id to exists, might raise AssertionError
        """
        if not self._is_logged_in():
            if self._signaler is not None:
                self._signaler.signal(self._signaler.SRP_NOT_LOGGED_IN_ERROR)
            return

        self._srp_auth.logout()

    def _is_logged_in(self):
        """
        Return whether the user is logged in or not.

        :rtype: bool
        """
        return (self._srp_auth is not None and
                self._srp_auth.is_authenticated())

    def get_logged_in_status(self):
        """
        Signal if the user is currently logged in or not.
        """
        if self._signaler is None:
            return

        signal = None
        if self._is_logged_in():
            signal = self._signaler.SRP_STATUS_LOGGED_IN
        else:
            signal = self._signaler.SRP_STATUS_NOT_LOGGED_IN

        self._signaler.signal(signal)


class Signaler(QtCore.QObject):
    """
    Signaler object, handles converting string commands to Qt signals.

    This is intended for the separation in frontend/backend, this will
    live in the frontend.
    """

    ####################
    # These will only exist in the frontend
    # Signals for the ProviderBootstrapper
    prov_name_resolution = QtCore.Signal(object)
    prov_https_connection = QtCore.Signal(object)
    prov_download_provider_info = QtCore.Signal(object)

    prov_download_ca_cert = QtCore.Signal(object)
    prov_check_ca_fingerprint = QtCore.Signal(object)
    prov_check_api_certificate = QtCore.Signal(object)

    prov_problem_with_provider = QtCore.Signal(object)

    prov_unsupported_client = QtCore.Signal(object)
    prov_unsupported_api = QtCore.Signal(object)

    prov_cancelled_setup = QtCore.Signal(object)

    # Signals for SRPRegister
    srp_registration_finished = QtCore.Signal(object)
    srp_registration_failed = QtCore.Signal(object)
    srp_registration_taken = QtCore.Signal(object)

    # Signals for EIP bootstrapping
    eip_config_ready = QtCore.Signal(object)
    eip_client_certificate_ready = QtCore.Signal(object)

    eip_cancelled_setup = QtCore.Signal(object)

    # Signals for SRPAuth
    srp_auth_ok = QtCore.Signal(object)
    srp_auth_error = QtCore.Signal(object)
    srp_auth_server_error = QtCore.Signal(object)
    srp_auth_connection_error = QtCore.Signal(object)
    srp_auth_bad_user_or_password = QtCore.Signal(object)
    srp_logout_ok = QtCore.Signal(object)
    srp_logout_error = QtCore.Signal(object)
    srp_password_change_ok = QtCore.Signal(object)
    srp_password_change_error = QtCore.Signal(object)
    srp_password_change_badpw = QtCore.Signal(object)
    srp_not_logged_in_error = QtCore.Signal(object)
    srp_status_logged_in = QtCore.Signal(object)
    srp_status_not_logged_in = QtCore.Signal(object)

    # Signals for EIP
    eip_connected = QtCore.Signal(object)
    eip_disconnected = QtCore.Signal(object)
    eip_connection_died = QtCore.Signal(object)
    eip_connection_aborted = QtCore.Signal(object)

    # EIP problems
    eip_no_polkit_agent_error = QtCore.Signal(object)
    eip_no_tun_kext_error = QtCore.Signal(object)
    eip_no_pkexec_error = QtCore.Signal(object)
    eip_openvpn_not_found_error = QtCore.Signal(object)
    eip_openvpn_already_running = QtCore.Signal(object)
    eip_alien_openvpn_already_running = QtCore.Signal(object)
    eip_vpn_launcher_exception = QtCore.Signal(object)

    eip_get_gateways_list = QtCore.Signal(object)
    eip_get_gateways_list_error = QtCore.Signal(object)
    eip_uninitialized_provider = QtCore.Signal(object)
    eip_get_initialized_providers = QtCore.Signal(object)

    # signals from parsing openvpn output
    eip_network_unreachable = QtCore.Signal(object)
    eip_process_restart_tls = QtCore.Signal(object)
    eip_process_restart_ping = QtCore.Signal(object)

    # signals from vpnprocess.py
    eip_state_changed = QtCore.Signal(dict)
    eip_status_changed = QtCore.Signal(dict)
    eip_process_finished = QtCore.Signal(int)

    # This signal is used to warn the backend user that is doing something
    # wrong
    backend_bad_call = QtCore.Signal(object)

    ####################
    # These will exist both in the backend AND the front end.
    # The frontend might choose to not "interpret" all the signals
    # from the backend, but the backend needs to have all the signals
    # it's going to emit defined here
    PROV_NAME_RESOLUTION_KEY = "prov_name_resolution"
    PROV_HTTPS_CONNECTION_KEY = "prov_https_connection"
    PROV_DOWNLOAD_PROVIDER_INFO_KEY = "prov_download_provider_info"
    PROV_DOWNLOAD_CA_CERT_KEY = "prov_download_ca_cert"
    PROV_CHECK_CA_FINGERPRINT_KEY = "prov_check_ca_fingerprint"
    PROV_CHECK_API_CERTIFICATE_KEY = "prov_check_api_certificate"
    PROV_PROBLEM_WITH_PROVIDER_KEY = "prov_problem_with_provider"
    PROV_UNSUPPORTED_CLIENT = "prov_unsupported_client"
    PROV_UNSUPPORTED_API = "prov_unsupported_api"
    PROV_CANCELLED_SETUP = "prov_cancelled_setup"

    SRP_REGISTRATION_FINISHED = "srp_registration_finished"
    SRP_REGISTRATION_FAILED = "srp_registration_failed"
    SRP_REGISTRATION_TAKEN = "srp_registration_taken"
    SRP_AUTH_OK = "srp_auth_ok"
    SRP_AUTH_ERROR = "srp_auth_error"
    SRP_AUTH_SERVER_ERROR = "srp_auth_server_error"
    SRP_AUTH_CONNECTION_ERROR = "srp_auth_connection_error"
    SRP_AUTH_BAD_USER_OR_PASSWORD = "srp_auth_bad_user_or_password"
    SRP_LOGOUT_OK = "srp_logout_ok"
    SRP_LOGOUT_ERROR = "srp_logout_error"
    SRP_PASSWORD_CHANGE_OK = "srp_password_change_ok"
    SRP_PASSWORD_CHANGE_ERROR = "srp_password_change_error"
    SRP_PASSWORD_CHANGE_BADPW = "srp_password_change_badpw"
    SRP_NOT_LOGGED_IN_ERROR = "srp_not_logged_in_error"
    SRP_STATUS_LOGGED_IN = "srp_status_logged_in"
    SRP_STATUS_NOT_LOGGED_IN = "srp_status_not_logged_in"

    EIP_CONFIG_READY = "eip_config_ready"
    EIP_CLIENT_CERTIFICATE_READY = "eip_client_certificate_ready"
    EIP_CANCELLED_SETUP = "eip_cancelled_setup"

    EIP_CONNECTED = "eip_connected"
    EIP_DISCONNECTED = "eip_disconnected"
    EIP_CONNECTION_DIED = "eip_connection_died"
    EIP_CONNECTION_ABORTED = "eip_connection_aborted"
    EIP_NO_POLKIT_AGENT_ERROR = "eip_no_polkit_agent_error"
    EIP_NO_TUN_KEXT_ERROR = "eip_no_tun_kext_error"
    EIP_NO_PKEXEC_ERROR = "eip_no_pkexec_error"
    EIP_OPENVPN_NOT_FOUND_ERROR = "eip_openvpn_not_found_error"
    EIP_OPENVPN_ALREADY_RUNNING = "eip_openvpn_already_running"
    EIP_ALIEN_OPENVPN_ALREADY_RUNNING = "eip_alien_openvpn_already_running"
    EIP_VPN_LAUNCHER_EXCEPTION = "eip_vpn_launcher_exception"

    EIP_GET_GATEWAYS_LIST = "eip_get_gateways_list"
    EIP_GET_GATEWAYS_LIST_ERROR = "eip_get_gateways_list_error"
    EIP_UNINITIALIZED_PROVIDER = "eip_uninitialized_provider"
    EIP_GET_INITIALIZED_PROVIDERS = "eip_get_initialized_providers"

    EIP_NETWORK_UNREACHABLE = "eip_network_unreachable"
    EIP_PROCESS_RESTART_TLS = "eip_process_restart_tls"
    EIP_PROCESS_RESTART_PING = "eip_process_restart_ping"

    EIP_STATE_CHANGED = "eip_state_changed"
    EIP_STATUS_CHANGED = "eip_status_changed"
    EIP_PROCESS_FINISHED = "eip_process_finished"

    BACKEND_BAD_CALL = "backend_bad_call"

    def __init__(self):
        """
        Constructor for the Signaler
        """
        QtCore.QObject.__init__(self)
        self._signals = {}

        signals = [
            self.PROV_NAME_RESOLUTION_KEY,
            self.PROV_HTTPS_CONNECTION_KEY,
            self.PROV_DOWNLOAD_PROVIDER_INFO_KEY,
            self.PROV_DOWNLOAD_CA_CERT_KEY,
            self.PROV_CHECK_CA_FINGERPRINT_KEY,
            self.PROV_CHECK_API_CERTIFICATE_KEY,
            self.PROV_PROBLEM_WITH_PROVIDER_KEY,
            self.PROV_UNSUPPORTED_CLIENT,
            self.PROV_UNSUPPORTED_API,
            self.PROV_CANCELLED_SETUP,

            self.SRP_REGISTRATION_FINISHED,
            self.SRP_REGISTRATION_FAILED,
            self.SRP_REGISTRATION_TAKEN,

            self.EIP_CONFIG_READY,
            self.EIP_CLIENT_CERTIFICATE_READY,
            self.EIP_CANCELLED_SETUP,

            self.EIP_CONNECTED,
            self.EIP_DISCONNECTED,
            self.EIP_CONNECTION_DIED,
            self.EIP_CONNECTION_ABORTED,
            self.EIP_NO_POLKIT_AGENT_ERROR,
            self.EIP_NO_TUN_KEXT_ERROR,
            self.EIP_NO_PKEXEC_ERROR,
            self.EIP_OPENVPN_NOT_FOUND_ERROR,
            self.EIP_OPENVPN_ALREADY_RUNNING,
            self.EIP_ALIEN_OPENVPN_ALREADY_RUNNING,
            self.EIP_VPN_LAUNCHER_EXCEPTION,

            self.EIP_GET_GATEWAYS_LIST,
            self.EIP_GET_GATEWAYS_LIST_ERROR,
            self.EIP_UNINITIALIZED_PROVIDER,
            self.EIP_GET_INITIALIZED_PROVIDERS,

            self.EIP_NETWORK_UNREACHABLE,
            self.EIP_PROCESS_RESTART_TLS,
            self.EIP_PROCESS_RESTART_PING,

            self.EIP_STATE_CHANGED,
            self.EIP_STATUS_CHANGED,
            self.EIP_PROCESS_FINISHED,

            self.SRP_AUTH_OK,
            self.SRP_AUTH_ERROR,
            self.SRP_AUTH_SERVER_ERROR,
            self.SRP_AUTH_CONNECTION_ERROR,
            self.SRP_AUTH_BAD_USER_OR_PASSWORD,
            self.SRP_LOGOUT_OK,
            self.SRP_LOGOUT_ERROR,
            self.SRP_PASSWORD_CHANGE_OK,
            self.SRP_PASSWORD_CHANGE_ERROR,
            self.SRP_PASSWORD_CHANGE_BADPW,
            self.SRP_NOT_LOGGED_IN_ERROR,
            self.SRP_STATUS_LOGGED_IN,
            self.SRP_STATUS_NOT_LOGGED_IN,

            self.BACKEND_BAD_CALL,
        ]

        for sig in signals:
            self._signals[sig] = getattr(self, sig)

    def signal(self, key, data=None):
        """
        Emits a Qt signal based on the key provided, with the data if provided.

        :param key: string identifying the signal to emit
        :type key: str
        :param data: object to send with the data
        :type data: object

        NOTE: The data object will be a serialized str in the backend,
        and an unserialized object in the frontend, but for now we
        just care about objects.
        """
        # Right now it emits Qt signals. The backend version of this
        # will do zmq.send_multipart, and the frontend version will be
        # similar to this

        # for some reason emitting 'None' gives a segmentation fault.
        if data is None:
            data = ''

        try:
            self._signals[key].emit(data)
        except KeyError:
            log.err("Unknown key for signal %s!" % (key,))


class Backend(object):
    """
    Backend for everything, the UI should only use this class.
    """

    PASSED_KEY = "passed"
    ERROR_KEY = "error"

    def __init__(self, bypass_checks=False):
        """
        Constructor for the backend.
        """
        # Components map for the commands received
        self._components = {}

        # Ongoing defers that will be cancelled at stop time
        self._ongoing_defers = []

        # Signaler object to translate commands into Qt signals
        self._signaler = Signaler()

        # Component registration
        self._register(Provider(self._signaler, bypass_checks))
        self._register(Register(self._signaler))
        self._register(Authenticate(self._signaler))
        self._register(EIP(self._signaler))

        # We have a looping call on a thread executing all the
        # commands in queue. Right now this queue is an actual Queue
        # object, but it'll become the zmq recv_multipart queue
        self._lc = LoopingCall(threads.deferToThread, self._worker)

        # Temporal call_queue for worker, will be replaced with
        # recv_multipart os something equivalent in the loopingcall
        self._call_queue = Queue()

    @property
    def signaler(self):
        """
        Public signaler access to let the UI connect to its signals.
        """
        return self._signaler

    def start(self):
        """
        Starts the looping call
        """
        log.msg("Starting worker...")
        self._lc.start(0.01)

    def stop(self):
        """
        Stops the looping call and tries to cancel all the defers.
        """
        log.msg("Stopping worker...")
        if self._lc.running:
            self._lc.stop()
        while len(self._ongoing_defers) > 0:
            d = self._ongoing_defers.pop()
            d.cancel()

    def _register(self, component):
        """
        Registers a component in this backend

        :param component: Component to register
        :type component: any object that implements ILEAPComponent
        """
        # TODO: assert that the component implements the interfaces
        # expected
        try:
            self._components[component.key] = component
        except Exception:
            log.msg("There was a problem registering %s" % (component,))
            log.err()

    def _signal_back(self, _, signal):
        """
        Helper method to signal back (callback like behavior) to the
        UI that an operation finished.

        :param signal: signal name
        :type signal: str
        """
        self._signaler.signal(signal)

    def _worker(self):
        """
        Worker method, called from a different thread and as a part of
        a looping call
        """
        try:
            # this'll become recv_multipart
            cmd = self._call_queue.get(block=False)

            # cmd is: component, method, signalback, *args
            func = getattr(self._components[cmd[0]], cmd[1])
            d = func(*cmd[3:])
            if d is not None:  # d may be None if a defer chain is cancelled.
                # A call might not have a callback signal, but if it does,
                # we add it to the chain
                if cmd[2] is not None:
                    d.addCallbacks(self._signal_back, log.err, cmd[2])
                d.addCallbacks(self._done_action, log.err,
                               callbackKeywords={"d": d})
                d.addErrback(log.err)
                self._ongoing_defers.append(d)
        except Empty:
            # If it's just empty we don't have anything to do.
            pass
        except defer.CancelledError:
            logger.debug("defer cancelled somewhere (CancelledError).")
        except Exception:
            # But we log the rest
            log.err()

    def _done_action(self, _, d):
        """
        Remover of the defer once it's done

        :param d: defer to remove
        :type d: twisted.internet.defer.Deferred
        """
        if d in self._ongoing_defers:
            self._ongoing_defers.remove(d)

    # XXX: Temporal interface until we migrate to zmq
    # We simulate the calls to zmq.send_multipart. Once we separate
    # this in two processes, the methods bellow can be changed to
    # send_multipart and this backend class will be really simple.

    def setup_provider(self, provider):
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
        self._call_queue.put(("provider", "setup_provider", None, provider))

    def cancel_setup_provider(self):
        """
        Cancel the ongoing setup provider (if any).
        """
        self._call_queue.put(("provider", "cancel_setup_provider", None))

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
        self._call_queue.put(("provider", "bootstrap", None, provider))

    def register_user(self, provider, username, password):
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
        self._call_queue.put(("register", "register_user", None, provider,
                              username, password))

    def setup_eip(self, provider):
        """
        Initiate the setup for a provider

        :param domain: URL for the provider
        :type domain: unicode

        Signals:
            eip_config_ready             -> {PASSED_KEY: bool, ERROR_KEY: str}
            eip_client_certificate_ready -> {PASSED_KEY: bool, ERROR_KEY: str}
            eip_cancelled_setup
        """
        self._call_queue.put(("eip", "setup_eip", None, provider))

    def cancel_setup_eip(self):
        """
        Cancel the ongoing setup EIP (if any).
        """
        self._call_queue.put(("eip", "cancel_setup_eip", None))

    def start_eip(self):
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
        """
        self._call_queue.put(("eip", "start", None))

    def stop_eip(self, shutdown=False):
        """
        Stop the EIP service.

        :param shutdown:
        :type shutdown: bool
        """
        self._call_queue.put(("eip", "stop", None, shutdown))

    def terminate_eip(self):
        """
        Terminate the EIP service, not necessarily in a nice way.
        """
        self._call_queue.put(("eip", "terminate", None))

    def eip_get_gateways_list(self, domain):
        """
        Signal a list of gateways for the given provider.

        :param domain: the domain to get the gateways.
        :type domain: str

        # TODO discuss how to document the expected result object received of
        # the signal
        :signal type: list of str

        Signals:
            eip_get_gateways_list -> list of unicode
            eip_get_gateways_list_error
            eip_uninitialized_provider
        """
        self._call_queue.put(("eip", "get_gateways_list", None, domain))

    def eip_get_initialized_providers(self, domains):
        """
        Signal a list of the given domains and if they are initialized or not.

        :param domains: the list of domains to check.
        :type domain: list of str

        Signals:
            eip_get_initialized_providers -> list of tuple(unicode, bool)

        """
        self._call_queue.put(("eip", "get_initialized_providers",
                              None, domains))

    def login(self, provider, username, password):
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
        self._call_queue.put(("authenticate", "login", None, provider,
                              username, password))

    def logout(self):
        """
        Log out the current session.

        Signals:
            srp_logout_ok
            srp_logout_error
            srp_not_logged_in_error
        """
        self._call_queue.put(("authenticate", "logout", None))

    def cancel_login(self):
        """
        Cancel the ongoing login (if any).
        """
        self._call_queue.put(("authenticate", "cancel_login", None))

    def change_password(self, current_password, new_password):
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
        self._call_queue.put(("authenticate", "change_password", None,
                              current_password, new_password))

    def get_logged_in_status(self):
        """
        Signal if the user is currently logged in or not.

        Signals:
            srp_status_logged_in
            srp_status_not_logged_in
        """
        self._call_queue.put(("authenticate", "get_logged_in_status", None))

    ###########################################################################
    # XXX HACK: this section is meant to be a place to hold methods and
    # variables needed in the meantime while we migrate all to the backend.

    def get_provider_config(self):
        provider_config = self._components["provider"]._provider_config
        return provider_config
