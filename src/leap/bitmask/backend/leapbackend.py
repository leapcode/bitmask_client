# -*- coding: utf-8 -*-
# leapbackend.py
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
Backend for GUI/Logic communication.
"""
import logging

from Queue import Queue, Empty

from twisted.internet import reactor
from twisted.internet import threads, defer
from twisted.internet.task import LoopingCall

import zope.interface
import zope.proxy

from leap.bitmask.backend.leapsignaler import Signaler
from leap.bitmask.backend import components

logger = logging.getLogger(__name__)


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

        # Objects needed by several components, so we make a proxy and pass
        # them around
        self._soledad_proxy = zope.proxy.ProxyBase(None)
        self._keymanager_proxy = zope.proxy.ProxyBase(None)

        # Component registration
        self._register(components.Provider(self._signaler, bypass_checks))
        self._register(components.Register(self._signaler))
        self._register(components.Authenticate(self._signaler))
        self._register(components.EIP(self._signaler))
        self._register(components.Soledad(self._soledad_proxy,
                                          self._keymanager_proxy,
                                          self._signaler))
        self._register(components.Keymanager(self._keymanager_proxy,
                                             self._signaler))
        self._register(components.Mail(self._soledad_proxy,
                                       self._keymanager_proxy,
                                       self._signaler))

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
        logger.debug("Starting worker...")
        self._lc.start(0.01)

    def stop(self):
        """
        Stops the looping call and tries to cancel all the defers.
        """
        reactor.callLater(2, self._stop)

    def _stop(self):
        """
        Delayed stopping of worker. Called from `stop`.
        """
        logger.debug("Stopping worker...")
        if self._lc.running:
            self._lc.stop()
        else:
            logger.warning("Looping call is not running, cannot stop")

        logger.debug("Cancelling ongoing defers...")
        while len(self._ongoing_defers) > 0:
            d = self._ongoing_defers.pop()
            d.cancel()
        logger.debug("Defers cancelled.")

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
            logger.error("There was a problem registering %s" % (component,))

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
                    d.addCallbacks(self._signal_back, logger.error, cmd[2])
                d.addCallbacks(self._done_action, logger.error,
                               callbackKeywords={"d": d})
                d.addErrback(logger.error)
                self._ongoing_defers.append(d)
        except Empty:
            # If it's just empty we don't have anything to do.
            pass
        except defer.CancelledError:
            logger.debug("defer cancelled somewhere (CancelledError).")
        except Exception as e:
            # But we log the rest
            logger.exception("Unexpected exception: {0!r}".format(e))

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
        self._call_queue.put(("provider", "setup_provider", None, provider))

    def provider_cancel_setup(self):
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

    def provider_get_supported_services(self, domain):
        """
        Signal a list of supported services provided by the given provider.

        :param domain: the provider to get the services from.
        :type domain: str

        Signals:
            prov_get_supported_services -> list of unicode
        """
        self._call_queue.put(("provider", "get_supported_services", None,
                              domain))

    def provider_get_all_services(self, providers):
        """
        Signal a list of services provided by all the configured providers.

        :param providers: the list of providers to get the services.
        :type providers: list

        Signals:
            prov_get_all_services -> list of unicode
        """
        self._call_queue.put(("provider", "get_all_services", None,
                              providers))

    def provider_get_details(self, domain, lang):
        """
        Signal a ProviderConfigLight object with the current ProviderConfig
        settings.

        :param domain: the domain name of the provider.
        :type domain: str
        :param lang: the language to use for localized strings.
        :type lang: str

        Signals:
            prov_get_details -> ProviderConfigLight
        """
        self._call_queue.put(("provider", "get_details", None, domain, lang))

    def provider_get_pinned_providers(self):
        """
        Signal the pinned providers.

        Signals:
            prov_get_pinned_providers -> list of provider domains
        """
        self._call_queue.put(("provider", "get_pinned_providers", None))

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
        self._call_queue.put(("register", "register_user", None, provider,
                              username, password))

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
        self._call_queue.put(("eip", "setup_eip", None, provider,
                              skip_network))

    def eip_cancel_setup(self):
        """
        Cancel the ongoing setup EIP (if any).
        """
        self._call_queue.put(("eip", "cancel_setup_eip", None))

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
        self._call_queue.put(("eip", "start", None, restart))

    def eip_stop(self, shutdown=False, restart=False, failed=False):
        """
        Stop the EIP service.

        :param shutdown: whether this is the final shutdown.
        :type shutdown: bool

        :param restart: whether this is part of a restart.
        :type restart: bool
        """
        self._call_queue.put(("eip", "stop", None, shutdown, restart))

    def eip_terminate(self):
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

    def eip_can_start(self, domain):
        """
        Signal whether it has everything that is needed to run EIP or not

        :param domain: the domain for the provider to check
        :type domain: str

        Signals:
            eip_can_start
            eip_cannot_start
        """
        self._call_queue.put(("eip", "can_start",
                              None, domain))

    def eip_check_dns(self, domain):
        """
        Check if we can resolve the given domain name.

        :param domain: the domain for the provider to check
        :type domain: str

        Signals:
            eip_dns_ok
            eip_dns_error
        """
        self._call_queue.put(("eip", "check_dns", None, domain))

    def tear_fw_down(self):
        """
        Signal the need to tear the fw down.
        """
        self._call_queue.put(("eip", "tear_fw_down", None))

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
        self._call_queue.put(("authenticate", "login", None, provider,
                              username, password))

    def user_logout(self):
        """
        Log out the current session.

        Signals:
            srp_logout_ok
            srp_logout_error
            srp_not_logged_in_error
        """
        self._call_queue.put(("authenticate", "logout", None))

    def user_cancel_login(self):
        """
        Cancel the ongoing login (if any).
        """
        self._call_queue.put(("authenticate", "cancel_login", None))

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
        self._call_queue.put(("authenticate", "change_password", None,
                              current_password, new_password))

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
        self._call_queue.put(("soledad", "change_password", None,
                              new_password))

    def user_get_logged_in_status(self):
        """
        Signal if the user is currently logged in or not.

        Signals:
            srp_status_logged_in
            srp_status_not_logged_in
        """
        self._call_queue.put(("authenticate", "get_logged_in_status", None))

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
        self._call_queue.put(("soledad", "bootstrap", None,
                              username, domain, password))

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
        self._call_queue.put(("soledad", "load_offline", None,
                              username, password, uuid))

    def soledad_cancel_bootstrap(self):
        """
        Cancel the ongoing soledad bootstrapping process (if any).
        """
        self._call_queue.put(("soledad", "cancel_bootstrap", None))

    def soledad_close(self):
        """
        Close soledad database.
        """
        self._call_queue.put(("soledad", "close", None))

    def keymanager_list_keys(self):
        """
        Signal a list of public keys locally stored.

        Signals:
            keymanager_keys_list -> list
        """
        self._call_queue.put(("keymanager", "list_keys", None))

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
        self._call_queue.put(("keymanager", "export_keys", None,
                              username, filename))

    def keymanager_get_key_details(self, username):
        """
        Signal the given username's key details.

        :param username: the username whos keys we need to get details.
        :type username: str

        Signals:
            keymanager_key_details
        """
        self._call_queue.put(("keymanager", "get_key_details", None, username))

    def smtp_start_service(self, full_user_id, download_if_needed=False):
        """
        Start the SMTP service.

        :param full_user_id: user id, in the form "user@provider"
        :type full_user_id: str
        :param download_if_needed: True if it should check for mtime
                                   for the file
        :type download_if_needed: bool
        """
        self._call_queue.put(("mail", "start_smtp_service", None,
                              full_user_id, download_if_needed))

    def imap_start_service(self, full_user_id, offline=False):
        """
        Start the IMAP service.

        :param full_user_id: user id, in the form "user@provider"
        :type full_user_id: str
        :param offline: whether imap should start in offline mode or not.
        :type offline: bool
        """
        self._call_queue.put(("mail", "start_imap_service", None,
                              full_user_id, offline))

    def smtp_stop_service(self):
        """
        Stop the SMTP service.
        """
        self._call_queue.put(("mail", "stop_smtp_service", None))

    def imap_stop_service(self):
        """
        Stop imap service.

        Signals:
            imap_stopped
        """
        self._call_queue.put(("mail", "stop_imap_service", None))
