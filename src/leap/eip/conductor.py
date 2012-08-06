"""
stablishes a vpn connection and monitors its state
"""
from __future__ import (division, unicode_literals, print_function)
#import threading
from functools import partial
import logging
import os

from leap.util.coroutines import spawn_and_watch_process


from leap.eip.config import (get_config, build_ovpn_command,
                             check_or_create_default_vpnconf,
                             EIPNoPkexecAvailable,
                             EIPNoPolkitAuthAgentAvailable)
from leap.eip.vpnwatcher import EIPConnectionStatus, status_watcher
from leap.eip.vpnmanager import OpenVPNManager, ConnectionRefusedError

logger = logging.getLogger(name=__name__)


# TODO Move exceptions to their own module

class EIPNoCommandError(Exception):
    pass


class ConnectionError(Exception):
    """
    generic connection error
    """
    pass


class EIPClientError(Exception):
    """
    base EIPClient exception
    """
    def __str__(self):
        if len(self.args) >= 1:
            return repr(self.args[0])
        else:
            return ConnectionError


class UnrecoverableError(EIPClientError):
    """
    we cannot do anything about it, sorry
    """
    # XXX we should catch this and raise
    # to qtland, so we emit signal
    # to translate whatever kind of error
    # to user-friendly msg in dialog.
    pass

#
# Openvpn related classes
#


class OpenVPNConnection(object):
    """
    All related to invocation
    of the openvpn binary
    """
    # Connection Methods

    def __init__(self, config_file=None,
                 watcher_cb=None, debug=False):
        #XXX FIXME
        #change watcher_cb to line_observer
        """
        :param config_file: configuration file to read from
        :param watcher_cb: callback to be \
called for each line in watched stdout
        :param signal_map: dictionary of signal names and callables \
to be triggered for each one of them.
        :type config_file: str
        :type watcher_cb: function
        :type signal_map: dict
        """
        # XXX get host/port from config
        self.manager = OpenVPNManager()
        self.debug = debug
        #print('conductor:%s' % debug)

        self.config_file = config_file
        self.watcher_cb = watcher_cb
        #self.signal_maps = signal_maps

        self.subp = None
        self.watcher = None

        self.server = None
        self.port = None
        self.proto = None

        self.missing_pkexec = False
        self.missing_auth_agent = False
        self.command = None
        self.args = None

        self.autostart = True
        self._get_or_create_config()

    def _set_autostart(self):
        config = self.config
        if config.has_option('openvpn', 'autostart'):
            autostart = config.getboolean('openvpn',
                                          'autostart')
            self.autostart = autostart
        else:
            if config.has_option('DEFAULT', 'autostart'):
                autostart = config.getboolean('DEFAULT',
                                              'autostart')
                self.autostart = autostart

    def _set_ovpn_command(self):
        config = self.config
        if config.has_option('openvpn', 'command'):
            commandline = config.get('openvpn', 'command')

            command_split = commandline.split(' ')
            command = command_split[0]
            if len(command_split) > 1:
                args = command_split[1:]
            else:
                args = []

            self.command = command
            self.args = args
        else:
        # no command in config, we build it up.
        # XXX check also for command-line --command flag
            try:
                command, args = build_ovpn_command(config,
                                                   debug=self.debug)
            except EIPNoPolkitAuthAgentAvailable:
                command = args = None
                self.missing_auth_agent = True
            except EIPNoPkexecAvailable:
                command = args = None
                self.missing_pkexec = True

            # XXX if not command, signal error.
            self.command = command
            self.args = args

    def _check_ovpn_config(self):
        """
        checks if there is a default openvpn config.
        if not, it writes one with info from the provider
        definition file
        """
        # TODO
        # - get --with-openvpn-config from opts
        check_or_create_default_vpnconf(self.config)

    def _get_or_create_config(self):
        """
        retrieves the config options from defaults or
        home file, or config file passed in command line.
        populates command and args to be passed to subprocess.
        """
        config = get_config(config_file=self.config_file)
        self.config = config

        self._set_autostart()
        self._set_ovpn_command()
        self._check_ovpn_config()

    def _launch_openvpn(self):
        """
        invocation of openvpn binaries in a subprocess.
        """
        #XXX TODO:
        #deprecate watcher_cb,
        #use _only_ signal_maps instead

        if self.watcher_cb is not None:
            linewrite_callback = self.watcher_cb
        else:
            #XXX get logger instead
            linewrite_callback = lambda line: print('watcher: %s' % line)

        observers = (linewrite_callback,
                     partial(status_watcher, self.status))
        subp, watcher = spawn_and_watch_process(
            self.command,
            self.args,
            observers=observers)
        self.subp = subp
        self.watcher = watcher

        #conn_result = self.status.CONNECTED
        #return conn_result

    def _try_connection(self):
        """
        attempts to connect
        """
        if self.command is None:
            raise EIPNoCommandError
        if self.subp is not None:
            print('cowardly refusing to launch subprocess again')
            return
        self._launch_openvpn()

    def cleanup(self):
        """
        terminates child subprocess
        """
        if self.subp:
            self.subp.terminate()


class EIPConductor(OpenVPNConnection):
    """
    Manages the execution of the OpenVPN process, auto starts, monitors the
    network connection, handles configuration, fixes leaky hosts, handles
    errors, etc.
    Preferences will be stored via the Storage API. (TBD)
    Status updates (connected, bandwidth, etc) are signaled to the GUI.
    """

    def __init__(self, *args, **kwargs):
        self.settingsfile = kwargs.get('settingsfile', None)
        self.logfile = kwargs.get('logfile', None)
        self.error_queue = []
        self.desired_con_state = None  # ???

        status_signals = kwargs.pop('status_signals', None)
        self.status = EIPConnectionStatus(callbacks=status_signals)

        super(EIPConductor, self).__init__(*args, **kwargs)

    def connect(self):
        """
        entry point for connection process
        """
        self.manager.forget_errors()
        self._try_connection()
        # XXX should capture errors here?

    def disconnect(self):
        """
        disconnects client
        """
        self._disconnect()
        self.status.change_to(self.status.DISCONNECTED)

    def poll_connection_state(self):
        """
        """
        try:
            state = self.manager.get_connection_state()
        except ConnectionRefusedError:
            # connection refused. might be not ready yet.
            return
        if not state:
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

    #
    # private methods
    #

    def _disconnect(self):
        """
        private method for disconnecting
        """
        if self.subp is not None:
            self.subp.terminate()
            self.subp = None
        # XXX signal state changes! :)

    def _is_alive(self):
        """
        don't know yet
        """
        pass

    def _connect(self):
        """
        entry point for connection cascade methods.
        """
        #conn_result = ConState.DISCONNECTED
        try:
            conn_result = self._try_connection()
        except UnrecoverableError as except_msg:
            logger.error("FATAL: %s" % unicode(except_msg))
            conn_result = self.status.UNRECOVERABLE
        except Exception as except_msg:
            self.error_queue.append(except_msg)
            logger.error("Failed Connection: %s" %
                         unicode(except_msg))
        return conn_result
