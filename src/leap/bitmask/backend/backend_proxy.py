# -*- coding: utf-8 -*-
# backend_proxy.py
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
The BackendProxy handles calls from the GUI and forwards (through ZMQ)
to the backend.
"""
# XXX should document the relationship to the API here.

import functools
import Queue
import threading
import time

import zmq

from leap.bitmask.backend.api import API, STOP_REQUEST, PING_REQUEST
from leap.bitmask.backend.settings import Settings
from leap.bitmask.backend.utils import generate_zmq_certificates_if_needed
from leap.bitmask.backend.utils import get_backend_certificates
from leap.bitmask.config import flags

import logging
logger = logging.getLogger(__name__)


class BackendProxy(object):
    """
    The BackendProxy handles calls from the GUI and forwards (through ZMQ)
    to the backend.
    """

    if flags.ZMQ_HAS_CURVE:
        PORT = '5556'
        SERVER = "tcp://localhost:%s" % PORT
    else:
        SERVER = "ipc:///tmp/bitmask.socket.0"

    POLL_TIMEOUT = 4000  # ms
    POLL_TRIES = 3

    PING_INTERVAL = 2  # secs

    def __init__(self):
        generate_zmq_certificates_if_needed()

        self._socket = None

        self.settings = Settings()

        # initialize ZMQ stuff:
        context = zmq.Context()
        logger.debug("Connecting to server...")
        socket = context.socket(zmq.REQ)

        if flags.ZMQ_HAS_CURVE:
            # public, secret = zmq.curve_keypair()
            client_keys = zmq.curve_keypair()
            socket.curve_publickey = client_keys[0]
            socket.curve_secretkey = client_keys[1]

            # The client must know the server's public key to make a CURVE
            # connection.
            public, _ = get_backend_certificates()
            socket.curve_serverkey = public

        socket.setsockopt(zmq.RCVTIMEO, 1000)
        socket.setsockopt(zmq.LINGER, 0)  # Terminate early
        socket.connect(self.SERVER)
        self._socket = socket

        self._ping_at = 0
        self.online = False

        self._call_queue = Queue.Queue()
        self._worker_caller = threading.Thread(target=self._worker)

    def start(self):
        self._worker_caller.start()

    def check_online(self):
        """
        Return whether the backend is accessible or not.
        You don't need to do `run` in order to use this.

        :rtype: bool
        """
        # we use a small timeout in order to response quickly if the backend is
        # offline
        self._send_request(PING_REQUEST, retry=False, timeout=500)
        self._socket.close()
        return self.online

    def _worker(self):
        """
        Worker loop that processes the Queue of pending requests to do.
        """
        while True:
            try:
                request = self._call_queue.get(block=False)
                # break the loop after sending the 'stop' action to the
                # backend.
                if request == STOP_REQUEST:
                    break

                self._send_request(request)
            except Queue.Empty:
                pass
            time.sleep(0.01)
            self._ping()

        logger.debug("BackendProxy worker stopped.")

    def _reset_ping(self):
        """
        Reset the ping timeout counter.
        This is called for every ping and request.
        """
        self._ping_at = time.time() + self.PING_INTERVAL

    def _ping(self):
        """
        Heartbeat helper.
        Sends a PING request just to know that the server is alive.
        """
        if time.time() > self._ping_at:
            self._send_request(PING_REQUEST)
            self._reset_ping()

    def _api_call(self, *args, **kwargs):
        """
        Call the `api_method` method in backend (through zmq).

        :param kwargs: named arguments to forward to the backend api method.
        :type kwargs: dict

        Note: is mandatory to have the kwarg 'api_method' defined.
        """
        if args:
            # Use a custom message to be more clear about using kwargs *only*
            raise Exception("All arguments need to be kwargs!")

        api_method = kwargs.pop('api_method', None)
        if api_method is None:
            raise Exception("Missing argument, no method name specified.")

        request = {
            'api_method': api_method,
            'arguments': kwargs,
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
        self._call_queue.put(request_json)

        if api_method == STOP_REQUEST:
            self._call_queue.put(STOP_REQUEST)

    def _send_request(self, request, retry=True, timeout=None):
        """
        Send the given request to the server.
        This is used from a thread safe loop in order to avoid sending a
        request without receiving a response from a previous one.

        :param request: the request to send.
        :type request: str
        :param retry: whether we should retry or not in case of timeout.
        :type retry: bool
        :param timeout: a custom timeout (milliseconds) to wait for a response.
        :type timeout: int
        """
        # logger.debug("Sending request to backend: {0}".format(request))
        self._socket.send(request)

        poll = zmq.Poller()
        poll.register(self._socket, zmq.POLLIN)

        reply = None

        tries = 0
        if not retry:
            tries = self.POLL_TRIES + 1  # this means: no retries left

        if timeout is None:
            timeout = self.POLL_TIMEOUT

        while True:
            socks = dict(poll.poll(timeout))
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
            self.online = False
        else:
            # msg = "Received reply for '{0}' -> '{1}'".format(request, reply)
            # logger.debug(msg)
            self.online = True
            # request received, no ping needed for other interval.
            self._reset_ping()

    def __getattribute__(self, name):
        """
        This allows the user to do:
            bp = BackendProxy()
            bp.some_method()

        Just by having defined 'some_method' in the API

        :param name: the attribute name that is requested.
        :type name: str
        """
        if name in API:
            return functools.partial(self._api_call, api_method=name)
        else:
            return object.__getattribute__(self, name)
