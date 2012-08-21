"""
OpenVPN Connection
"""
from __future__ import (print_function)
import logging
import socket
import time
from functools import partial

logging.basicConfig()
logger = logging.getLogger(name=__name__)
logger.setLevel(logging.DEBUG)

from leap.base.connection import Connection
from leap.util.coroutines import spawn_and_watch_process

from leap.eip.udstelnet import UDSTelnet
from leap.eip import config as eip_config
from leap.eip import exceptions as eip_exceptions


class OpenVPNConnection(Connection):
    """
    All related to invocation
    of the openvpn binary
    """
    # Connection Methods

    def __init__(self, config_file=None,
                 watcher_cb=None,
                 debug=False,
                 host="/tmp/.eip.sock",
                 port="unix",
                 password=None,
                 *args, **kwargs):
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
        self.bad_keyfile_perms = False
        self.missing_vpn_keyfile = False
        self.missing_provider = False
        self.bad_provider = False

        #XXX workaround for signaling
        #the ui that we don't know how to
        #manage a connection error
        self.with_errors = False

        self.command = None
        self.args = None

        self.autostart = True
        self._get_or_create_config()
        self._check_vpn_keys()

        #
        # management init methods
        #

        self.host = host
        if isinstance(port, str) and port.isdigit():
            port = int(port)
        elif port == "unix":
            port = "unix"
        else:
            port = None
        self.port = port
        self.password = password

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
                command, args = eip_config.build_ovpn_command(
                    config,
                    debug=self.debug)
            except eip_exceptions.EIPNoPolkitAuthAgentAvailable:
                command = args = None
                self.missing_auth_agent = True
            except eip_exceptions.EIPNoPkexecAvailable:
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
        try:
            eip_config.check_or_create_default_vpnconf(self.config)
        except eip_exceptions.EIPInitNoProviderError:
            logger.error('missing default provider definition')
            self.missing_provider = True
        except eip_exceptions.EIPInitBadProviderError:
            logger.error('bad provider definition')
            self.bad_provider = True

    def _get_or_create_config(self):
        """
        retrieves the config options from defaults or
        home file, or config file passed in command line.
        populates command and args to be passed to subprocess.
        """
        config = eip_config.get_config(
            config_file=self.config_file)
        self.config = config

        self._set_autostart()
        self._set_ovpn_command()
        self._check_ovpn_config()

    def _check_vpn_keys(self):
        """
        checks for correct permissions on vpn keys
        """
        try:
            eip_config.check_vpn_keys(self.config)
        except eip_exceptions.EIPInitNoKeyFileError:
            self.missing_vpn_keyfile = True
        except eip_exceptions.EIPInitBadKeyFilePermError:
            logger.error('error while checking vpn keys')
            self.bad_keyfile_perms = True

    def _launch_openvpn(self):
        """
        invocation of openvpn binaries in a subprocess.
        """
        #XXX TODO:
        #deprecate watcher_cb,
        #use _only_ signal_maps instead

        logger.debug('_launch_openvpn called')
        if self.watcher_cb is not None:
            linewrite_callback = self.watcher_cb
        else:
            #XXX get logger instead
            linewrite_callback = lambda line: print('watcher: %s' % line)

        # the partial is not
        # being applied now because we're not observing the process
        # stdout like we did in the early stages. but I leave it
        # here since it will be handy for observing patterns in the
        # thru-the-manager updates (with regex)
        observers = (linewrite_callback,
                     partial(lambda con_status, line: None, self.status))
        subp, watcher = spawn_and_watch_process(
            self.command,
            self.args,
            observers=observers)
        self.subp = subp
        self.watcher = watcher

    def _try_connection(self):
        """
        attempts to connect
        """
        if self.command is None:
            raise eip_exceptions.EIPNoCommandError
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

    #
    # management methods
    #
    # XXX REVIEW-ME
    # REFACTOR INFO: (former "manager".
    # Can we move to another
    # base class to test independently?)
    #

    def forget_errors(self):
        print('forgetting errors')
        self.with_errors = False

    def connect_to_management(self):
        """Connect to openvpn management interface"""
        #logger.debug('connecting socket')
        if hasattr(self, 'tn'):
            self.close()
        self.tn = UDSTelnet(self.host, self.port)

        # XXX make password optional
        # specially for win. we should generate
        # the pass on the fly when invoking manager
        # from conductor

        #self.tn.read_until('ENTER PASSWORD:', 2)
        #self.tn.write(self.password + '\n')
        #self.tn.read_until('SUCCESS:', 2)

        self._seek_to_eof()
        #self.forget_errors()
        return True

    def _seek_to_eof(self):
        """
        Read as much as available. Position seek pointer to end of stream
        """
        b = self.tn.read_eager()
        while b:
            b = self.tn.read_eager()

    def connected(self):
        """
        Returns True if connected
        rtype: bool
        """
        return hasattr(self, 'tn')

    def close(self, announce=True):
        """
        Close connection to openvpn management interface
        """
        logger.debug('closing socket')
        if announce:
            self.tn.write("quit\n")
            self.tn.read_all()
        self.tn.get_socket().close()
        del self.tn

    def _send_command(self, cmd):
        """
        Send a command to openvpn and return response as list
        """
        #logger.debug('connected? %s' % self.connected())
        if not self.connected():
            try:
                #logger.debug('try to connect')
                self.connect_to_management()
            except eip_exceptions.MissingSocketError:
                #XXX capture more helpful error
                return self.make_error()
            except:
                raise
        try:
            if hasattr(self, 'tn'):
                self.tn.write(cmd + "\n")
        except socket.error:
            logger.error('socket error')
            self.close(announce=False)
            return []
        buf = self.tn.read_until(b"END", 2)
        self._seek_to_eof()
        blist = buf.split('\r\n')
        if blist[-1].startswith('END'):
            del blist[-1]
            return blist
        else:
            return []

    def _send_short_command(self, cmd):
        """
        parse output from commands that are
        delimited by "success" instead
        """
        if not self.connected():
            self.connect()
        self.tn.write(cmd + "\n")
        # XXX not working?
        buf = self.tn.read_until(b"SUCCESS", 2)
        self._seek_to_eof()
        blist = buf.split('\r\n')
        return blist

    #
    # useful vpn commands
    #

    def pid(self):
        #XXX broken
        return self._send_short_command("pid")

    def make_error(self):
        """
        capture error and wrap it in an
        understandable format
        """
        #XXX get helpful error codes
        self.with_errors = True
        now = int(time.time())
        return '%s,LAUNCHER ERROR,ERROR,-,-' % now

    def state(self):
        """
        OpenVPN command: state
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
    # parse  info
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

        when_ts = time.strptime(when.split(',')[1], "%a %b %d %H:%M:%S %Y")
        sep = ','
        # XXX cleanup!
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
