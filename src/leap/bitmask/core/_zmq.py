# -*- coding: utf-8 -*-
# _zmq.py
# Copyright (C) 2015 LEAP
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
ZMQ REQ-REP Dispatcher.
"""

from twisted.application import service
from twisted.internet import reactor
from twisted.python import log

from txzmq import ZmqEndpoint, ZmqEndpointType
from txzmq import ZmqFactory, ZmqREPConnection

from leap.bitmask.core import ENDPOINT
from leap.bitmask.core.dispatcher import CommandDispatcher


class ZMQServerService(service.Service):

    def __init__(self, core):
        self._core = core

    def startService(self):
        zf = ZmqFactory()
        e = ZmqEndpoint(ZmqEndpointType.bind, ENDPOINT)

        self._conn = _DispatcherREPConnection(zf, e, self._core)
        reactor.callWhenRunning(self._conn.do_greet)
        service.Service.startService(self)

    def stopService(self):
        service.Service.stopService(self)


class _DispatcherREPConnection(ZmqREPConnection):

    def __init__(self, zf, e, core):
        ZmqREPConnection.__init__(self, zf, e)
        self.dispatcher = CommandDispatcher(core)

    def gotMessage(self, msgId, *parts):

        r = self.dispatcher.dispatch(parts)
        r.addCallback(self.defer_reply, msgId)

    def defer_reply(self, response, msgId):
        reactor.callLater(0, self.reply, msgId, str(response))

    def log_err(self, failure, msgId):
        log.err(failure)
        self.defer_reply("ERROR: %r" % failure, msgId)

    def do_greet(self):
        log.msg('starting ZMQ dispatcher')
