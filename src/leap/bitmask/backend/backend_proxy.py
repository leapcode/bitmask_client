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
import threading

import zmq
from zmq.eventloop import ioloop
from zmq.eventloop import zmqstream

from taskthread import TimerTask

from leap.bitmask.backend.api import API, STOP_REQUEST, PING_REQUEST
from leap.bitmask.backend.settings import Settings
from leap.bitmask.backend.utils import generate_zmq_certificates_if_needed
from leap.bitmask.backend.utils import get_backend_certificates
from leap.bitmask.config import flags

import logging
logger = logging.getLogger(__name__)


class ZmqREQConnection(threading.Thread):
    """
    A threaded zmq req connection.
    """

    def __init__(self, server_address, on_recv):
        """
        Initialize the connection.

        :param server_address: The address of the backend zmq server.
        :type server: str
        :param on_recv: The callback to be executed when a message is
            received.
        :type on_recv: callable(msg)
        """
        threading.Thread.__init__(self)
        self._server_address = server_address
        self._on_recv = on_recv
        self._stream = None
        self._init_zmq()

    def _init_zmq(self):
        """
        Configure the zmq components and connection.
        """
        logger.debug("Setting up ZMQ connection to server...")
        context = zmq.Context()
        socket = context.socket(zmq.REQ)

        # we use zmq's eventloop in order to asynchronously send requests
        loop = ioloop.ZMQIOLoop.current()
        self._stream = zmqstream.ZMQStream(socket, loop)

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

        self._stream.on_recv(self._on_recv)

    def run(self):
        """
        Run the threaded stream connection loop.
        """
        self._stream.socket.connect(self._server_address)
        logger.debug("Starting ZMQ loop.")
        self._stream.io_loop.start()
        logger.debug("Finished ZMQ loop.")

    def stop(self):
        """
        Stop the threaded connection loop.
        """
        self._stream.io_loop.stop()

    def send(self, *args, **kwargs):
        """
        Send a message through this connection.
        """
        # Important note: calling send on the zmqstream from another
        # thread doesn’t properly tell the IOLoop thread that there’s an
        # event to process. This could cuase small delays if the IOLoop is
        # already processing lots of events, but it can cause the message
        # to never send if the zmq socket is the only one it’s handling.
        #
        # Because of that, we want ZmqREQConnection.send to hand off the
        # stream.send to the IOLoop’s thread via IOLoop.add_callback:
        self._stream.io_loop.add_callback(
            lambda: self._stream.send(*args, **kwargs))


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

    PING_INTERVAL = 2  # secs

    def __init__(self):
        """
        Initialize the backend proxy.
        """
        generate_zmq_certificates_if_needed()
        self._do_work = threading.Event()
        self._work_lock = threading.Lock()
        self._connection = ZmqREQConnection(self.SERVER, self._set_online)
        self._heartbeat = TimerTask(self._ping, delay=self.PING_INTERVAL)
        self._ping_event = threading.Event()
        self.online = False
        self.settings = Settings()

    def _set_online(self, _):
        """
        Mark the backend as being online.

        This is used as the zmq connection's on_recv callback, and so it is
        passed the received message as a parameter. Because we currently don't
        use that message, we just ignore it for now.
        """
        self.online = True
        # the following event is used when checking whether the backend is
        # online
        self._ping_event.set()

    def _set_offline(self):
        """
        Mark the backend as being offline.
        """
        self.online = False

    def check_online(self):
        """
        Return whether the backend is accessible or not.
        You don't need to do `run` in order to use this.
        :rtype: bool
        """
        logger.debug("Checking whether backend is online...")
        self._send_request(PING_REQUEST)
        # self._ping_event will eventually be set by the zmq connection's
        # on_recv callback, so we use a small timeout in order to response
        # quickly if the backend is offline
        if not self._ping_event.wait(0.5):
            logger.warning("Backend is offline!")
            self._set_offline()
        return self.online

    def start(self):
        """
        Start the backend proxy.
        """
        logger.debug("Starting backend proxy...")
        self._do_work.set()
        self._connection.start()
        self.check_online()
        self._heartbeat.start()

    def _stop(self):
        """
        Stop the backend proxy.
        """
        with self._work_lock:  # avoid sending after connection was closed
            self._do_work.clear()
            self._heartbeat.stop()
        self._connection.stop()
        logger.debug("BackendProxy worker stopped.")

    def _ping(self):
        """
        Heartbeat helper.
        Sends a PING request just to know that the server is alive.
        """
        self._send_request(PING_REQUEST)

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

        request_json = None

        try:
            request_json = zmq.utils.jsonapi.dumps(request)
        except Exception as e:
            msg = ("Error serializing request into JSON.\n"
                   "Exception: {0} Data: {1}")
            msg = msg.format(e, request)
            logger.critical(msg)
            raise

        # queue the call in order to handle the request in a thread safe way.
        self._send_request(request_json)

        if api_method == STOP_REQUEST:
            self._stop()

    def _send_request(self, request):
        """
        Send the given request to the server.
        This is used from a thread safe loop in order to avoid sending a
        request without receiving a response from a previous one.

        :param request: the request to send.
        :type request: str
        """
        with self._work_lock:  # avoid sending after connection was closed
            if self._do_work.is_set():
                self._connection.send(request)

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
