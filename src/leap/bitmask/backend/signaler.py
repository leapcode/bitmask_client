# -*- coding: utf-8 -*-
# signaler.py
# Copyright (C) 2013, 2014 LEAP
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
Signaler client.
Receives signals from the backend and sends to the signaling server.
"""
import Queue
import threading
import time

import zmq

from leap.bitmask.backend.api import SIGNALS
from leap.bitmask.backend.utils import get_frontend_certificates
from leap.bitmask.config import flags
from leap.bitmask.logs.utils import get_logger

logger = get_logger()


class Signaler(object):
    """
    Signaler client.
    Receives signals from the backend and sends to the signaling server.
    """
    if flags.ZMQ_HAS_CURVE:
        PORT = "5667"
        SERVER = "tcp://localhost:%s" % PORT
    else:
        SERVER = "ipc:///tmp/bitmask.socket.1"
    POLL_TIMEOUT = 2000  # ms
    POLL_TRIES = 500

    def __init__(self):
        """
        Initialize the ZMQ socket to talk to the signaling server.
        """
        context = zmq.Context()
        logger.debug("Connecting to signaling server...")
        socket = context.socket(zmq.REQ)

        if flags.ZMQ_HAS_CURVE:
            # public, secret = zmq.curve_keypair()
            client_keys = zmq.curve_keypair()
            socket.curve_publickey = client_keys[0]
            socket.curve_secretkey = client_keys[1]

            # The client must know the server's public key to make a CURVE
            # connection.
            public, _ = get_frontend_certificates()
            socket.curve_serverkey = public

        socket.setsockopt(zmq.RCVTIMEO, 1000)
        socket.setsockopt(zmq.LINGER, 0)  # Terminate early
        socket.connect(self.SERVER)
        self._socket = socket

        self._signal_queue = Queue.Queue()

        self._do_work = threading.Event()  # used to stop the worker thread.
        self._worker_signaler = threading.Thread(target=self._worker)

    def __getattribute__(self, name):
        """
        This allows the user to do:
            S = Signaler()
            S.SOME_SIGNAL

        Just by having defined 'some_signal' in _SIGNALS

        :param name: the attribute name that is requested.
        :type name: str
        """
        if name in SIGNALS:
            return name
        else:
            return object.__getattribute__(self, name)

    def signal(self, signal, data=None):
        """
        Sends a signal to the signaling server.

        :param signal: the signal to send.
        :type signal: str
        """
        if signal not in SIGNALS:
            raise Exception("Unknown signal: '{0}'".format(signal))

        request = {
            'signal': signal,
            'data': data,
        }

        try:
            request_json = zmq.utils.jsonapi.dumps(request)
        except Exception as e:
            msg = ("Error serializing request into JSON.\n"
                   "Exception: {0} Data: {1}")
            msg = msg.format(e, request)
            logger.critical(msg)
            raise

        # queue the call in order to handle the request in a thread safe way.
        self._signal_queue.put(request_json)

    def _worker(self):
        """
        Worker loop that processes the Queue of pending requests to do.
        """
        while self._do_work.is_set():
            try:
                request = self._signal_queue.get(block=False)
                self._send_request(request)
            except Queue.Empty:
                pass
            time.sleep(0.01)

        logger.debug("Signaler thread stopped.")

    def start(self):
        """
        Start the Signaler worker.
        """
        self._do_work.set()
        self._worker_signaler.start()

    def stop(self):
        """
        Stop the Signaler worker.
        """
        self._do_work.clear()

    def _send_request(self, request):
        """
        Send the given request to the server.
        This is used from a thread safe loop in order to avoid sending a
        request without receiving a response from a previous one.

        :param request: the request to send.
        :type request: str
        """
        # logger.debug("Signaling '{0}'".format(request))
        self._socket.send(request)

        poll = zmq.Poller()
        poll.register(self._socket, zmq.POLLIN)

        reply = None
        tries = 0

        while True:
            socks = dict(poll.poll(self.POLL_TIMEOUT))
            if socks.get(self._socket) == zmq.POLLIN:
                reply = self._socket.recv()
                break

            tries += 1
            if tries < self.POLL_TRIES:
                logger.warning('Retrying receive... {0}/{1}'.format(
                    tries, self.POLL_TRIES))
            else:
                break

        if reply is None:
            msg = "Timeout error contacting backend."
            logger.critical(msg)
        # else:
        #     msg = "Received reply for '{0}' -> '{1}'".format(request, reply)
        #     logger.debug(msg)
