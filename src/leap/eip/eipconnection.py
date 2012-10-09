"""
EIP Connection Class
"""
from __future__ import (absolute_import,)
import logging
import Queue
import sys

from leap.eip.checks import ProviderCertChecker
from leap.eip.checks import EIPConfigChecker
from leap.eip import config as eipconfig
from leap.eip import exceptions as eip_exceptions
from leap.eip.openvpnconnection import OpenVPNConnection

logger = logging.getLogger(name=__name__)


class EIPConnection(OpenVPNConnection):
    """
    Manages the execution of the OpenVPN process, auto starts, monitors the
    network connection, handles configuration, fixes leaky hosts, handles
    errors, etc.
    Status updates (connected, bandwidth, etc) are signaled to the GUI.
    """

    def __init__(self,
                 provider_cert_checker=ProviderCertChecker,
                 config_checker=EIPConfigChecker,
                 *args, **kwargs):
        self.settingsfile = kwargs.get('settingsfile', None)
        self.logfile = kwargs.get('logfile', None)

        self.error_queue = Queue.Queue()

        status_signals = kwargs.pop('status_signals', None)
        self.status = EIPConnectionStatus(callbacks=status_signals)

        checker_signals = kwargs.pop('checker_signals', None)
        self.checker_signals = checker_signals

        self.provider_cert_checker = provider_cert_checker()
        self.config_checker = config_checker()

        host = eipconfig.get_socket_path()
        kwargs['host'] = host

        super(EIPConnection, self).__init__(*args, **kwargs)

    def has_errors(self):
        return True if self.error_queue.qsize() != 0 else False

    def run_checks(self, skip_download=False, skip_verify=False):
        """
        run all eip checks previous to attempting a connection
        """
        logger.debug('running conductor checks')
        print 'conductor checks!'

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

    def connect(self):
        """
        entry point for connection process
        """
        self.forget_errors()
        self._try_connection()

    def disconnect(self):
        """
        disconnects client
        """
        self._disconnect()
        self.status.change_to(self.status.DISCONNECTED)

    def shutdown(self):
        """
        shutdown and quit
        """
        self.desired_con_state = self.status.DISCONNECTED

    def connection_state(self):
        """
        returns the current connection state
        """
        return self.status.current

    def poll_connection_state(self):
        """
        """
        # XXX this separation does not
        # make sense anymore after having
        # merged Connection and Manager classes.
        # XXX GET RID OF THIS FUNCTION HERE!
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

    def get_icon_name(self):
        """
        get icon name from status object
        """
        return self.status.get_state_icon()

    def get_leap_status(self):
        return self.status.get_leap_status()

    #
    # private methods
    #

    def _disconnect(self):
        """
        private method for disconnecting
        """
        if self.subp is not None:
            logger.debug('disconnecting...')
            self.subp.terminate()
            self.subp = None

    #def _is_alive(self):
        #"""
        #don't know yet
        #"""
        #pass

    def _connect(self):
        """
        entry point for connection cascade methods.
        """
        try:
            conn_result = self._try_connection()
        except eip_exceptions.UnrecoverableError as except_msg:
            logger.error("FATAL: %s" % unicode(except_msg))
            conn_result = self.status.UNRECOVERABLE

        # XXX enqueue exceptions themselves instead?
        except Exception as except_msg:
            self.error_queue.append(except_msg)
            logger.error("Failed Connection: %s" %
                         unicode(except_msg))
        return conn_result


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
