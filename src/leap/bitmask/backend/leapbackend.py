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
import socket
import time

from functools import partial
from Queue import Queue, Empty
from threading import Condition

from twisted.internet import reactor
from twisted.internet import threads, defer
from twisted.internet.task import LoopingCall
from twisted.python import log

import zope.interface
import zope.proxy

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.crypto.srpauth import SRPAuth
from leap.bitmask.crypto.srpregister import SRPRegister
from leap.bitmask.platform_init import IS_LINUX
from leap.bitmask.provider.providerbootstrapper import ProviderBootstrapper
from leap.bitmask.provider.pinned import PinnedProviders
from leap.bitmask.services import get_supported
from leap.bitmask.services.eip import eipconfig
from leap.bitmask.services.eip import get_openvpn_management
from leap.bitmask.services.eip.eipbootstrapper import EIPBootstrapper

from leap.bitmask.services.eip import vpnlauncher, vpnprocess
from leap.bitmask.services.eip import linuxvpnlauncher, darwinvpnlauncher
from leap.bitmask.services.eip import get_vpn_launcher

from leap.bitmask.services.mail.imapcontroller import IMAPController
from leap.bitmask.services.mail.smtpbootstrapper import SMTPBootstrapper
from leap.bitmask.services.mail.smtpconfig import SMTPConfig

from leap.bitmask.services.soledad.soledadbootstrapper import \
    SoledadBootstrapper
from leap.bitmask.util import force_eval

from leap.common import certs as leap_certs

from leap.keymanager import openpgp
from leap.keymanager.errors import KeyAddressMismatch, KeyFingerprintMismatch

from leap.soledad.client import NoStorageSecret, PassphraseTooShort

# Frontend side
from PySide import QtCore

logger = logging.getLogger(__name__)


class ILEAPComponent(zope.interface.Interface):
    """
    Interface that every component for the backend should comply to
    """

    key = zope.interface.Attribute("Key id for this component")


