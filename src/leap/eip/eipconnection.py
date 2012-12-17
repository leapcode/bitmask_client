"""
EIP Connection Class
"""
from __future__ import (absolute_import,)
import logging
import Queue
import sys
import time

from dateutil.parser import parse as dateparse

from leap.eip.checks import ProviderCertChecker
from leap.eip.checks import EIPConfigChecker
from leap.eip import config as eipconfig
from leap.eip import exceptions as eip_exceptions
from leap.eip.openvpnconnection import OpenVPNConnection

logger = logging.getLogger(name=__name__)


class StatusMixIn(object):

    # a bunch of methods related with querying the connection
    # state/status and displaying useful info.
    # Needs to get clear on what is what, and
    # separate functions.
    # Should separate EIPConnectionStatus (self.status)
    # from the OpenVPN state/status command and parsing.

    def connection_state(self):
        """
        returns the current connection state
        """
        return self.status.current

    def get_icon_name(self):
        """
        get icon name from status object
        """
        return self.status.get_state_icon()

    def get_leap_status(self):
        return self.status.get_leap_status()

    def poll_connection_state(self):
        """
        """
        try:
            state = self.get_connection_state()
        except eip_exceptions.ConnectionRefusedError:
            # connection refused. might be not ready yet.
            logger.warning('connection refused')
            return
        if not state:
            logger.debug('no state')
            return
        (ts, status_step,
         ok, ip, remote) = state
        self.status.set_vpn_state(status_step)
        status_step = self.status.get_readable_status()
        return (ts, status_step, ok, ip, remote)

    def make_error(self):
        """
        capture error and wrap it in an
        understandable format
        """
        # mostly a hack to display errors in the debug UI
        # w/o breaking the polling.
        #XXX get helpful error codes
        self.with_errors = True
        now = int(time.time())
        return '%s,LAUNCHER ERROR,ERROR,-,-' % now

    def state(self):
        """
        Sends OpenVPN command: state
        """
        state = self._send_command("state")
        if not state:
            return None
        if isinstance(state, str):
            return state
        if isinstance(state, list):
            if len(state) == 1:
                return state[0]
            else:
                return state[-1]

    def vpn_status(self):
        """
        OpenVPN command: status
        """
        status = self._send_command("status")
        return status

    def vpn_status2(self):
        """
        OpenVPN command: last 2 statuses
        """
        return self._send_command("status 2")

    #
    # parse  info as the UI expects
    #

    def get_status_io(self):
        status = self.vpn_status()
        if isinstance(status, str):
            lines = status.split('\n')
        if isinstance(status, list):
            lines = status
        try:
            (header, when, tun_read, tun_write,
             tcp_read, tcp_write, auth_read) = tuple(lines)
        except ValueError:
            return None

        when_ts = dateparse(when.split(',')[1]).timetuple()
        sep = ','
        # XXX clean up this!
        tun_read = tun_read.split(sep)[1]
        tun_write = tun_write.split(sep)[1]
        tcp_read = tcp_read.split(sep)[1]
        tcp_write = tcp_write.split(sep)[1]
        auth_read = auth_read.split(sep)[1]

        # XXX this could be a named tuple. prettier.
        return when_ts, (tun_read, tun_write, tcp_read, tcp_write, auth_read)

    def get_connection_state(self):
        state = self.state()
        if state is not None:
            ts, status_step, ok, ip, remote = state.split(',')
            ts = time.gmtime(float(ts))
            # XXX this could be a named tuple. prettier.
            return ts, status_step, ok, ip, remote


class EIPConnection(OpenVPNConnection, StatusMixIn):
    """
    Aka conductor.
    Manages the execution of the OpenVPN process, auto starts, monitors the
    network connection, handles configuration, fixes leaky hosts, handles
    errors, etc.
    Status updates (connected, bandwidth, etc) are signaled to the GUI.
    """

    # XXX change name to EIPConductor ??

    def __init__(self,
                 provider_cert_checker=ProviderCertChecker,
                 config_checker=EIPConfigChecker,
                 *args, **kwargs):
        #self.settingsfile = kwargs.get('settingsfile', None)
        #self.logfile = kwargs.get('logfile', None)
        self.provider = kwargs.pop('provider', None)
        self._providercertchecker = provider_cert_checker
        self._configchecker = config_checker

        self.error_queue = Queue.Queue()

        status_signals = kwargs.pop('status_signals', None)
        self.status = EIPConnectionStatus(callbacks=status_signals)

        checker_signals = kwargs.pop('checker_signals', None)
        self.checker_signals = checker_signals

        self.init_checkers()

        host = eipconfig.get_socket_path()
        kwargs['host'] = host

        super(EIPConnection, self).__init__(*args, **kwargs)

    def connect(self):
        """
        entry point for connection process
        """
        # in OpenVPNConnection
        self.try_openvpn_connection()

    def disconnect(self, shutdown=False):
        """
        disconnects client
        """
        self.terminate_openvpn_connection(shutdown=shutdown)
        self.status.change_to(self.status.DISCONNECTED)

    def has_errors(self):
        return True if self.error_queue.qsize() != 0 else False

    def init_checkers(self):
        """
        initialize checkers
        """
        self.provider_cert_checker = self._providercertchecker(
            domain=self.provider)
        self.config_checker = self._configchecker(domain=self.provider)

    def set_provider_domain(self, domain):
        """
        sets the provider domain.
        used from the first run wizard when we launch the run_checks
        and connect process after having initialized the conductor.
        """
        # This looks convoluted, right.
        # We have to reinstantiate checkers cause we're passing
        # the domain param that we did not know at the beginning
        # (only for the firstrunwizard case)
        self.provider = domain
        self.init_checkers()

    def run_checks(self, skip_download=False, skip_verify=False):
        """
        run all eip checks previous to attempting a connection
        """
        logger.debug('running conductor checks')

        def push_err(exc):
            # keep the original traceback!
            exc_traceback = sys.exc_info()[2]
            self.error_queue.put((exc, exc_traceback))

        try:
            # network (1)
            if self.checker_signals:
                for signal in self.checker_signals:
                    signal('checking encryption keys')
            self.provider_cert_checker.run_all(skip_verify=skip_verify)
        except Exception as exc:
            push_err(exc)
        try:
            if self.checker_signals:
                for signal in self.checker_signals:
                    signal('checking provider config')
            self.config_checker.run_all(skip_download=skip_download)
        except Exception as exc:
            push_err(exc)
        try:
            self.run_openvpn_checks()
        except Exception as exc:
            push_err(exc)


