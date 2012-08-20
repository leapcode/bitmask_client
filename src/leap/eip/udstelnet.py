import os
import socket
import telnetlib

from leap.eip import exceptions as eip_exceptions


class UDSTelnet(telnetlib.Telnet):
    """
    a telnet-alike class, that can listen
    on unix domain sockets
    """

    def open(self, host, port=23, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        """Connect to a host. If port is 'unix', it
        will open a connection over unix docmain sockets.

        The optional second argument is the port number, which
        defaults to the standard telnet port (23).

        Don't try to reopen an already connected instance.
        """
        self.eof = 0
        self.host = host
        self.port = port
        self.timeout = timeout

        if self.port == "unix":
            # unix sockets spoken
            if not os.path.exists(self.host):
                raise eip_exceptions.MissingSocketError
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self.sock.connect(self.host)
            except socket.error:
                raise eip_exceptions.ConnectionRefusedError
        else:
            self.sock = socket.create_connection((host, port), timeout)
