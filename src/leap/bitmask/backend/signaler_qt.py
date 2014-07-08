#!/usr/bin/env python
# encoding: utf-8
import threading
import time

from PySide import QtCore

import zmq
from zmq.auth.thread import ThreadAuthenticator

from leap.bitmask.backend.api import SIGNALS
from leap.bitmask.backend.utils import get_frontend_certificates

import logging
logger = logging.getLogger(__name__)


class SignalerQt(QtCore.QThread):
    """
    Signaling server.
    Receives signals from the signaling client and emit Qt signals for the GUI.
    """
    PORT = "5667"
    BIND_ADDR = "tcp://127.0.0.1:%s" % PORT

    def __init__(self):
        QtCore.QThread.__init__(self)
        self._do_work = threading.Event()
        self._do_work.set()

    def run(self):
        """
        Start a loop to process the ZMQ requests from the signaler client.
        """
        logger.debug("Running SignalerQt loop")
        context = zmq.Context()
        socket = context.socket(zmq.REP)

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

        while self._do_work.is_set():
            # Wait for next request from client
            try:
                request = socket.recv(zmq.NOBLOCK)
                logger.debug("Received request: '{0}'".format(request))
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

        logger.debug("Emitting '{0}'".format(signal))
        if data is None:
            qt_signal.emit()
        else:
            qt_signal.emit(data)