class EIPConnectionStatus(object):
    """
    Keep track of client (gui) and openvpn
    states.

    These are the OpenVPN states:
    CONNECTING    -- OpenVPN's initial state.
    WAIT          -- (Client only) Waiting for initial response
                     from server.
    AUTH          -- (Client only) Authenticating with server.
    GET_CONFIG    -- (Client only) Downloading configuration options
                     from server.
    ASSIGN_IP     -- Assigning IP address to virtual network
                     interface.
    ADD_ROUTES    -- Adding routes to system.
    CONNECTED     -- Initialization Sequence Completed.
    RECONNECTING  -- A restart has occurred.
    EXITING       -- A graceful exit is in progress.

    We add some extra states:

    DISCONNECTED  -- GUI initial state.
    UNRECOVERABLE -- An unrecoverable error has been raised
                     while invoking openvpn service.
    """
    CONNECTING = 1
    WAIT = 2
    AUTH = 3
    GET_CONFIG = 4
    ASSIGN_IP = 5
    ADD_ROUTES = 6
    CONNECTED = 7
    RECONNECTING = 8
    EXITING = 9

    # gui specific states:
    UNRECOVERABLE = 11
    DISCONNECTED = 0

    def __init__(self, callbacks=None):
        """
        EIPConnectionStatus is initialized with a tuple
        of signals to be triggered.
        :param callbacks: a tuple of (callable) observers
        :type callbacks: tuple
        """
        self.current = self.DISCONNECTED
        self.previous = None
        # (callbacks to connect to signals in Qt-land)
        self.callbacks = callbacks

    def get_readable_status(self):
        # XXX DRY status / labels a little bit.
        # think we'll want to i18n this.
        human_status = {
            0: 'disconnected',
            1: 'connecting',
            2: 'waiting',
            3: 'authenticating',
            4: 'getting config',
            5: 'assigning ip',
            6: 'adding routes',
            7: 'connected',
            8: 'reconnecting',
            9: 'exiting',
            11: 'unrecoverable error',
        }
        return human_status[self.current]

    def get_leap_status(self):
        # XXX improve nomenclature
        leap_status = {
            0: 'disconnected',
            1: 'connecting to gateway',
            2: 'connecting to gateway',
            3: 'authenticating',
            4: 'establishing network encryption',
            5: 'establishing network encryption',
            6: 'establishing network encryption',
            7: 'connected',
            8: 'reconnecting',
            9: 'exiting',
            11: 'unrecoverable error',
        }
        return leap_status[self.current]

    def get_state_icon(self):
        """
        returns the high level icon
        for each fine-grain openvpn state
        """
        connecting = (self.CONNECTING,
                      self.WAIT,
                      self.AUTH,
                      self.GET_CONFIG,
                      self.ASSIGN_IP,
                      self.ADD_ROUTES)
        connected = (self.CONNECTED,)
        disconnected = (self.DISCONNECTED,
                        self.UNRECOVERABLE)

        # this can be made smarter,
        # but it's like it'll change,
        # so +readability.

        if self.current in connecting:
            return "connecting"
        if self.current in connected:
            return "connected"
        if self.current in disconnected:
            return "disconnected"

    def set_vpn_state(self, status):
        """
        accepts a state string from the management
        interface, and sets the internal state.
        :param status: openvpn STATE (uppercase).
        :type status: str
        """
        if hasattr(self, status):
            self.change_to(getattr(self, status))

    def set_current(self, to):
        """
        setter for the 'current' property
        :param to: destination state
        :type to: int
        """
        self.current = to

    def change_to(self, to):
        """
        :param to: destination state
        :type to: int
        """
        if to == self.current:
            return
        changed = False
        from_ = self.current
        self.current = to

        # We can add transition restrictions
        # here to ensure no transitions are
        # allowed outside the fsm.

        self.set_current(to)
        changed = True

        #trigger signals (as callbacks)
        #print('current state: %s' % self.current)
        if changed:
            self.previous = from_
            if self.callbacks:
                for cb in self.callbacks:
                    if callable(cb):
                        cb(self)
