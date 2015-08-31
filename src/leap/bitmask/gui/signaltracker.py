# -*- coding: utf-8 -*-
# signaltracker.py
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
from PySide import QtCore

from leap.bitmask.logs.utils import get_logger

logger = get_logger()


class SignalTracker(QtCore.QObject):
    """
    A class meant to be inherited from that helps to do the Qt connect and keep
    track of the connections made, allowing to disconnect those tracked signals
    as well.
    """
    def __init__(self):
        # this list contains the connected signals that we want to keep track.
        # each item of the list is a:
        # tuple of (Qt signal, callable or Qt slot or Qt signal)
        self._connected_signals = []

    def connect_and_track(self, signal, method):
        """
        Connect the signal and keep track of it.

        :param signal: the signal to connect to.
        :type signal: QtCore.Signal
        :param method: the method to call when the signal is triggered.
        :type method: callable, Slot or Signal
        """
        if (signal, method) in self._connected_signals:
            logger.warning("Signal already connected.")
            return

        self._connected_signals.append((signal, method))
        signal.connect(method)

    def disconnect_and_untrack(self):
        """
        Disconnect all the tracked signals.
        """
        for signal, method in self._connected_signals:
            try:
                signal.disconnect(method)
            except (TypeError, RuntimeError) as e:
                logger.warning("Disconnect error: {0!r}".format(e))
                logger.warning("Signal: {0!r} -> {1!r}".format(signal, method))

        self._connected_signals = []
