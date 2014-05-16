# -*- coding: utf-8 -*-
# abstractbootstrapper.py
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

"""
Abstract bootstrapper implementation
"""
import logging

import requests

from functools import partial

from PySide import QtCore

from twisted.python import log
from twisted.internet import threads
from twisted.internet.defer import CancelledError

from leap.common.check import leap_assert, leap_assert_type

logger = logging.getLogger(__name__)


class AbstractBootstrapper(QtCore.QObject):
    """
    Abstract Bootstrapper that implements the needed deferred callbacks
    """

    PASSED_KEY = "passed"
    ERROR_KEY = "error"

    def __init__(self, signaler=None, bypass_checks=False):
        """
        Constructor for the abstract bootstrapper

        :param signaler: Signaler object used to receive notifications
                         from the backend
        :type signaler: Signaler
        :param bypass_checks: Set to true if the app should bypass
                              first round of checks for CA
                              certificates at bootstrap
        :type bypass_checks: bool
        """
        QtCore.QObject.__init__(self)

        leap_assert(self._gui_errback.im_func ==
                    AbstractBootstrapper._gui_errback.im_func,
                    "Cannot redefine _gui_errback")
        leap_assert(self._errback.im_func ==
                    AbstractBootstrapper._errback.im_func,
                    "Cannot redefine _errback")
        leap_assert(self._gui_notify.im_func ==
                    AbstractBootstrapper._gui_notify.im_func,
                    "Cannot redefine _gui_notify")

        # **************************************************** #
        # Dependency injection helpers, override this for more
        # granular testing
        self._fetcher = requests
        # **************************************************** #

        self._session = self._fetcher.session()
        self._bypass_checks = bypass_checks
        self._signal_to_emit = None
        self._err_msg = None
        self._signaler = signaler
        self._cancel_signal = None

    def _gui_errback(self, failure):
        """
        Errback used to notify the GUI of a problem, it should be used
        as the last errback of the whole chain.

        Traps all exceptions if a signal is defined, otherwise it just
        lets it continue.

        NOTE: This method is final, it should not be redefined.

        :param failure: failure object that Twisted generates
        :type failure: twisted.python.failure.Failure
        """
        if failure.check(CancelledError):
            logger.debug("Defer cancelled.")
            failure.trap(Exception)
            if self._signaler is not None and self._cancel_signal is not None:
                self._signaler.signal(self._cancel_signal)
            return

        if self._signal_to_emit:
            err_msg = self._err_msg \
                if self._err_msg is not None \
                else str(failure.value)
            data = {
                self.PASSED_KEY: False,
                self.ERROR_KEY: err_msg
            }
            # TODO: Remove this check when all the bootstrappers are
            # in the backend form
            if isinstance(self._signal_to_emit, basestring):
                if self._signaler is not None:
                    self._signaler.signal(self._signal_to_emit, data)
                else:
                    logger.warning("Tried to notify but no signaler found")
            else:
                self._signal_to_emit.emit(data)
            log.err(failure)
            failure.trap(Exception)

    def _errback(self, failure, signal=None):
        """
        Regular errback used for the middle of the chain. If it's
        executed, the first one will set the signal to emit as
        failure.

        NOTE: This method is final, it should not be redefined.

        :param failure: failure object that Twisted generates
        :type failure: twisted.python.failure.Failure
        :param signal: Signal to emit if it fails here first
        :type signal: QtCore.SignalInstance

        :returns: failure object that Twisted generates
        :rtype: twisted.python.failure.Failure
        """
        if self._signal_to_emit is None:
            self._signal_to_emit = signal
        return failure

    def _gui_notify(self, _, signal=None):
        """
        Callback used to notify the GUI of a success. Will emit signal
        if specified

        NOTE: This method is final, it should not be redefined.

        :param _: IGNORED. Returned from the previous callback
        :type _: IGNORED
        :param signal: Signal to emit if it fails here first
        :type signal: QtCore.SignalInstance
        """
        if signal is not None:
            data = {self.PASSED_KEY: True, self.ERROR_KEY: ""}
            if isinstance(signal, basestring):
                if self._signaler is not None:
                    self._signaler.signal(signal, data)
                else:
                    logger.warning("Tried to notify but no signaler found")
            else:
                signal.emit(data)

    def _callback_threader(self, cb, res, *args, **kwargs):
        return threads.deferToThread(cb, res, *args, **kwargs)

    def addCallbackChain(self, callbacks):
        """
        Creates a callback/errback chain on another thread using
        deferToThread and adds the _gui_errback to the end to notify
        the GUI on an error.

        :param callbacks: List of tuples of callbacks and the signal
                          associated to that callback
        :type callbacks: list(tuple(func, func))

        :returns: the defer with the callback chain
        :rtype: deferred
        """
        leap_assert_type(callbacks, list)

        self._signal_to_emit = None
        self._err_msg = None

        d = None
        for cb, sig in callbacks:
            if d is None:
                d = threads.deferToThread(cb)
            else:
                d.addCallback(partial(self._callback_threader, cb))
            d.addErrback(self._errback, signal=sig)
            d.addCallback(self._gui_notify, signal=sig)
        d.addErrback(self._gui_errback)
        return d