class ILEAPService(ILEAPComponent):
    """
    Interface that every Service needs to implement
    """

    def start(self, *args, **kwargs):
        """
        Start the service.
        """
        pass

    def stop(self, *args, **kwargs):
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
        self._signaler = signaler
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

        config = ProviderConfig.get_provider_config(provider)
        self._provider_config = config
        if config is not None:
            d = self._provider_bootstrapper.run_provider_setup_checks(
                config, download_if_needed=True)
        else:
            if self._signaler is not None:
                self._signaler.signal(
                    self._signaler.PROV_PROBLEM_WITH_PROVIDER_KEY)
            logger.error("Could not load provider configuration.")
            self._login_widget.set_enabled(True)

        if d is None:
            d = defer.Deferred()
        return d

    def _get_services(self, domain):
        """
        Returns a list of services provided by the given provider.

        :param domain: the provider to get the services from.
        :type domain: str

        :rtype: list of str
        """
        services = []
        provider_config = ProviderConfig.get_provider_config(domain)
        if provider_config is not None:
            services = provider_config.get_services()

        return services

    def get_supported_services(self, domain):
        """
        Signal a list of supported services provided by the given provider.

        :param domain: the provider to get the services from.
        :type domain: str

        Signals:
            prov_get_supported_services -> list of unicode
        """
        services = get_supported(self._get_services(domain))

        self._signaler.signal(
            self._signaler.PROV_GET_SUPPORTED_SERVICES, services)

    def get_all_services(self, providers):
        """
        Signal a list of services provided by all the configured providers.

        :param providers: the list of providers to get the services.
        :type providers: list

        Signals:
            prov_get_all_services -> list of unicode
        """
        services_all = set()

        for domain in providers:
            services = self._get_services(domain)
            services_all = services_all.union(set(services))

        self._signaler.signal(
            self._signaler.PROV_GET_ALL_SERVICES, services_all)

    def get_details(self, domain, lang=None):
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
        self._signaler.signal(
            self._signaler.PROV_GET_DETAILS,
            self._provider_config.get_light_config(domain, lang))

    def get_pinned_providers(self):
        """
        Signal the list of pinned provider domains.

        Signals:
            prov_get_pinned_providers -> list of provider domains
        """
        self._signaler.signal(
            self._signaler.PROV_GET_PINNED_PROVIDERS,
            PinnedProviders.domains())


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
        config = ProviderConfig.get_provider_config(domain)
        self._provider_config = config
        if config is not None:
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

    def setup_eip(self, domain, skip_network=False):
        """
        Initiate the setup for a provider

        :param domain: URL for the provider
        :type domain: unicode
        :param skip_network: Whether checks that involve network should be done
                             or not
        :type skip_network: bool

        :returns: the defer for the operation running in a thread.
        :rtype: twisted.internet.defer.Deferred
        """
        config = ProviderConfig.get_provider_config(domain)
        self._provider_config = config
        if config is not None:
            if skip_network:
                return defer.Deferred()
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

    def _start_eip(self, restart=False):
        """
        Start EIP

        :param restart: whether is is a restart.
        :type restart: bool
        """
        provider_config = self._provider_config
        eip_config = eipconfig.EIPConfig()
        domain = provider_config.get_domain()

        loaded = eipconfig.load_eipconfig_if_needed(
            provider_config, eip_config, domain)

        if not self._can_start(domain):
            if self._signaler is not None:
                self._signaler.signal(self._signaler.EIP_CONNECTION_ABORTED)
            return

        if not loaded:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.EIP_CONNECTION_ABORTED)
            logger.error("Tried to start EIP but cannot find any "
                         "available provider!")
            return

        host, port = get_openvpn_management()
        self._vpn.start(eipconfig=eip_config,
                        providerconfig=provider_config,
                        socket_host=host, socket_port=port,
                        restart=restart)

    def start(self, *args, **kwargs):
        """
        Start the service.
        """
        signaler = self._signaler

        if not self._provider_config.loaded():
            # This means that the user didn't call setup_eip first.
            self._signaler.signal(signaler.BACKEND_BAD_CALL, "EIP.start(), "
                                  "no provider loaded")
            return

        try:
            self._start_eip(*args, **kwargs)
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
            logger.debug('EIP: no errors')

    def _do_stop(self, shutdown=False, restart=False):
        """
        Stop the service. This is run in a thread to avoid blocking.
        """
        self._vpn.terminate(shutdown, restart)
        if IS_LINUX:
            self._wait_for_firewall_down()

    def stop(self, shutdown=False, restart=False):
        """
        Stop the service.
        """
        return threads.deferToThread(self._do_stop, shutdown, restart)

    def _wait_for_firewall_down(self):
        """
        Wait for the firewall to come down.
        """
        # Due to how we delay the resolvconf action in linux.
        # XXX this *has* to wait for a reasonable lapse, since we have some
        # delay in vpn.terminate.
        # For a better solution it should be signaled from backend that
        # everything is clear to proceed, or a timeout happened.
        MAX_FW_WAIT_RETRIES = 25
        FW_WAIT_STEP = 0.5

        retry = 1

        while retry <= MAX_FW_WAIT_RETRIES:
            if self._vpn.is_fw_down():
                self._signaler.signal(self._signaler.EIP_STOPPED)
                return
            else:
                #msg = "Firewall is not down yet, waiting... {0} of {1}"
                #msg = msg.format(retry, MAX_FW_WAIT_RETRIES)
                #logger.debug(msg)
                time.sleep(FW_WAIT_STEP)
                retry += 1
        logger.warning("After waiting, firewall is not down... "
                       "You might experience lack of connectivity")

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

    def tear_fw_down(self):
        """
        Tear the firewall down.
        """
        self._vpn.tear_down_firewall()

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

    def _can_start(self, domain):
        """
        Returns True if it has everything that is needed to run EIP,
        False otherwise

        :param domain: the domain for the provider to check
        :type domain: str
        """
        eip_config = eipconfig.EIPConfig()
        provider_config = ProviderConfig.get_provider_config(domain)

        api_version = provider_config.get_api_version()
        eip_config.set_api_version(api_version)
        eip_loaded = eip_config.load(eipconfig.get_eipconfig_path(domain))

        launcher = get_vpn_launcher()
        ovpn_path = force_eval(launcher.OPENVPN_BIN_PATH)
        if not os.path.isfile(ovpn_path):
            logger.error("Cannot start OpenVPN, binary not found")
            return False

        # check for other problems
        if not eip_loaded or provider_config is None:
            logger.error("Cannot load provider and eip config, cannot "
                         "autostart")
            return False

        client_cert_path = eip_config.\
            get_client_cert_path(provider_config, about_to_download=False)

        if leap_certs.should_redownload(client_cert_path):
            logger.error("The client should redownload the certificate,"
                         " cannot autostart")
            return False

        if not os.path.isfile(client_cert_path):
            logger.error("Can't find the certificate, cannot autostart")
            return False

        return True

    def can_start(self, domain):
        """
        Signal whether it has everything that is needed to run EIP or not

        :param domain: the domain for the provider to check
        :type domain: str

        Signals:
            eip_can_start
            eip_cannot_start
        """
        if self._can_start(domain):
            if self._signaler is not None:
                self._signaler.signal(self._signaler.EIP_CAN_START)
        else:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.EIP_CANNOT_START)

    def check_dns(self, domain):
        """
        Check if we can resolve the given domain name.

        :param domain: the domain to check.
        :type domain: str
        """
        def do_check():
            """
            Try to resolve the domain name.
            """
            socket.gethostbyname(domain.encode('idna'))

        def check_ok(_):
            """
            Callback handler for `do_check`.
            """
            self._signaler.signal(self._signaler.EIP_DNS_OK)
            logger.debug("DNS check OK")

        def check_err(failure):
            """
            Errback handler for `do_check`.

            :param failure: the failure that triggered the errback.
            :type failure: twisted.python.failure.Failure
            """
            logger.debug("Can't resolve hostname. {0!r}".format(failure))

            self._signaler.signal(self._signaler.EIP_DNS_ERROR)

            # python 2.7.4 raises socket.error
            # python 2.7.5 raises socket.gaierror
            failure.trap(socket.gaierror, socket.error)

        d = threads.deferToThread(do_check)
        d.addCallback(check_ok)
        d.addErrback(check_err)


