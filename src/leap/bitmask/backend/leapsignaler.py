# -*- coding: utf-8 -*-
# components.py
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
Signaler for Backend/Frontend communication.
"""
import logging

from PySide import QtCore

logger = logging.getLogger(__name__)


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

    prov_get_all_services = QtCore.Signal(object)
    prov_get_supported_services = QtCore.Signal(object)
    prov_get_details = QtCore.Signal(object)
    prov_get_pinned_providers = QtCore.Signal(object)

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
    eip_stopped = QtCore.Signal(object)

    eip_dns_ok = QtCore.Signal(object)
    eip_dns_error = QtCore.Signal(object)

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
    eip_tear_fw_down = QtCore.Signal(object)

    # signals whether the needed files to start EIP exist or not
    eip_can_start = QtCore.Signal(object)
    eip_cannot_start = QtCore.Signal(object)

    # Signals for Soledad
    soledad_bootstrap_failed = QtCore.Signal(object)
    soledad_bootstrap_finished = QtCore.Signal(object)
    soledad_offline_failed = QtCore.Signal(object)
    soledad_offline_finished = QtCore.Signal(object)
    soledad_invalid_auth_token = QtCore.Signal(object)
    soledad_cancelled_bootstrap = QtCore.Signal(object)
    soledad_password_change_ok = QtCore.Signal(object)
    soledad_password_change_error = QtCore.Signal(object)

    # Keymanager signals
    keymanager_export_ok = QtCore.Signal(object)
    keymanager_export_error = QtCore.Signal(object)
    keymanager_keys_list = QtCore.Signal(object)

    keymanager_import_ioerror = QtCore.Signal(object)
    keymanager_import_datamismatch = QtCore.Signal(object)
    keymanager_import_missingkey = QtCore.Signal(object)
    keymanager_import_addressmismatch = QtCore.Signal(object)
    keymanager_import_ok = QtCore.Signal(object)

    keymanager_key_details = QtCore.Signal(object)

    # mail related signals
    imap_stopped = QtCore.Signal(object)

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
    PROV_GET_ALL_SERVICES = "prov_get_all_services"
    PROV_GET_SUPPORTED_SERVICES = "prov_get_supported_services"
    PROV_GET_DETAILS = "prov_get_details"
    PROV_GET_PINNED_PROVIDERS = "prov_get_pinned_providers"

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
    EIP_STOPPED = "eip_stopped"

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
    EIP_TEAR_FW_DOWN = "eip_tear_fw_down"

    EIP_CAN_START = "eip_can_start"
    EIP_CANNOT_START = "eip_cannot_start"

    EIP_DNS_OK = "eip_dns_ok"
    EIP_DNS_ERROR = "eip_dns_error"

    SOLEDAD_BOOTSTRAP_FAILED = "soledad_bootstrap_failed"
    SOLEDAD_BOOTSTRAP_FINISHED = "soledad_bootstrap_finished"
    SOLEDAD_OFFLINE_FAILED = "soledad_offline_failed"
    SOLEDAD_OFFLINE_FINISHED = "soledad_offline_finished"
    SOLEDAD_INVALID_AUTH_TOKEN = "soledad_invalid_auth_token"

    SOLEDAD_PASSWORD_CHANGE_OK = "soledad_password_change_ok"
    SOLEDAD_PASSWORD_CHANGE_ERROR = "soledad_password_change_error"

    SOLEDAD_CANCELLED_BOOTSTRAP = "soledad_cancelled_bootstrap"

    KEYMANAGER_EXPORT_OK = "keymanager_export_ok"
    KEYMANAGER_EXPORT_ERROR = "keymanager_export_error"
    KEYMANAGER_KEYS_LIST = "keymanager_keys_list"

    KEYMANAGER_IMPORT_IOERROR = "keymanager_import_ioerror"
    KEYMANAGER_IMPORT_DATAMISMATCH = "keymanager_import_datamismatch"
    KEYMANAGER_IMPORT_MISSINGKEY = "keymanager_import_missingkey"
    KEYMANAGER_IMPORT_ADDRESSMISMATCH = "keymanager_import_addressmismatch"
    KEYMANAGER_IMPORT_OK = "keymanager_import_ok"
    KEYMANAGER_KEY_DETAILS = "keymanager_key_details"

    IMAP_STOPPED = "imap_stopped"

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
            self.PROV_GET_ALL_SERVICES,
            self.PROV_GET_SUPPORTED_SERVICES,
            self.PROV_GET_DETAILS,
            self.PROV_GET_PINNED_PROVIDERS,

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
            self.EIP_STOPPED,

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

            self.EIP_CAN_START,
            self.EIP_CANNOT_START,

            self.EIP_DNS_OK,
            self.EIP_DNS_ERROR,

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

            self.SOLEDAD_BOOTSTRAP_FAILED,
            self.SOLEDAD_BOOTSTRAP_FINISHED,
            self.SOLEDAD_OFFLINE_FAILED,
            self.SOLEDAD_OFFLINE_FINISHED,
            self.SOLEDAD_INVALID_AUTH_TOKEN,
            self.SOLEDAD_CANCELLED_BOOTSTRAP,

            self.SOLEDAD_PASSWORD_CHANGE_OK,
            self.SOLEDAD_PASSWORD_CHANGE_ERROR,

            self.KEYMANAGER_EXPORT_OK,
            self.KEYMANAGER_EXPORT_ERROR,
            self.KEYMANAGER_KEYS_LIST,

            self.KEYMANAGER_IMPORT_IOERROR,
            self.KEYMANAGER_IMPORT_DATAMISMATCH,
            self.KEYMANAGER_IMPORT_MISSINGKEY,
            self.KEYMANAGER_IMPORT_ADDRESSMISMATCH,
            self.KEYMANAGER_IMPORT_OK,
            self.KEYMANAGER_KEY_DETAILS,

            self.IMAP_STOPPED,

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
            logger.error("Unknown key for signal %s!" % (key,))
