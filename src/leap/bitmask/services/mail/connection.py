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
Email Connections
"""
from PySide import QtCore

from leap.bitmask.services.connections import AbstractLEAPConnection


class IMAPConnectionSignals(QtCore.QObject):
    """
    Qt Signals used by IMAPConnection
    """
    # commands
    do_connect_signal = QtCore.Signal()
    do_disconnect_signal = QtCore.Signal()

    # intermediate stages
    connecting_signal = QtCore.Signal()
    disconnecting_signal = QtCore.Signal()

    connected_signal = QtCore.Signal()
    disconnected_signal = QtCore.Signal()

    connection_died_signal = QtCore.Signal()
    connection_aborted_signal = QtCore.Signal()


class IMAPConnection(AbstractLEAPConnection):

    _connection_name = "IMAP"

    def __init__(self):
        self._qtsigs = IMAPConnectionSignals()


class SMTPConnectionSignals(QtCore.QObject):
    """
    Qt Signals used by SMTPConnection
    """
    # commands
    do_connect_signal = QtCore.Signal()
    do_disconnect_signal = QtCore.Signal()

    # intermediate stages
    connecting_signal = QtCore.Signal()
    disconnecting_signal = QtCore.Signal()

    connected_signal = QtCore.Signal()
    disconnected_signal = QtCore.Signal()

    connection_died_signal = QtCore.Signal()
    connection_aborted_signal = QtCore.Signal()


class SMTPConnection(AbstractLEAPConnection):

    _connection_name = "IMAP"

    def __init__(self):
        self._qtsigs = SMTPConnectionSignals()


class MailConnectionSignals(QtCore.QObject):
    """
    Qt Signals used by MailConnection
    """
    # commands
    do_connect_signal = QtCore.Signal()
    do_disconnect_signal = QtCore.Signal()

    connecting_signal = QtCore.Signal()
    disconnecting_signal = QtCore.Signal()

    connected_signal = QtCore.Signal()
    disconnected_signal = QtCore.Signal()

    connection_died_signal = QtCore.Signal()
    connection_aborted_signal = QtCore.Signal()


class MailConnection(AbstractLEAPConnection):

    components = IMAPConnection, SMTPConnection
    _connection_name = "Mail"

    def __init__(self):
        self._qtsigs = MailConnectionSignals()