class Soledad(object):
    """
    Interfaces with setup of Soledad.
    """
    zope.interface.implements(ILEAPComponent)

    def __init__(self, soledad_proxy, keymanager_proxy, signaler=None):
        """
        Constructor for the Soledad component.

        :param soledad_proxy: proxy to pass around a Soledad object.
        :type soledad_proxy: zope.ProxyBase
        :param keymanager_proxy: proxy to pass around a Keymanager object.
        :type keymanager_proxy: zope.ProxyBase
        :param signaler: Object in charge of handling communication
                         back to the frontend
        :type signaler: Signaler
        """
        self.key = "soledad"
        self._soledad_proxy = soledad_proxy
        self._keymanager_proxy = keymanager_proxy
        self._signaler = signaler
        self._soledad_bootstrapper = SoledadBootstrapper(signaler)
        self._soledad_defer = None

    def bootstrap(self, username, domain, password):
        """
        Bootstrap Soledad with the user credentials.

        Signals:
            soledad_download_config
            soledad_gen_key

        :param user: user's login
        :type user: unicode
        :param domain: the domain that we are using.
        :type domain: unicode
        :param password: user's password
        :type password: unicode
        """
        provider_config = ProviderConfig.get_provider_config(domain)
        if provider_config is not None:
            self._soledad_defer = threads.deferToThread(
                self._soledad_bootstrapper.run_soledad_setup_checks,
                provider_config, username, password,
                download_if_needed=True)
            self._soledad_defer.addCallback(self._set_proxies_cb)
        else:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.SOLEDAD_BOOTSTRAP_FAILED)
            logger.error("Could not load provider configuration.")

        return self._soledad_defer

    def _set_proxies_cb(self, _):
        """
        Update the soledad and keymanager proxies to reference the ones created
        in the bootstrapper.
        """
        zope.proxy.setProxiedObject(self._soledad_proxy,
                                    self._soledad_bootstrapper.soledad)
        zope.proxy.setProxiedObject(self._keymanager_proxy,
                                    self._soledad_bootstrapper.keymanager)

    def load_offline(self, username, password, uuid):
        """
        Load the soledad database in offline mode.

        :param username: full user id (user@provider)
        :type username: str or unicode
        :param password: the soledad passphrase
        :type password: unicode
        :param uuid: the user uuid
        :type uuid: str or unicode

        Signals:
            Signaler.soledad_offline_finished
            Signaler.soledad_offline_failed
        """
        self._soledad_bootstrapper.load_offline_soledad(
            username, password, uuid)

    def cancel_bootstrap(self):
        """
        Cancel the ongoing soledad bootstrap (if any).
        """
        if self._soledad_defer is not None:
            logger.debug("Cancelling soledad defer.")
            self._soledad_defer.cancel()
            self._soledad_defer = None
            zope.proxy.setProxiedObject(self._soledad_proxy, None)

    def close(self):
        """
        Close soledad database.
        """
        if not zope.proxy.sameProxiedObjects(self._soledad_proxy, None):
            self._soledad_proxy.close()
            zope.proxy.setProxiedObject(self._soledad_proxy, None)

    def _change_password_ok(self, _):
        """
        Password change callback.
        """
        if self._signaler is not None:
            self._signaler.signal(self._signaler.SOLEDAD_PASSWORD_CHANGE_OK)

    def _change_password_error(self, failure):
        """
        Password change errback.

        :param failure: failure object containing problem.
        :type failure: twisted.python.failure.Failure
        """
        if failure.check(NoStorageSecret):
            logger.error("No storage secret for password change in Soledad.")
        if failure.check(PassphraseTooShort):
            logger.error("Passphrase too short.")

        if self._signaler is not None:
            self._signaler.signal(self._signaler.SOLEDAD_PASSWORD_CHANGE_ERROR)

    def change_password(self, new_password):
        """
        Change the database's password.

        :param new_password: the new password.
        :type new_password: unicode

        :returns: a defer to interact with.
        :rtype: twisted.internet.defer.Deferred
        """
        d = threads.deferToThread(self._soledad_proxy.change_passphrase,
                                  new_password)
        d.addCallback(self._change_password_ok)
        d.addErrback(self._change_password_error)


