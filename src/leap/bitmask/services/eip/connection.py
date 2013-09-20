# -*- coding: utf-8 -*-
# connection.py
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
EIP Connection
"""
from PySide import QtCore

from leap.bitmask.services.connections import AbstractLEAPConnection


class EIPConnectionSignals(QtCore.QObject):
    """
    Qt Signals used by EIPConnection
    """
    # commands
    do_connect_signal = QtCore.Signal()
    do_disconnect_signal = QtCore.Signal()

    # intermediate stages
    # this is currently binded to mainwindow._start_eip
    connecting_signal = QtCore.Signal()
    # this is currently binded to mainwindow._stop_eip
    disconnecting_signal = QtCore.Signal()

    connected_signal = QtCore.Signal()
    disconnected_signal = QtCore.Signal()

    connection_died_signal = QtCore.Signal()


class EIPConnection(AbstractLEAPConnection):

    def __init__(self):
        self._qtsigs = EIPConnectionSignals()
