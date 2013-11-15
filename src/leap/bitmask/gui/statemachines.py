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

from PySide import QtCore
from PySide.QtCore import QStateMachine, QState, Signal
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


class SignallingState(QState):
    """
    A state that emits a custom signal on entry.
    """
    def __init__(self, signal, parent=None, name=None):
        """
        Initializer.
        :param signal: the signal to be emitted on entry on this state.
        :type signal: QtCore.QSignal
        """
        super(SignallingState, self).__init__(parent)
        self._signal = signal
        self._name = name

    def onEntry(self, *args):
        """
        Emits the signal on entry.
        """
        logger.debug('State %s::%s entered. Emitting signal ...'
                     % (self._name, self.objectName()))
        if self._signal is not None:
            self._signal.emit()


class States(object):
    """
    States for composite objects
    """

    class Off(SignallingState):
        pass

    class Connecting(SignallingState):
        pass

    class On(SignallingState):
        pass

    class Disconnecting(SignallingState):
        pass

    class StepsTrack(QObject):
        state_change = Signal()

        def __init__(self, target):
            super(States.StepsTrack, self).__init__()
            self.received = set([])
            self.target = set(target)

        def is_all_done(self):
            return all([ev in self.target for ev in self.received])

        def is_any_done(self):
            return any([ev in self.target for ev in self.received])

        def seen(self, _type):
            if _type in self.target:
                self.received.add(_type)

        def reset_seen(self):
            self.received = set([])

    class TransitionOR(QtCore.QSignalTransition):

        def __init__(self, state):
            super(States.TransitionOR, self).__init__(
                state, QtCore.SIGNAL('state_change()'))
            self.state = state

        def eventTest(self, e):
            self.state.seen(e.type())
            done = self.state.is_any_done()
            if done:
                self.state.reset_seen()
            return done

        def onTransition(self, e):
            pass

    class TransitionAND(QtCore.QSignalTransition):

        def __init__(self, state):
            super(States.TransitionAND, self).__init__(
                state, QtCore.SIGNAL('state_change()'))
            self.state = state

        def eventTest(self, e):
            self.state.seen(e.type())
            done = self.state.is_all_done()
            if done:
                self.state.reset_seen()
            return done

        def onTransition(self, e):
            pass


class CompositeEvent(QtCore.QEvent):
    def __init__(self):
        super(CompositeEvent, self).__init__(
            QtCore.QEvent.Type(self.ID))


class Composite(object):
    # TODO we should generate the connectingEvents dinamycally,
    # depending on how much composite states do we get.
    # This only supports up to 2 composite states.

    class ConnectingEvent1(CompositeEvent):
        ID = QtCore.QEvent.User + 1

    class ConnectingEvent2(CompositeEvent):
        ID = QtCore.QEvent.User + 2

    class ConnectedEvent1(CompositeEvent):
        ID = QtCore.QEvent.User + 3

    class ConnectedEvent2(CompositeEvent):
        ID = QtCore.QEvent.User + 4

    class DisconnectingEvent1(CompositeEvent):
        ID = QtCore.QEvent.User + 5

    class DisconnectingEvent2(CompositeEvent):
        ID = QtCore.QEvent.User + 6

    class DisconnectedEvent1(CompositeEvent):
        ID = QtCore.QEvent.User + 7

    class DisconnectedEvent2(CompositeEvent):
        ID = QtCore.QEvent.User + 8


class Events(QtCore.QObject):
    """
    A Wrapper object for containing the events that will be
    posted to a composite state machine.
    """
    def __init__(self, parent=None):
        """
        Initializes the QObject with the given parent.
        """
        QtCore.QObject.__init__(self, parent)