class Keymanager(object):
    """
    Interfaces with KeyManager.
    """
    zope.interface.implements(ILEAPComponent)

    def __init__(self, keymanager_proxy, signaler=None):
        """
        Constructor for the Keymanager component.

        :param keymanager_proxy: proxy to pass around a Keymanager object.
        :type keymanager_proxy: zope.ProxyBase
        :param signaler: Object in charge of handling communication
                         back to the frontend
        :type signaler: Signaler
        """
        self.key = "keymanager"
        self._keymanager_proxy = keymanager_proxy
        self._signaler = signaler

    def import_keys(self, username, filename):
        """
        Imports the username's key pair.
        Those keys need to be ascii armored.

        :param username: the user that will have the imported pair of keys.
        :type username: str
        :param filename: the name of the file where the key pair is stored.
        :type filename: str
        """
        # NOTE: This feature is disabled right now since is dangerous
        return

        new_key = ''
        signal = None
        try:
            with open(filename, 'r') as keys_file:
                new_key = keys_file.read()
        except IOError as e:
            logger.error("IOError importing key. {0!r}".format(e))
            signal = self._signaler.KEYMANAGER_IMPORT_IOERROR
            self._signaler.signal(signal)
            return

        keymanager = self._keymanager_proxy
        try:
            public_key, private_key = keymanager.parse_openpgp_ascii_key(
                new_key)
        except (KeyAddressMismatch, KeyFingerprintMismatch) as e:
            logger.error(repr(e))
            signal = self._signaler.KEYMANAGER_IMPORT_DATAMISMATCH
            self._signaler.signal(signal)
            return

        if public_key is None or private_key is None:
            signal = self._signaler.KEYMANAGER_IMPORT_MISSINGKEY
            self._signaler.signal(signal)
            return

        current_public_key = keymanager.get_key(username, openpgp.OpenPGPKey)
        if public_key.address != current_public_key.address:
            logger.error("The key does not match the ID")
            signal = self._signaler.KEYMANAGER_IMPORT_ADDRESSMISMATCH
            self._signaler.signal(signal)
            return

        keymanager.delete_key(self._key)
        keymanager.delete_key(self._key_priv)
        keymanager.put_key(public_key)
        keymanager.put_key(private_key)
        keymanager.send_key(openpgp.OpenPGPKey)

        logger.debug('Import ok')
        signal = self._signaler.KEYMANAGER_IMPORT_OK

        self._signaler.signal(signal)

    def export_keys(self, username, filename):
        """
        Export the given username's keys to a file.

        :param username: the username whos keys we need to export.
        :type username: str
        :param filename: the name of the file where we want to save the keys.
        :type filename: str
        """
        keymanager = self._keymanager_proxy

        public_key = keymanager.get_key(username, openpgp.OpenPGPKey)
        private_key = keymanager.get_key(username, openpgp.OpenPGPKey,
                                         private=True)
        try:
            with open(filename, 'w') as keys_file:
                keys_file.write(public_key.key_data)
                keys_file.write(private_key.key_data)

            logger.debug('Export ok')
            self._signaler.signal(self._signaler.KEYMANAGER_EXPORT_OK)
        except IOError as e:
            logger.error("IOError exporting key. {0!r}".format(e))
            self._signaler.signal(self._signaler.KEYMANAGER_EXPORT_ERROR)

    def list_keys(self):
        """
        List all the keys stored in the local DB.
        """
        keys = self._keymanager_proxy.get_all_keys_in_local_db()
        self._signaler.signal(self._signaler.KEYMANAGER_KEYS_LIST, keys)

    def get_key_details(self, username):
        """
        List all the keys stored in the local DB.
        """
        public_key = self._keymanager_proxy.get_key(username,
                                                    openpgp.OpenPGPKey)
        details = (public_key.key_id, public_key.fingerprint)
        self._signaler.signal(self._signaler.KEYMANAGER_KEY_DETAILS, details)


