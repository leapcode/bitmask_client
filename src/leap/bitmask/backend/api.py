# -*- coding: utf-8 -*-
# api.py
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
Backend available API and SIGNALS definition.
"""
STOP_REQUEST = "stop"

API = (
    STOP_REQUEST,  # this method needs to be defined in order to support the
                   # backend stop action

    "eip_can_start",
    "eip_cancel_setup",
    "eip_check_dns",
    "eip_get_gateways_list",
    "eip_get_initialized_providers",
    "eip_setup",
    "eip_start",
    "eip_stop",
    "eip_terminate",
    "imap_start_service",
    "imap_stop_service",
    "keymanager_export_keys",
    "keymanager_get_key_details",
    "keymanager_list_keys",
    "provider_bootstrap",
    "provider_cancel_setup",
    "provider_get_all_services",
    "provider_get_details",
    "provider_get_pinned_providers",
    "provider_get_supported_services",
    "provider_setup",
    "smtp_start_service",
    "smtp_stop_service",
    "soledad_bootstrap",
    "soledad_cancel_bootstrap",
    "soledad_change_password",
    "soledad_close",
    "soledad_load_offline",
    "tear_fw_down",
    "user_cancel_login",
    "user_change_password",
    "user_get_logged_in_status",
    "user_login",
    "user_logout",
    "user_register",
)


SIGNALS = (
    "backend_bad_call",
    "eip_alien_openvpn_already_running",
    "eip_can_start",
    "eip_cancelled_setup",
    "eip_cannot_start",
    "eip_client_certificate_ready",
    "eip_config_ready",
    "eip_connected",
    "eip_connection_aborted",
    "eip_connection_died",
    "eip_disconnected",
    "eip_dns_error",
    "eip_dns_ok",
    "eip_get_gateways_list",
    "eip_get_gateways_list_error",
    "eip_get_initialized_providers",
    "eip_network_unreachable",
    "eip_no_pkexec_error",
    "eip_no_polkit_agent_error",
    "eip_no_tun_kext_error",
    "eip_openvpn_already_running",
    "eip_openvpn_not_found_error",
    "eip_process_finished",
    "eip_process_restart_ping",
    "eip_process_restart_tls",
    "eip_state_changed",
    "eip_status_changed",
    "eip_stopped",
    "eip_tear_fw_down",
    "eip_uninitialized_provider",
    "eip_vpn_launcher_exception",
    "imap_stopped",
    "keymanager_export_error",
    "keymanager_export_ok",
    "keymanager_import_addressmismatch",
    "keymanager_import_datamismatch",
    "keymanager_import_ioerror",
    "keymanager_import_missingkey",
    "keymanager_import_ok",
    "keymanager_key_details",
    "keymanager_keys_list",
    "prov_cancelled_setup",
    "prov_check_api_certificate",
    "prov_check_ca_fingerprint",
    "prov_download_ca_cert",
    "prov_download_provider_info",
    "prov_get_all_services",
    "prov_get_details",
    "prov_get_pinned_providers",
    "prov_get_supported_services",
    "prov_https_connection",
    "prov_name_resolution",
    "prov_problem_with_provider",
    "prov_unsupported_api",
    "prov_unsupported_client",
    "soledad_bootstrap_failed",
    "soledad_bootstrap_finished",
    "soledad_cancelled_bootstrap",
    "soledad_invalid_auth_token",
    "soledad_offline_failed",
    "soledad_offline_finished",
    "soledad_password_change_error",
    "soledad_password_change_ok",
    "srp_auth_bad_user_or_password",
    "srp_auth_connection_error",
    "srp_auth_error",
    "srp_auth_ok",
    "srp_auth_server_error",
    "srp_logout_error",
    "srp_logout_ok",
    "srp_not_logged_in_error",
    "srp_password_change_badpw",
    "srp_password_change_error",
    "srp_password_change_ok",
    "srp_registration_failed",
    "srp_registration_finished",
    "srp_registration_taken",
    "srp_status_logged_in",
    "srp_status_not_logged_in",
)
