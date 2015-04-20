# -*- coding: utf-8 -*-
# leapsignaler.py
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
Signaling server, used to define the API signals.
"""
from PySide import QtCore

from leap.bitmask.backend.signaler_qt import SignalerQt


class LeapSignaler(SignalerQt):
    """
    Signaling server subclass, used to define the API signals.
    """
    backend_bad_call = QtCore.Signal(object)

    eip_alien_openvpn_already_running = QtCore.Signal()
    eip_can_start = QtCore.Signal()
    eip_cancelled_setup = QtCore.Signal()
    eip_cannot_start = QtCore.Signal()
    eip_client_certificate_ready = QtCore.Signal(object)
    eip_config_ready = QtCore.Signal(object)
    eip_connected = QtCore.Signal()
    eip_connection_aborted = QtCore.Signal()
    eip_connection_died = QtCore.Signal(object)
    eip_disconnected = QtCore.Signal(object)
    eip_dns_error = QtCore.Signal()
    eip_dns_ok = QtCore.Signal()
    eip_get_gateway_country_code = QtCore.Signal(object)
    eip_get_gateways_list = QtCore.Signal(object)
    eip_get_gateways_list_error = QtCore.Signal()
    eip_get_initialized_providers = QtCore.Signal(object)
    eip_network_unreachable = QtCore.Signal()
    eip_no_gateway = QtCore.Signal()
    eip_no_pkexec_error = QtCore.Signal()
    eip_no_polkit_agent_error = QtCore.Signal()
    eip_no_tun_kext_error = QtCore.Signal()
    eip_openvpn_already_running = QtCore.Signal()
    eip_openvpn_not_found_error = QtCore.Signal()
    eip_process_finished = QtCore.Signal(int)
    eip_process_restart_ping = QtCore.Signal()
    eip_process_restart_tls = QtCore.Signal()
    eip_state_changed = QtCore.Signal(dict)
    eip_status_changed = QtCore.Signal(dict)
    eip_stopped = QtCore.Signal()
    eip_tear_fw_down = QtCore.Signal(object)
    eip_bitmask_root_vpn_down = QtCore.Signal(object)
    eip_uninitialized_provider = QtCore.Signal()
    eip_vpn_launcher_exception = QtCore.Signal()

    imap_stopped = QtCore.Signal()

    keymanager_export_error = QtCore.Signal()
    keymanager_export_ok = QtCore.Signal()
    keymanager_import_addressmismatch = QtCore.Signal()
    keymanager_import_datamismatch = QtCore.Signal()
    keymanager_import_ioerror = QtCore.Signal()
    keymanager_import_missingkey = QtCore.Signal()
    keymanager_import_ok = QtCore.Signal()
    keymanager_key_details = QtCore.Signal(object)
    keymanager_keys_list = QtCore.Signal(object)

    prov_cancelled_setup = QtCore.Signal()
    prov_check_api_certificate = QtCore.Signal(object)
    prov_check_ca_fingerprint = QtCore.Signal(object)
    prov_download_ca_cert = QtCore.Signal(object)
    prov_download_provider_info = QtCore.Signal(object)
    prov_get_all_services = QtCore.Signal(object)
    prov_get_details = QtCore.Signal(object)
    prov_get_pinned_providers = QtCore.Signal(object)
    prov_get_supported_services = QtCore.Signal(object)
    prov_https_connection = QtCore.Signal(object)
    prov_name_resolution = QtCore.Signal(object)
    prov_problem_with_provider = QtCore.Signal()
    prov_unsupported_api = QtCore.Signal()
    prov_unsupported_client = QtCore.Signal()

    soledad_bootstrap_failed = QtCore.Signal()
    soledad_bootstrap_finished = QtCore.Signal()
    soledad_cancelled_bootstrap = QtCore.Signal()
    soledad_invalid_auth_token = QtCore.Signal()
    soledad_offline_failed = QtCore.Signal()
    soledad_offline_finished = QtCore.Signal()
    soledad_password_change_error = QtCore.Signal()
    soledad_password_change_ok = QtCore.Signal()

    srp_auth_bad_user_or_password = QtCore.Signal()
    srp_auth_connection_error = QtCore.Signal()
    srp_auth_error = QtCore.Signal()
    srp_auth_ok = QtCore.Signal()
    srp_auth_server_error = QtCore.Signal()
    srp_logout_error = QtCore.Signal()
    srp_logout_ok = QtCore.Signal()
    srp_not_logged_in_error = QtCore.Signal()
    srp_password_change_badpw = QtCore.Signal()
    srp_password_change_error = QtCore.Signal()
    srp_password_change_ok = QtCore.Signal()
    srp_registration_disabled = QtCore.Signal()
    srp_registration_failed = QtCore.Signal()
    srp_registration_finished = QtCore.Signal()
    srp_registration_taken = QtCore.Signal()
    srp_status_logged_in = QtCore.Signal()
    srp_status_not_logged_in = QtCore.Signal()