class Mail(object):
    """
    Interfaces with setup and launch of Mail.
    """
    # We give each service some time to come to a halt before forcing quit
    SERVICE_STOP_TIMEOUT = 20

    zope.interface.implements(ILEAPComponent)

    def __init__(self, soledad_proxy, keymanager_proxy, signaler=None):
        """
        Constructor for the Mail component.

        :param soledad_proxy: proxy to pass around a Soledad object.
        :type soledad_proxy: zope.ProxyBase
        :param keymanager_proxy: proxy to pass around a Keymanager object.
        :type keymanager_proxy: zope.ProxyBase
        :param signaler: Object in charge of handling communication
                         back to the frontend
        :type signaler: Signaler
        """
        self.key = "mail"
        self._signaler = signaler
        self._soledad_proxy = soledad_proxy
        self._keymanager_proxy = keymanager_proxy
        self._imap_controller = IMAPController(self._soledad_proxy,
                                               self._keymanager_proxy)
        self._smtp_bootstrapper = SMTPBootstrapper()
        self._smtp_config = SMTPConfig()

    def start_smtp_service(self, full_user_id, download_if_needed=False):
        """
        Start the SMTP service.

        :param full_user_id: user id, in the form "user@provider"
        :type full_user_id: str
        :param download_if_needed: True if it should check for mtime
                                   for the file
        :type download_if_needed: bool

        :returns: a defer to interact with.
        :rtype: twisted.internet.defer.Deferred
        """
        return threads.deferToThread(
            self._smtp_bootstrapper.start_smtp_service,
            self._keymanager_proxy, full_user_id, download_if_needed)

    def start_imap_service(self, full_user_id, offline=False):
        """
        Start the IMAP service.

        :param full_user_id: user id, in the form "user@provider"
        :type full_user_id: str
        :param offline: whether imap should start in offline mode or not.
        :type offline: bool

        :returns: a defer to interact with.
        :rtype: twisted.internet.defer.Deferred
        """
        return threads.deferToThread(
            self._imap_controller.start_imap_service,
            full_user_id, offline)

    def stop_smtp_service(self):
        """
        Stop the SMTP service.

        :returns: a defer to interact with.
        :rtype: twisted.internet.defer.Deferred
        """
        return threads.deferToThread(self._smtp_bootstrapper.stop_smtp_service)

    def _stop_imap_service(self):
        """
        Stop imap and wait until the service is stopped to signal that is done.
        """
        cv = Condition()
        cv.acquire()
        threads.deferToThread(self._imap_controller.stop_imap_service, cv)
        logger.debug('Waiting for imap service to stop.')
        cv.wait(self.SERVICE_STOP_TIMEOUT)
        logger.debug('IMAP stopped')
        self._signaler.signal(self._signaler.IMAP_STOPPED)

    def stop_imap_service(self):
        """
        Stop imap service (fetcher, factory and port).

        :returns: a defer to interact with.
        :rtype: twisted.internet.defer.Deferred
        """
        return threads.deferToThread(self._stop_imap_service)


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
        self._login_defer = None
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
        config = ProviderConfig.get_provider_config(domain)
        if config is not None:
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

        # Objects needed by several components, so we make a proxy and pass
        # them around
        self._soledad_proxy = zope.proxy.ProxyBase(None)
        self._keymanager_proxy = zope.proxy.ProxyBase(None)

        # Component registration
        self._register(Provider(self._signaler, bypass_checks))
        self._register(Register(self._signaler))
        self._register(Authenticate(self._signaler))
        self._register(EIP(self._signaler))
        self._register(Soledad(self._soledad_proxy,
                               self._keymanager_proxy,
                               self._signaler))
        self._register(Keymanager(self._keymanager_proxy,
                                  self._signaler))
        self._register(Mail(self._soledad_proxy,
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
