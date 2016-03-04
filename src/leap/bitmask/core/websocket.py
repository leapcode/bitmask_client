# -*- coding: utf-8 -*-
# websocket.py
# Copyright (C) 2015, 2016 LEAP
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
WebSockets Dispatcher Service.
"""

import os
import pkg_resources

from twisted.internet import reactor
from twisted.application import service

from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.resource import WebSocketResource
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol

from leap.bitmask.core.dispatcher import CommandDispatcher


class WebSocketsDispatcherService(service.Service):

    """
    A Dispatcher for BitmaskCore exposing a WebSockets Endpoint.
    """

    def __init__(self, core, port=8080, debug=False):
        self._core = core
        self.port = port
        self.debug = debug

    def startService(self):

        factory = WebSocketServerFactory(u"ws://127.0.0.1:%d" % self.port,
                                         debug=self.debug)
        factory.protocol = DispatcherProtocol
        factory.protocol.dispatcher = CommandDispatcher(self._core)

        # FIXME: Site.start/stopFactory should start/stop factories wrapped as
        # Resources
        factory.startFactory()

        resource = WebSocketResource(factory)

        # we server static files under "/" ..
        webdir = os.path.abspath(
            pkg_resources.resource_filename("leap.bitmask.core", "web"))
        root = File(webdir)

        # and our WebSocket server under "/ws"
        root.putChild(u"bitmask", resource)

        # both under one Twisted Web Site
        site = Site(root)

        self.site = site
        self.factory = factory

        self.listener = reactor.listenTCP(self.port, site)

    def stopService(self):
        self.factory.stopFactory()
        self.site.stopFactory()
        self.listener.stopListening()


class DispatcherProtocol(WebSocketServerProtocol):

    def onMessage(self, msg, binary):
        parts = msg.split()
        r = self.dispatcher.dispatch(parts)
        r.addCallback(self.defer_reply, binary)

    def reply(self, response, binary):
        self.sendMessage(response, binary)

    def defer_reply(self, response, binary):
        reactor.callLater(0, self.reply, response, binary)

    def _get_service(self, name):
        return self.core.getServiceNamed(name)
