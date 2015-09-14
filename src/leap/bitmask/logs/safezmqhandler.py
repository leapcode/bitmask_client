# -*- coding: utf-8 -*-
# safezmqhandler.py
# Copyright (C) 2013, 2014, 2015 LEAP
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
A thread-safe zmq handler for LogBook.
"""
import json
import threading

from logbook.queues import ZeroMQHandler
from logbook import NOTSET

import zmq


class SafeZMQHandler(ZeroMQHandler):
    """
    A ZMQ log handler for LogBook that is thread-safe.

    This log handler makes use of the existing zmq handler and if the user
    tries to log something from a different thread than the one used to
    create the handler a new socket is created for that thread.

    Note: In ZMQ, Contexts are threadsafe objects, but Sockets are not.
    """

    def __init__(self, uri=None, level=NOTSET, filter=None, bubble=False,
                 context=None, multi=False):
        """
        Safe zmq handler constructor that calls the ZeroMQHandler constructor
        and does some extra initializations.
        """
        # The current `SafeZMQHandler` uses the `ZeroMQHandler` constructor
        # which creates a socket each time.
        # The purpose of the `self._sockets` attribute is to prevent cases in
        # which we use the same logger in different threads. For instance when
        # we (in the same file) `deferToThread` a method/function, we are using
        # the same logger/socket without calling get_logger again.
        # If we want to reuse the socket, we need to rewrite this constructor
        # instead of calling the ZeroMQHandler's one.
        # The best approach may be to inherit directly from `logbook.Handler`.

        args = (self, uri, level, filter, bubble, context, multi)
        ZeroMQHandler.__init__(*args)

        current_id = self._get_caller_id()
        # we store the socket created on the parent
        self._sockets = {current_id: self.socket}

        # store the settings for new socket creation
        self._multi = multi
        self._uri = uri

    def _get_caller_id(self):
        """
        Return an id for the caller that depends on the current thread.
        Thanks to this we can detect if we are running in a thread different
        than the one who created the socket and create a new one for it.

        :rtype: int
        """
        # NOTE it makes no sense to use multiprocessing id since the sockets
        # list can't/shouldn't be shared between processes. We only use
        # thread id. The user needs to make sure that the handler is created
        # inside each process.
        return threading.current_thread().ident

    def _get_new_socket(self):
        """
        Return a new socket using the `uri` and `multi` parameters given in the
        constructor.

        :rtype: zmq.Socket
        """
        socket = None

        if self._multi:
            socket = self.context.socket(zmq.PUSH)
            if self._uri is not None:
                socket.connect(self._uri)
        else:
            socket = self.context.socket(zmq.PUB)
            if self._uri is not None:
                socket.bind(self._uri)

        return socket

    def emit(self, record):
        """
        Emit the given `record` through the socket.

        :param record: the record to emit
        :type record: Logbook.LogRecord
        """
        current_id = self._get_caller_id()
        socket = None

        if current_id in self._sockets:
            socket = self._sockets[current_id]
        else:
            # TODO: create new socket
            socket = self._get_new_socket()
            self._sockets[current_id] = socket

        socket.send(json.dumps(self.export_record(record)).encode("utf-8"))

    def close(self, linger=-1):
        """
        Close all the sockets and linger `linger` time.

        This reimplements the ZeroMQHandler.close method that is used by
        context methods.

        :param linger: time to linger, -1 to not to.
        :type linger: int
        """
        for socket in self._sockets.values():
            socket.close(linger)
