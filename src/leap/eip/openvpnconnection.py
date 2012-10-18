"""
OpenVPN Connection
"""
from __future__ import (print_function)
import logging
import psutil
import socket
import time
from functools import partial

logger = logging.getLogger(name=__name__)

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

    def __init__(self,
                 #config_file=None,
                 watcher_cb=None,
                 debug=False,
                 host=None,
                 port="unix",
                 password=None,
                 *args, **kwargs):
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
        #XXX FIXME
        #change watcher_cb to line_observer

        logger.debug('init openvpn connection')
        self.debug = debug
        # XXX if not host: raise ImproperlyConfigured
        self.ovpn_verbosity = kwargs.get('ovpn_verbosity', None)

        #self.config_file = config_file
        self.watcher_cb = watcher_cb
        #self.signal_maps = signal_maps

        self.subp = None
        self.watcher = None

        self.server = None
        self.port = None
        self.proto = None

        #XXX workaround for signaling
        #the ui that we don't know how to
        #manage a connection error
        #self.with_errors = False

        self.command = None
        self.args = None

        # XXX get autostart from config
        self.autostart = True

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

    def run_openvpn_checks(self):
        logger.debug('running openvpn checks')
        self._check_if_running_instance()
        self._set_ovpn_command()
        self._check_vpn_keys()

    def _set_ovpn_command(self):
        # XXX check also for command-line --command flag
        try:
            command, args = eip_config.build_ovpn_command(
                debug=self.debug,
                socket_path=self.host,
                ovpn_verbosity=self.ovpn_verbosity)
        except eip_exceptions.EIPNoPolkitAuthAgentAvailable:
            command = args = None
            raise
        except eip_exceptions.EIPNoPkexecAvailable:
            command = args = None
            raise

        # XXX if not command, signal error.
        self.command = command
        self.args = args

    def _check_vpn_keys(self):
        """
        checks for correct permissions on vpn keys
        """
        try:
            eip_config.check_vpn_keys()
        except eip_exceptions.EIPInitBadKeyFilePermError:
            logger.error('Bad VPN Keys permission!')
            # do nothing now
        # and raise the rest ...

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
            logger.debug('cowardly refusing to launch subprocess again')

        self._launch_openvpn()

    def _check_if_running_instance(self):
        """
        check if openvpn is already running
        """
        for process in psutil.get_process_list():
            if process.name == "openvpn":
                logger.debug('an openvpn instance is already running.')
                logger.debug('attempting to stop openvpn instance.')
                if not self._stop():
                    raise eip_exceptions.OpenVPNAlreadyRunning

        logger.debug('no openvpn instance found.')

    def cleanup(self):
        """
        terminates openvpn child subprocess
        """
        if self.subp:
            self._stop()

            # XXX kali --
            # I think this will block if child process
            # does not return.
            # Maybe we can .poll() for a given
            # interval and exit in any case.

            RETCODE = self.subp.wait()
            if RETCODE:
                logger.error(
                    'cannot terminate subprocess! '
                    '(We might have left openvpn running)')

    def _get_openvpn_process(self):
        # plist = [p for p in psutil.get_process_list() if p.name == "openvpn"]
        # return plist[0] if plist else None
        for process in psutil.get_process_list():
            if process.name == "openvpn":
                return process
        return None

    # management methods
    #
    # XXX REVIEW-ME
    # REFACTOR INFO: (former "manager".
    # Can we move to another
    # base class to test independently?)
    #

    #def forget_errors(self):
        #logger.debug('forgetting errors')
        #self.with_errors = False

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
        return True

    def _seek_to_eof(self):
        """
        Read as much as available. Position seek pointer to end of stream
        """
        try:
            b = self.tn.read_eager()
        except EOFError:
            logger.debug("Could not read from socket. Assuming it died.")
            return
        while b:
            try:
                b = self.tn.read_eager()
            except EOFError:
                logger.debug("Could not read from socket. Assuming it died.")

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
        if not self.connected():
            try:
                self.connect_to_management()
            except eip_exceptions.MissingSocketError:
                logger.warning('missing management socket')
                return []
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
        #logger.debug('status called')
        status = self._send_command("status")
        return status

    def vpn_status2(self):
        """
        OpenVPN command: last 2 statuses
        """
        return self._send_command("status 2")

    def _stop(self):
        """
        stop openvpn process
        by sending SIGTERM to the management
        interface
        """
        logger.debug("disconnecting...")
        self._send_command("signal SIGTERM\n")

        if self.subp:
            return True

        #shutting openvpn failured
        #try patching in old openvpn host and trying again
        process = self._get_openvpn_process()
        if process:
            self.host = \
                process.cmdline[process.cmdline.index("--management") + 1]
            self._send_command("signal SIGTERM\n")

            #make sure the process was terminated
            process = self._get_openvpn_process()
            if not process:
                logger.debug("Existing OpenVPN Process Terminated")
                return True
            else:
                logger.error("Unable to terminate existing OpenVPN Process.")
                return False

        return True

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
