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
Backend components
"""

# TODO [ ] Get rid of all this deferToThread mess, or at least contain
#          all of it into its own threadpool.

import logging
import os
import socket
import time

from functools import partial

from twisted.internet import threads, defer
from twisted.python import log

import zope.interface
import zope.proxy

from leap.bitmask.backend.settings import Settings, GATEWAY_AUTOMATIC
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
from leap.bitmask.util.privilege_policies import LinuxPolicyChecker

from leap.common import certs as leap_certs

from leap.keymanager import openpgp

from leap.soledad.client.secrets import PassphraseTooShort
from leap.soledad.client.secrets import NoStorageSecret

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
                    self._signaler.prov_problem_with_provider)
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
            self._signaler.prov_get_supported_services, services)

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
            self._signaler.prov_get_all_services, list(services_all))

    def get_details(self, domain, lang=None):
        """
        Signal a dict with the current ProviderConfig settings.

        :param domain: the domain name of the provider.
        :type domain: str
        :param lang: the language to use for localized strings.
        :type lang: str

        Signals:
            prov_get_details -> dict
        """
        self._signaler.signal(
            self._signaler.prov_get_details,
            self._provider_config.get_light_config(domain, lang))

    def get_pinned_providers(self):
        """
        Signal the list of pinned provider domains.

        Signals:
            prov_get_pinned_providers -> list of provider domains
        """
        self._signaler.signal(
            self._signaler.prov_get_pinned_providers,
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
                self._signaler.signal(self._signaler.srp_registration_failed)
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
                self._signaler.signal(self._signaler.eip_connection_aborted)
            return

        if not loaded:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.eip_connection_aborted)
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
            self._signaler.signal(signaler.backend_bad_call, "EIP.start(), "
                                  "no provider loaded")
            return

        try:
            self._start_eip(*args, **kwargs)
        except vpnprocess.OpenVPNAlreadyRunning:
            signaler.signal(signaler.eip_openvpn_already_running)
        except vpnprocess.AlienOpenVPNAlreadyRunning:
            signaler.signal(signaler.eip_alien_openvpn_already_running)
        except vpnlauncher.OpenVPNNotFoundException:
            signaler.signal(signaler.eip_openvpn_not_found_error)
        except vpnlauncher.VPNLauncherException:
            # TODO: this seems to be used for 'gateway not found' only.
            #       see vpnlauncher.py
            signaler.signal(signaler.eip_vpn_launcher_exception)
        except linuxvpnlauncher.EIPNoPolkitAuthAgentAvailable:
            signaler.signal(signaler.eip_no_polkit_agent_error)
        except linuxvpnlauncher.EIPNoPkexecAvailable:
            signaler.signal(signaler.eip_no_pkexec_error)
        except darwinvpnlauncher.EIPNoTunKextLoaded:
            signaler.signal(signaler.eip_no_tun_kext_error)
        except Exception as e:
            logger.error("Unexpected problem: {0!r}".format(e))
        else:
            logger.debug('EIP: no errors')

    def stop(self, shutdown=False, restart=False):
        """
        Stop the service.
        """
        self._vpn.terminate(shutdown, restart)
        if IS_LINUX:
            self._wait_for_firewall_down()

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
                self._signaler.signal(self._signaler.eip_stopped)
                return
            else:
                # msg = "Firewall is not down yet, waiting... {0} of {1}"
                # msg = msg.format(retry, MAX_FW_WAIT_RETRIES)
                # logger.debug(msg)
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
            self._signaler.signal(self._signaler.eip_get_initialized_providers,
                                  filtered_domains)

    def tear_fw_down(self):
        """
        Tear the firewall down.
        """
        self._vpn.tear_down_firewall()

    def bitmask_root_vpn_down(self):
        """
        Bring openvpn down, using bitmask-root helper.
        """
        self._vpn.bitmask_root_vpn_down()

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
                    self._signaler.eip_uninitialized_provider)
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
                    self._signaler.eip_get_gateways_list_error)
            return

        gateways = eipconfig.VPNGatewaySelector(eip_config).get_gateways_list()

        if self._signaler is not None:
            self._signaler.signal(
                self._signaler.eip_get_gateways_list, gateways)

    def get_gateway_country_code(self, domain):
        """
        Signal the country code for the currently used gateway for the given
        provider.

        :param domain: the domain to get country code.
        :type domain: str

        Signals:
            eip_get_gateway_country_code -> str
            eip_no_gateway
        """
        settings = Settings()

        eip_config = eipconfig.EIPConfig()
        provider_config = ProviderConfig.get_provider_config(domain)

        api_version = provider_config.get_api_version()
        eip_config.set_api_version(api_version)
        eip_config.load(eipconfig.get_eipconfig_path(domain))

        gateway_selector = eipconfig.VPNGatewaySelector(eip_config)
        gateway_conf = settings.get_selected_gateway(domain)

        if gateway_conf == GATEWAY_AUTOMATIC:
            gateways = gateway_selector.get_gateways()
        else:
            gateways = [gateway_conf]

        if not gateways:
            self._signaler.signal(self._signaler.eip_no_gateway)
            return

        # this only works for selecting the first gateway, as we're
        # currently doing.
        ccodes = gateway_selector.get_gateways_country_code()
        gateway_ccode = ccodes[gateways[0]]

        self._signaler.signal(self._signaler.eip_get_gateway_country_code,
                              gateway_ccode)

    def _can_start(self, domain):
        """
        Returns True if it has everything that is needed to run EIP,
        False otherwise

        :param domain: the domain for the provider to check
        :type domain: str
        """
        if not LinuxPolicyChecker.is_up():
            logger.error("No polkit agent running.")
            return False

        eip_config = eipconfig.EIPConfig()
        provider_config = ProviderConfig.get_provider_config(domain)

        api_version = provider_config.get_api_version()
        eip_config.set_api_version(api_version)
        eip_loaded = eip_config.load(eipconfig.get_eipconfig_path(domain))

        launcher = get_vpn_launcher()
        ovpn_path = force_eval(launcher.OPENVPN_BIN_PATH)
        if not os.path.isfile(ovpn_path):
            logger.error("Cannot start OpenVPN, binary not found: %s" %
                         (ovpn_path,))
            return False

        # check for other problems
        if not eip_loaded or provider_config is None:
            logger.error("Cannot load provider and eip config, cannot "
                         "autostart")
            return False

        client_cert_path = eip_config.\
            get_client_cert_path(provider_config, about_to_download=True)

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
                self._signaler.signal(self._signaler.eip_can_start)
        else:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.eip_cannot_start)

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
            self._signaler.signal(self._signaler.eip_dns_ok)
            logger.debug("DNS check OK")

        def check_err(failure):
            """
            Errback handler for `do_check`.

            :param failure: the failure that triggered the errback.
            :type failure: twisted.python.failure.Failure
            """
            logger.debug("Can't resolve hostname. {0!r}".format(failure))

            self._signaler.signal(self._signaler.eip_dns_error)

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
            sb = self._soledad_bootstrapper
            self._soledad_defer = sb.run_soledad_setup_checks(
                provider_config, username, password,
                download_if_needed=True)
            self._soledad_defer.addCallback(self._set_proxies_cb)
        else:
            if self._signaler is not None:
                self._signaler.signal(self._signaler.soledad_bootstrap_failed)
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
        d = self._soledad_bootstrapper.load_offline_soledad(
            username, password, uuid)
        d.addCallback(self._set_proxies_cb)

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
            self._signaler.signal(self._signaler.soledad_password_change_ok)

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
            self._signaler.signal(self._signaler.soledad_password_change_error)

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

    def export_keys(self, username, filename):
        """
        Export the given username's keys to a file.

        :param username: the username whos keys we need to export.
        :type username: str
        :param filename: the name of the file where we want to save the keys.
        :type filename: str
        """
        keymanager = self._keymanager_proxy

        def export(keys):
            public_key, private_key = keys
            # XXX: This is blocking. We could use writeToFD, but is POSIX only
            #      https://twistedmatrix.com/documents/current/api/twisted.internet.fdesc.html#writeToFD
            with open(filename, 'w') as keys_file:
                keys_file.write(public_key.key_data)
                keys_file.write(private_key.key_data)

            logger.debug('Export ok')
            self._signaler.signal(self._signaler.keymanager_export_ok)

        def log_error(failure):
            logger.error(
                "Error exporting key. {0!r}".format(failure.value))
            self._signaler.signal(self._signaler.keymanager_export_error)

        dpub = keymanager.get_key(username, openpgp.OpenPGPKey)
        dpriv = keymanager.get_key(username, openpgp.OpenPGPKey,
                                   private=True)
        d = defer.gatherResults([dpub, dpriv])
        d.addCallback(export)
        d.addErrback(log_error)

    def list_keys(self):
        """
        List all the keys stored in the local DB.
        """
        d = self._keymanager_proxy.get_all_keys()
        d.addCallback(
            lambda keys:
            self._signaler.signal(self._signaler.keymanager_keys_list, keys))

    def get_key_details(self, username):
        """
        List all the keys stored in the local DB.
        """
        def signal_details(public_key):
            details = (public_key.key_id, public_key.fingerprint)
            self._signaler.signal(self._signaler.keymanager_key_details,
                                  details)

        d = self._keymanager_proxy.get_key(username,
                                           openpgp.OpenPGPKey)
        d.addCallback(signal_details)


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
        # FIXME just get a fucking deferred and signal as a callback, with
        # timeout and cancellability
        threads.deferToThread(self._imap_controller.stop_imap_service)
        logger.debug('Waiting for imap service to stop.')
        self._signaler.signal(self._signaler.imap_stopped)

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
                self._signaler.signal(self._signaler.srp_auth_error)
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
                self._signaler.signal(self._signaler.srp_not_logged_in_error)
            return

        return self._srp_auth.change_password(current_password, new_password)

    def logout(self):
        """
        Log out the current session.
        Expects a session_id to exists, might raise AssertionError
        """
        if not self._is_logged_in():
            if self._signaler is not None:
                self._signaler.signal(self._signaler.srp_not_logged_in_error)
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
            signal = self._signaler.srp_status_logged_in
        else:
            signal = self._signaler.srp_status_not_logged_in

        self._signaler.signal(signal)
