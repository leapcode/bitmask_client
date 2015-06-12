# -*- coding: utf-8 -*-
# backend.py
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

# FIXME this is missing module documentation. It would be fine to say a couple
# of lines about the whole backend architecture.
import json
import os
import time

import psutil

from twisted.internet import defer, reactor, threads, task

import txzmq
import zmq
try:
    from zmq.auth.thread import ThreadAuthenticator
except ImportError:
    pass

from leap.bitmask.backend.api import API, PING_REQUEST
from leap.bitmask.backend.signaler import Signaler
from leap.bitmask.backend.utils import get_backend_certificates
from leap.bitmask.config import flags
from leap.bitmask.logs.utils import get_logger

logger = get_logger()


class TxZmqREPConnection(object):
    """
    A twisted based zmq rep connection.
    """

    def __init__(self, server_address, process_request):
        """
        Initialize the connection.

        :param server_address: The address of the backend zmq server.
        :type server: str
        :param process_request: A callable used to process incoming requests.
        :type process_request: callable(messageParts)
        """
        self._server_address = server_address
        self._process_request = process_request
        self._zmq_factory = None
        self._zmq_connection = None
        self._init_txzmq()

    def _init_txzmq(self):
        """
        Configure the txzmq components and connection.
        """
        self._zmq_factory = txzmq.ZmqFactory()
        self._zmq_factory.registerForShutdown()
        self._zmq_connection = txzmq.ZmqREPConnection(self._zmq_factory)

        context = self._zmq_factory.context
        socket = self._zmq_connection.socket

        def _gotMessage(messageId, messageParts):
            self._zmq_connection.reply(messageId, "OK")
            self._process_request(messageParts)

        self._zmq_connection.gotMessage = _gotMessage

        if flags.ZMQ_HAS_CURVE:
            # Start an authenticator for this context.
            auth = ThreadAuthenticator(context)
            auth.start()
            # XXX do not hardcode this here.
            auth.allow('127.0.0.1')

            # Tell authenticator to use the certificate in a directory
            auth.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)
            public, secret = get_backend_certificates()
            socket.curve_publickey = public
            socket.curve_secretkey = secret
            socket.curve_server = True  # must come before bind

        proto, addr = self._server_address.split('://')  # tcp/ipc, ip/socket
        socket.bind(self._server_address)
        if proto == 'ipc':
            os.chmod(addr, 0600)


class Backend(object):
    """
    Backend server.
    Receives signals from backend_proxy and emit signals if needed.
    """
    # XXX we might want to make this configurable per-platform,
    # and use the most performant socket type on each one.
    if flags.ZMQ_HAS_CURVE:
        # XXX this should not be hardcoded. Make it configurable.
        PORT = '5556'
        BIND_ADDR = "tcp://127.0.0.1:%s" % PORT
    else:
        SOCKET_FILE = "/tmp/bitmask.socket.0"
        BIND_ADDR = "ipc://%s" % SOCKET_FILE

    PING_INTERVAL = 2  # secs

    def __init__(self, frontend_pid=None):
        """
        Backend constructor, create needed instances.
        """
        self._signaler = Signaler()
        self._frontend_pid = frontend_pid
        self._frontend_checker = None
        self._ongoing_defers = []
        self._zmq_connection = TxZmqREPConnection(
            self.BIND_ADDR, self._process_request)

    def _check_frontend_alive(self):
        """
        Check if the frontend is alive and stop the backend if it is not.
        """
        pid = self._frontend_pid
        if pid is not None and not psutil.pid_exists(pid):
            logger.critical("The frontend is down!")
            self.stop()

    def _stop_reactor(self):
        """
        Stop the Twisted reactor, but first wait a little for some threads to
        complete their work.

        Note: this method needs to be run in a different thread so the
        time.sleep() does not block and other threads can finish.
        i.e.:
            use threads.deferToThread(this_method) instead of this_method()
        """
        wait_max = 3  # seconds
        wait_step = 0.5
        wait = 0
        while self._ongoing_defers and wait < wait_max:
            time.sleep(wait_step)
            wait += wait_step
            msg = "Waiting for running threads to finish... {0}/{1}"
            msg = msg.format(wait, wait_max)
            logger.debug(msg)

        # after a timeout we shut down the existing threads.
        for d in self._ongoing_defers:
            d.cancel()

        logger.debug("Stopping the Twisted reactor...")
        reactor.stop()

    def run(self):
        """
        Start the ZMQ server and run the loop to handle requests.
        """
        self._signaler.start()
        self._frontend_checker = task.LoopingCall(self._check_frontend_alive)
        self._frontend_checker.start(self.PING_INTERVAL)
        logger.debug("Starting Twisted reactor.")
        reactor.run()
        logger.debug("Finished Twisted reactor.")

    def stop(self):
        """
        Stop the server and the zmq request parse loop.
        """
        logger.debug("Stopping the backend...")
        self._signaler.stop()
        self._frontend_checker.stop()
        threads.deferToThread(self._stop_reactor)

    def _process_request(self, request_json):
        """
        Process a request and call the according method with the given
        parameters.

        :param request_json: a json specification of a request.
        :type request_json: str
        """
        if request_json == PING_REQUEST:
            # do not process request if it's just a ping
            return

        try:
            # request = zmq.utils.jsonapi.loads(request_json)
            # We use stdlib's json to ensure that we get unicode strings
            request = json.loads(request_json)
            api_method = request['api_method']
            kwargs = request['arguments'] or None
        except Exception as e:
            msg = "Malformed JSON data in Backend request '{0}'. Exc: {1!r}"
            msg = msg.format(request_json, e)
            msg = msg.format(request_json)
            logger.critical(msg)
            raise

        if api_method not in API:
            logger.error("Invalid API call '{0}'".format(api_method))
            return

        self._run_in_thread(api_method, kwargs)

    def _run_in_thread(self, api_method, kwargs):
        """
        Run the method name in a thread with the given arguments.

        :param api_method: the callable name to run in a thread.
        :type api_method: str
        :param kwargs: the arguments dict that will be sent to the callable.
        :type kwargs: tuple
        """
        func = getattr(self, api_method)

        method = func
        if kwargs is not None:
            method = lambda: func(**kwargs)

        # logger.debug("Running method: '{0}' "
        #            "with args: '{1}' in a thread".format(api_method, kwargs))

        # run the action in a thread and keep track of it
        d = threads.deferToThread(method)
        d.addCallback(self._done_action, d)
        d.addErrback(self._done_action, d)
        self._ongoing_defers.append(d)

    def _done_action(self, failure, d):
        """
        Remove the defer from the ongoing list.

        :param failure: the failure that triggered the errback.
                        None if no error.
        :type failure: twisted.python.failure.Failure
        :param d: defer to remove
        :type d: twisted.internet.defer.Deferred
        """
        if failure is not None:
            if failure.check(defer.CancelledError):
                logger.debug("A defer was cancelled.")
            else:
                logger.error("There was a failure - {0!r}".format(failure))
                logger.error(failure.getTraceback())

        if d in self._ongoing_defers:
            self._ongoing_defers.remove(d)
