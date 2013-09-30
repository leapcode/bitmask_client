# -*- coding: utf-8 -*-
# statemachines.py
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
State machines for the Bitmask app.
"""
import logging

from PySide.QtCore import QStateMachine, QState
from PySide.QtCore import QObject

from leap.bitmask.services import connections
from leap.common.check import leap_assert_type

logger = logging.getLogger(__name__)

_tr = QObject().tr

# Indexes for the state dict
_ON = "on"
_OFF = "off"
_CON = "connecting"
_DIS = "disconnecting"


class IntermediateState(QState):
    """
    Intermediate state that emits a custom signal on entry
    """
    def __init__(self, signal):
        """
        Initializer.
        :param signal: the signal to be emitted on entry on this state.
        :type signal: QtCore.QSignal
        """
        super(IntermediateState, self).__init__()
        self._signal = signal

    def onEntry(self, *args):
        """
        Emits the signal on entry.
        """
        logger.debug('IntermediateState entered. Emitting signal ...')
        if self._signal is not None:
            self._signal.emit()


class ConnectionMachineBuilder(object):
    """
    Builder class for state machines made from LEAPConnections.
    """
    def __init__(self, connection):
        """
        :param connection: an instance of a concrete LEAPConnection
                      we will be building a state machine for.
        :type connection: AbstractLEAPConnection
        """
        self._conn = connection
        leap_assert_type(self._conn, connections.AbstractLEAPConnection)

    def make_machine(self, button=None, action=None, label=None):
        """
        Creates a statemachine associated with the passed controls.

        :param button: the switch button.
        :type button: QPushButton

        :param action: the actionh that controls connection switch in a menu.
        :type action: QAction

        :param label: the label that displays the connection state
        :type label: QLabel

        :returns: a state machine
        :rtype: QStateMachine
        """
        machine = QStateMachine()
        conn = self._conn

        states = self._make_states(button, action, label)

        # transitions:

        states[_OFF].addTransition(
            conn.qtsigs.do_connect_signal,
            states[_CON])

        # * Clicking the buttons or actions transitions to the
        #   intermediate stage.
        if button:
            states[_OFF].addTransition(
                button.clicked,
                states[_CON])
            states[_ON].addTransition(
                button.clicked,
                states[_DIS])

        if action:
            states[_OFF].addTransition(
                action.triggered,
                states[_CON])
            states[_ON].addTransition(
                action.triggered,
                states[_DIS])

        # * We transition to the completed stages when
        #   we receive the matching signal from the underlying
        #   conductor.

        states[_CON].addTransition(
            conn.qtsigs.connected_signal,
            states[_ON])
        states[_DIS].addTransition(
            conn.qtsigs.disconnected_signal,
            states[_OFF])

        # * If we receive the connection_died, we transition
        #   from on directly to the off state
        states[_ON].addTransition(
            conn.qtsigs.connection_died_signal,
            states[_OFF])

        # * If we receive the connection_aborted, we transition
        #   from connecting to the off state
        states[_CON].addTransition(
            conn.qtsigs.connection_aborted_signal,
            states[_OFF])
        # * Connection died can in some cases also be
        #   triggered while we are in CONNECTING
        #   state. I should be avoided, since connection_aborted
        #   is clearer (and reserve connection_died
        #   for transitions from on->off
        states[_CON].addTransition(
            conn.qtsigs.connection_died_signal,
            states[_OFF])

        # adding states to the machine
        for state in states.itervalues():
            machine.addState(state)
        machine.setInitialState(states[_OFF])
        return machine

    def _make_states(self, button, action, label):
        """
        Creates the four states for the state machine

        :param button: the switch button.
        :type button: QPushButton

        :param action: the actionh that controls connection switch in a menu.
        :type action: QAction

        :param label: the label that displays the connection state
        :type label: QLabel

        :returns: a dict of states
        :rtype: dict
        """
        conn = self._conn
        states = {}

        # TODO add tooltip

        # OFF State ----------------------
        off = QState()
        off_label = _tr("Turn {0}").format(
            conn.Connected.short_label)
        if button:
            off.assignProperty(
                button, 'text', off_label)
            off.assignProperty(
                button, 'enabled', True)
        if action:
            off.assignProperty(
                action, 'text', off_label)
        off.setObjectName(_OFF)
        states[_OFF] = off

        # CONNECTING State ----------------
        connecting = IntermediateState(
            conn.qtsigs.connecting_signal)
        on_label = _tr("Turn {0}").format(
            conn.Disconnected.short_label)
        if button:
            connecting.assignProperty(
                button, 'text', on_label)
            connecting.assignProperty(
                button, 'enabled', False)
        if action:
            connecting.assignProperty(
                action, 'text', on_label)
            connecting.assignProperty(
                action, 'enabled', False)
        connecting.setObjectName(_CON)
        states[_CON] = connecting

        # ON State ------------------------
        on = QState()
        if button:
            on.assignProperty(
                button, 'text', on_label)
            on.assignProperty(
                button, 'enabled', True)
        if action:
            on.assignProperty(
                action, 'text', on_label)
            on.assignProperty(
                action, 'enabled', True)
        # TODO set label for ON state
        on.setObjectName(_ON)
        states[_ON] = on

        # DISCONNECTING State -------------
        disconnecting = IntermediateState(
            conn.qtsigs.disconnecting_signal)
        if button:
            disconnecting.assignProperty(
                button, 'enabled', False)
        # XXX complete disconnecting
        # TODO disable button
        disconnecting.setObjectName(_DIS)
        states[_DIS] = disconnecting

        return states
