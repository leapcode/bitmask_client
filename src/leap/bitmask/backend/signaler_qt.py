# -*- coding: utf-8 -*-
# signaler_qt.py
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
Signaling server.
Receives signals from the signaling client and emit Qt signals for the GUI.
"""
import os
import threading
import time

from PySide import QtCore

import zmq
try:
    from zmq.auth.thread import ThreadAuthenticator
except ImportError:
    pass

from leap.bitmask.backend.api import SIGNALS
from leap.bitmask.backend.utils import get_frontend_certificates
from leap.bitmask.config import flags
from leap.bitmask.logs.utils import get_logger

logger = get_logger()


class SignalerQt(QtCore.QObject):
    """
    Signaling server.
    Receives signals from the signaling client and emit Qt signals for the GUI.
    """
    if flags.ZMQ_HAS_CURVE:
        PORT = "5667"
        BIND_ADDR = "tcp://127.0.0.1:%s" % PORT
    else:
        SOCKET_FILE = "/tmp/bitmask.socket.1"
        BIND_ADDR = "ipc://%s" % SOCKET_FILE

    def __init__(self):
        QtCore.QObject.__init__(self)

        # Note: we use a plain thread instead of a QThread since works better.
        # The signaler was not responding on OSX if the worker loop was run in
        # a QThread.
        # Possibly, ZMQ was not getting cycles to do work because Qt not
        # receiving focus or something.
        self._worker_thread = threading.Thread(target=self._run)
        self._do_work = threading.Event()

    def start(self):
        """
        Start the worker thread for the signaler server.
        """
        self._do_work.set()
        self._worker_thread.start()

    def _run(self):
        """
        Start a loop to process the ZMQ requests from the signaler client.
        """
        logger.debug("Running SignalerQt loop")
        context = zmq.Context()
        socket = context.socket(zmq.REP)

        if flags.ZMQ_HAS_CURVE:
            # Start an authenticator for this context.
            auth = ThreadAuthenticator(context)
            auth.start()
            auth.allow('127.0.0.1')

            # Tell authenticator to use the certificate in a directory
            auth.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)
            public, secret = get_frontend_certificates()
            socket.curve_publickey = public
            socket.curve_secretkey = secret
            socket.curve_server = True  # must come before bind

        socket.bind(self.BIND_ADDR)

        if not flags.ZMQ_HAS_CURVE:
            os.chmod(self.SOCKET_FILE, 0600)

        while self._do_work.is_set():
            # Wait for next request from client
            try:
                request = socket.recv(zmq.NOBLOCK)
                # logger.debug("Received request: '{0}'".format(request))
                socket.send("OK")
                self._process_request(request)
            except zmq.ZMQError as e:
                if e.errno != zmq.EAGAIN:
                    raise
            time.sleep(0.01)

        logger.debug("SignalerQt thread stopped.")

    def stop(self):
        """
        Stop the SignalerQt blocking loop.
        """
        self._do_work.clear()

    def _process_request(self, request_json):
        """
        Process a request and call the according method with the given
        parameters.

        :param request_json: a json specification of a request.
        :type request_json: str
        """
        try:
            request = zmq.utils.jsonapi.loads(request_json)
            signal = request['signal']
            data = request['data']
        except Exception as e:
            msg = "Malformed JSON data in Signaler request '{0}'. Exc: {1!r}"
            msg = msg.format(request_json, e)
            logger.critical(msg)
            raise

        if signal not in SIGNALS:
            logger.error("Unknown signal received, '{0}'".format(signal))
            return

        try:
            qt_signal = getattr(self, signal)
        except Exception:
            logger.warning("Signal not implemented, '{0}'".format(signal))
            return

        # logger.debug("Emitting '{0}'".format(signal))
        if data is None:
            qt_signal.emit()
        else:
            qt_signal.emit(data)
