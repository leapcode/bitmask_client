from __future__ import (print_function)
import logging
import os
import socket
import telnetlib
import time

logger = logging.getLogger(name=__name__)
logger.setLevel('DEBUG')

TELNET_PORT = 23


class MissingSocketError(Exception):
    pass


class ConnectionRefusedError(Exception):
    pass


class UDSTelnet(telnetlib.Telnet):

    def open(self, host, port=0, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        """Connect to a host. If port is 'unix', it
        will open a connection over unix docmain sockets.

        The optional second argument is the port number, which
        defaults to the standard telnet port (23).

        Don't try to reopen an already connected instance.
        """
        self.eof = 0
        if not port:
            port = TELNET_PORT
        self.host = host
        self.port = port
        self.timeout = timeout

        if self.port == "unix":
            # unix sockets spoken
            if not os.path.exists(self.host):
                raise MissingSocketError
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self.sock.connect(self.host)
            except socket.error:
                raise ConnectionRefusedError
        else:
            self.sock = socket.create_connection((host, port), timeout)


# this class based in code from cube-routed project

class OpenVPNManager(object):
    """
    Run commands over OpenVPN management interface
    and parses the output.
    """
    # XXX might need a lock to avoid
    # race conditions here...

    def __init__(self, host="/tmp/.eip.sock", port="unix", password=None):
        #XXX hardcoded host here. change.
        self.host = host
        if isinstance(port, str) and port.isdigit():
            port = int(port)
        self.port = port
        self.password = password
        self.tn = None

        #XXX workaround for signaling
        #the ui that we don't know how to
        #manage a connection error
        self.with_errors = False

    def forget_errors(self):
        logger.debug('forgetting errors')
        self.with_errors = False

    def connect(self):
        """Connect to openvpn management interface"""
        try:
            self.close()
        except:
            #XXX don't like this general
            #catch here.
            pass
        if self.connected():
            return True
        self.tn = UDSTelnet(self.host, self.port)

        # XXX make password optional
        # specially for win plat. we should generate
        # the pass on the fly when invoking manager
        # from conductor

        #self.tn.read_until('ENTER PASSWORD:', 2)
        #self.tn.write(self.password + '\n')
        #self.tn.read_until('SUCCESS:', 2)

        self._seek_to_eof()
        self.forget_errors()
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
        #return bool(getattr(self, 'tn', None))
        try:
            assert self.tn
            return True
        except:
            #XXX get rid of
            #this pokemon exception!!!
            return False

    def close(self, announce=True):
        """
        Close connection to openvpn management interface
        """
        if announce:
            self.tn.write("quit\n")
            self.tn.read_all()
        self.tn.get_socket().close()
        del self.tn

    def _send_command(self, cmd, tries=0):
        """
        Send a command to openvpn and return response as list
        """
        if tries > 3:
            return []
        if not self.connected():
            try:
                self.connect()
            except MissingSocketError:
                #XXX capture more helpful error
                #messages
                #pass
                return self.make_error()
        try:
            self.tn.write(cmd + "\n")
        except socket.error:
            logger.error('socket error')
            print('socket error!')
            self.close(announce=False)
            self._send_command(cmd, tries=tries + 1)
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

    def status(self):
        """
        OpenVPN command: status
        """
        status = self._send_command("status")
        return status

    def status2(self):
        """
        OpenVPN command: last 2 statuses
        """
        return self._send_command("status 2")

    #
    # parse  info
    #

    def get_status_io(self):
        status = self.status()
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
