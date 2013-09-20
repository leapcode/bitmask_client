# -*- coding: utf-8 -*-
# connections.py
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
Abstract LEAP connections.
"""
# TODO use zope.interface instead
from abc import ABCMeta

from PySide import QtCore

from leap.common.check import leap_assert

_tr = QtCore.QObject().tr


class State(object):
    """
    Abstract state class
    """
    __metaclass__ = ABCMeta

    label = None
    short_label = None

"""
The different services should declare a ServiceConnection class that
inherits from AbstractLEAPConnection, so an instance of such class
can be used to inform the StateMachineBuilder of the particularities
of the state transitions for each particular connection.

In the future, we will extend this class to allow composites in connections,
so we can apply conditional logic to the transitions.
"""


class AbstractLEAPConnection(object):
    """
    Abstract LEAP Connection class.

    This class is likely to undergo heavy transformations
    in the coming releases, to better accomodate the use cases
    of the different connections that we use in the Bitmask
    client.
    """
    __metaclass__ = ABCMeta

    _connection_name = None

    @property
    def name(self):
        """
        Name of the connection
        """
        con_name = self._connection_name
        leap_assert(con_name is not None)
        return con_name

    _qtsigs = None

    @property
    def qtsigs(self):
        """
        Object that encapsulates the Qt Signals emitted
        by this connection.
        """
        return self._qtsigs

    # XXX for conditional transitions with composites,
    #     we might want to add
    #     a field with dependencies: what this connection
    #     needs for (ON) state.
    # XXX Look also at child states in the state machine.
    #depends = ()

    # Signals that derived classes
    # have to implement.

    # Commands
    do_connect_signal = None
    do_disconnect_signal = None

    # Intermediate stages
    connecting_signal = None
    disconnecting_signal = None

    # Complete stages
    connected_signal = None
    disconnected_signal = None

    # Bypass stages
    connection_died_signal = None

    class Disconnected(State):
        """Disconnected state"""
        label = _tr("Disconnected")
        short_label = _tr("OFF")

    class Connected(State):
        """Connected state"""
        label = _tr("Connected")
        short_label = _tr("ON")

    class Connecting(State):
        """Connecting state"""
        label = _tr("Connecting")
        short_label = _tr("...")

    class Disconnecting(State):
        """Disconnecting state"""
        label = _tr("Disconnecting")
        short_label = _tr("...")