class CompositeMachine(QStateMachine):

    def __init__(self, parent=None):
        QStateMachine.__init__(self, parent)

        # events
        self.events = Events(parent)
        self.create_events()

    def create_events(self):
        """
        Creates a bunch of events to be posted to the state machine when
        the transitions say so.
        """
        # XXX refactor into a dictionary?
        self.events.con_ev1 = Composite.ConnectingEvent1()
        self.events.con_ev2 = Composite.ConnectingEvent2()
        self.events.on_ev1 = Composite.ConnectedEvent1()
        self.events.on_ev2 = Composite.ConnectedEvent2()
        self.events.dis_ev1 = Composite.DisconnectingEvent1()
        self.events.dis_ev2 = Composite.DisconnectingEvent2()
        self.events.off_ev1 = Composite.DisconnectedEvent1()
        self.events.off_ev2 = Composite.DisconnectedEvent2()

    def beginSelectTransitions(self, e):
        """
        Weird. Having this method makes underlying backtraces
        to appear magically on the transitions.
        :param e: the received event
        :type e: QEvent
        """
        pass

    def _connect_children(self, child1, child2):
        """
        Connects the state transition signals for children machines.

        :param child1: the first child machine
        :type child1: QStateMachine
        :param child2: the second child machine
        :type child2: QStateMachine
        """
        # TODO refactor and generalize for composites
        # of more than 2 connections.

        c1 = child1.conn
        c1.qtsigs.connecting_signal.connect(self.con_ev1_slot)
        c1.qtsigs.connected_signal.connect(self.on_ev1_slot)
        c1.qtsigs.disconnecting_signal.connect(self.dis_ev1_slot)
        c1.qtsigs.disconnected_signal.connect(self.off_ev1_slot)

        c2 = child2.conn
        c2.qtsigs.connecting_signal.connect(self.con_ev2_slot)
        c2.qtsigs.connected_signal.connect(self.on_ev2_slot)
        c2.qtsigs.disconnecting_signal.connect(self.dis_ev2_slot)
        c2.qtsigs.disconnected_signal.connect(self.off_ev2_slot)

    # XXX why is this getting deletec in c++?
    #Traceback (most recent call last):
    #self.postEvent(self.events.on_ev2)
    #RuntimeError: Internal C++ object (ConnectedEvent2) already deleted.
    # XXX trying the following workaround, since
    # I cannot find why in the world this is getting deleted :(
    # XXX refactor!

    # slots connection1

    def con_ev1_slot(self):
        # XXX if we just postEvent, we get the Internal C++ object deleted...
        # so the workaround is to re-create it each time.
        self.events.con_ev1 = Composite.ConnectingEvent1()
        self.postEvent(self.events.con_ev1)

    def on_ev1_slot(self):
        self.events.on_ev1 = Composite.ConnectedEvent1()
        self.postEvent(self.events.on_ev1)

    def dis_ev1_slot(self):
        self.events.dis_ev1 = Composite.DisconnectingEvent1()
        self.postEvent(self.events.dis_ev1)

    def off_ev1_slot(self):
        self.events.off_ev1 = Composite.DisconnectedEvent1()
        self.postEvent(self.events.off_ev1)

    # slots connection2

    def con_ev2_slot(self):
        self.events.con_ev2 = Composite.ConnectingEvent2()
        self.postEvent(self.events.con_ev2)

    def on_ev2_slot(self):
        self.events.on_ev2 = Composite.ConnectedEvent2()
        self.postEvent(self.events.on_ev2)

    def dis_ev2_slot(self):
        self.events.dis_ev2 = Composite.DisconnectingEvent2()
        self.postEvent(self.events.dis_ev2)

    def off_ev2_slot(self):
        self.events.off_ev2 = Composite.DisconnectedEvent2()
        self.postEvent(self.events.off_ev2)


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

    def make_machine(self, **kwargs):
        """
        Creates a statemachine associated with the passed controls.

        It returns the state machine if the connection used for initializing
        the ConnectionMachineBuilder inherits exactly from
        LEAPAbstractConnection, and a tuple with the Composite Machine and its
        individual parts in case that it is a composite machine which
        connection definition inherits from more than one class that, on their
        time, inherit from LEAPAbstractConnection.

        :params: see parameters for ``_make_simple_machine``
        :returns: a QStateMachine, or a tuple with the form:
                  (CompositeStateMachine, (StateMachine1, StateMachine2))
        :rtype: QStateMachine or tuple
        """
        components = self._conn.components

        if components is None:
        # simple case: connection definition inherits directly from
        # the abstract connection.

            leap_assert_type(self._conn, connections.AbstractLEAPConnection)
            return self._make_simple_machine(self._conn, **kwargs)

        if components:
            # composite case: connection definition inherits from several
            # classes, each one of which inherit from the abstract connection.
            child_machines = tuple(
                [ConnectionMachineBuilder(connection()).make_machine()
                    for connection in components])
            composite_machine = self._make_composite_machine(
                self._conn, child_machines, **kwargs)

            composite_machine._connect_children(
                *child_machines)

            # XXX should also connect its own states with the signals
            # for the composite machine itself

            return (composite_machine, child_machines)

    def _make_composite_machine(self, conn, children,
                                **kwargs):
        """
        Creates a composite machine.

        :param conn: an instance of a connection definition.
        :type conn: LEAPAbstractConnection
        :param children: children machines
        :type children: tuple of state machines
        :returns: A composite state machine
        :rtype: QStateMachine
        """
        # TODO split this method in smaller utility functions.
        parent = kwargs.get('parent', None)

        # 1. create machine
        machine = CompositeMachine()

        # 2. create states
        off = States.Off(conn.qtsigs.disconnected_signal,
                         parent=machine,
                         name=conn.name)
        off.setObjectName("off")

        on = States.On(conn.qtsigs.connected_signal,
                       parent=machine,
                       name=conn.name)
        on.setObjectName("on")

        connecting_state = States.Connecting(
            conn.qtsigs.connecting_signal,
            parent=machine,
            name=conn.name)
        connecting_state.setObjectName("connecting")

        disconnecting_state = States.Disconnecting(
            conn.qtsigs.disconnecting_signal,
            parent=machine,
            name=conn.name)
        disconnecting_state.setObjectName("disconnecting")

        # 3. TODO create as many connectingEvents as needed (dynamically create
        # classses for that)
        # (we have manually created classes for events under CompositeEvent for
        # now, to begin with the simple 2 states case for mail.

        # 4. state tracking objects for each transition stage

        connecting_track0 = States.StepsTrack(
            (Composite.ConnectingEvent1.ID,
             Composite.ConnectingEvent2.ID))
        connecting_track0.setObjectName("connecting_step_0")

        connecting_track1 = States.StepsTrack(
            (Composite.ConnectedEvent1.ID,
             Composite.ConnectedEvent2.ID))
        connecting_track1.setObjectName("connecting_step_1")

        disconnecting_track0 = States.StepsTrack(
            (Composite.DisconnectingEvent1.ID,
             Composite.DisconnectingEvent2.ID))
        disconnecting_track0.setObjectName("disconnecting_step_0")

        disconnecting_track1 = States.StepsTrack(
            (Composite.DisconnectedEvent1.ID,
             Composite.DisconnectedEvent2.ID))
        disconnecting_track1.setObjectName("disconnecting_step_1")

        # 5. definte the transitions with the matching state-tracking
        # objects.

        # off -> connecting
        connecting_transition = States.TransitionOR(
            connecting_track0)
        connecting_transition.setTargetState(connecting_state)
        off.addTransition(connecting_transition)

        # connecting -> on
        connected_transition = States.TransitionAND(
            connecting_track1)
        connected_transition.setTargetState(on)
        connecting_state.addTransition(connected_transition)

        # on -> disconnecting
        disconnecting_transition = States.TransitionOR(
            disconnecting_track0)
        disconnecting_transition.setTargetState(disconnecting_state)
        on.addTransition(disconnecting_transition)

        # disconnecting -> off
        disconnected_transition = States.TransitionAND(
            disconnecting_track1)
        disconnected_transition.setTargetState(off)
        disconnecting_state.addTransition(disconnected_transition)

        machine.setInitialState(off)
        machine.conn = conn
        return machine

    def _make_simple_machine(self, conn,
                             button=None, action=None, label=None):
        """
        Creates a statemachine associated with the passed controls.

        :param conn: the connection instance that defines this machine.
        :type conn: AbstractLEAPConnection

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
        states = self._make_states(conn, button, action, label)

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

        machine.conn = conn
        return machine

    def _make_states(self, conn, button, action, label):
        """
        Creates the four states for the simple state machine.
        Adds the needed properties for the passed controls.

        :param conn: the connection instance that defines this machine.
        :type conn: AbstractLEAPConnection

        :param button: the switch button.
        :type button: QPushButton

        :param action: the actionh that controls connection switch in a menu.
        :type action: QAction

        :param label: the label that displays the connection state
        :type label: QLabel

        :returns: a dict of states
        :rtype: dict
        """
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
        connecting = SignallingState(
            conn.qtsigs.connecting_signal,
            name=conn.name)
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
        disconnecting = SignallingState(
            conn.qtsigs.disconnecting_signal,
            name=conn.name)
        if button:
            disconnecting.assignProperty(
                button, 'enabled', False)
        # XXX complete disconnecting
        # TODO disable button
        disconnecting.setObjectName(_DIS)
        states[_DIS] = disconnecting

        return states
