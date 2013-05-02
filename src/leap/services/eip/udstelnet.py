# -*- coding: utf-8 -*-
# udstelnet.py
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

import os
import socket
import telnetlib


class ConnectionRefusedError(Exception):
    pass


class MissingSocketError(Exception):
    pass


class UDSTelnet(telnetlib.Telnet):
    """
    A telnet-alike class, that can listen on unix domain sockets
    """

    def open(self, host, port=23, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        """
        Connect to a host. If port is 'unix', it will open a
        connection over unix docmain sockets.

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
                raise MissingSocketError()
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                self.sock.connect(self.host)
            except socket.error:
                raise ConnectionRefusedError()
        else:
            self.sock = socket.create_connection((host, port), timeout)
