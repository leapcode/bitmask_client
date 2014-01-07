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

from Queue import Queue, Empty

from twisted.internet import threads, defer
from twisted.internet.task import LoopingCall
from twisted.python import log

import zope.interface

from leap.bitmask.config.providerconfig import ProviderConfig
from leap.bitmask.provider.providerbootstrapper import ProviderBootstrapper

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

    def start(self):
        """
        Starts the service.
        """
        pass

    def stop(self):
        """
        Stops the service.
        """
        pass

    def terminate(self):
        """
        Terminates the service, not necessarily in a nice way.
        """
        pass

    def status(self):
        """
        Returns a json object with the current status for the service.

        :rtype: object (list, str, dict)
        """
        # XXX: Use a namedtuple or a specific object instead of a json
        # object, since parsing it will be problematic otherwise.
        # It has to be something easily serializable though.
        pass

    def set_configs(self, keyval):
        """
        Sets the config parameters for this Service.

        :param keyval: values to configure
        :type keyval: dict, {str: str}
        """
        pass

    def get_configs(self, keys):
        """
        Returns the configuration values for the list of keys.

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

    PROBLEM_SIGNAL = "prov_problem_with_provider"

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
        object.__init__(self)
        self.key = "provider"
        self._provider_bootstrapper = ProviderBootstrapper(signaler,
                                                           bypass_checks)
        self._download_provider_defer = None
        self._provider_config = ProviderConfig()

    def setup_provider(self, provider):
        """
        Initiates the setup for a provider

        :param provider: URL for the provider
        :type provider: unicode
        """
        log.msg("Setting up provider %s..." % (provider.encode("idna"),))
        pb = self._provider_bootstrapper
        d = pb.run_provider_select_checks(provider, download_if_needed=True)
        self._download_provider_defer = d
        return d

    def bootstrap(self, provider):
        """
        Second stage of bootstrapping for a provider.

        :param provider: URL for the provider
        :type provider: unicode
        """

        d = None

        # If there's no loaded provider or
        # we want to connect to other provider...
        if (not self._provider_config.loaded() or
                self._provider_config.get_domain() != provider):
            self._provider_config.load(
                os.path.join("leap", "providers",
                             provider, "provider.json"))

        if self._provider_config.loaded():
            d = self._provider_bootstrapper.run_provider_setup_checks(
                self._provider_config,
                download_if_needed=True)
        else:
            if self._signaler is not None:
                self._signaler.signal(self.PROBLEM_SIGNAL)
            logger.error("Could not load provider configuration.")
            self._login_widget.set_enabled(True)

        if d is None:
            d = defer.Deferred()
        return d


class Signaler(QtCore.QObject):
    """
    Signaler object, handles converting string commands to Qt signals.

    This is intended for the separation in frontend/backend, this will
    live in the frontend.
    """

    # Signals for the ProviderBootstrapper
    # These will only exist in the frontend
    prov_name_resolution = QtCore.Signal(object)
    prov_https_connection = QtCore.Signal(object)
    prov_download_provider_info = QtCore.Signal(object)

    prov_download_ca_cert = QtCore.Signal(object)
    prov_check_ca_fingerprint = QtCore.Signal(object)
    prov_check_api_certificate = QtCore.Signal(object)

    prov_problem_with_provider = QtCore.Signal(object)

    prov_unsupported_client = QtCore.Signal(object)

    # These will exist both in the backend and the front end.
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
            self.PROV_UNSUPPORTED_CLIENT
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
        log.msg("Signaling %s :: %s" % (key, data))

        # for some reason emitting 'None' gives a segmentation fault.
        if data is None:
            data = ''

        try:
            self._signals[key].emit(data)
        except KeyError:
            log.msg("Unknown key for signal %s!" % (key,))


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
        object.__init__(self)

        # Components map for the commands received
        self._components = {}

        # Ongoing defers that will be cancelled at stop time
        self._ongoing_defers = []

        # Signaler object to translate commands into Qt signals
        self._signaler = Signaler()

        # Component registration
        self._register(Provider(self._signaler, bypass_checks))

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
        except Exception:
            # But we log the rest
            log.err()

    def _done_action(self, _, d):
        """
        Remover of the defer once it's done

        :param d: defer to remove
        :type d: twisted.internet.defer.Deferred
        """
        self._ongoing_defers.remove(d)

    # XXX: Temporal interface until we migrate to zmq
    # We simulate the calls to zmq.send_multipart. Once we separate
    # this in two processes, the methods bellow can be changed to
    # send_multipart and this backend class will be really simple.

    def setup_provider(self, provider):
        self._call_queue.put(("provider", "setup_provider", None, provider))

    def provider_bootstrap(self, provider):
        self._call_queue.put(("provider", "bootstrap", None, provider))
