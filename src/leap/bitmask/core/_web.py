# -*- coding: utf-8 -*-
# _web.py
# Copyright (C) 2016 LEAP
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
HTTP REST Dispatcher Service.
"""

import json
import os
import pkg_resources

from twisted.internet import reactor
from twisted.application import service

from twisted.web.resource import Resource
from twisted.web.server import Site, NOT_DONE_YET
from twisted.web.static import File

from leap.bitmask.core.dispatcher import CommandDispatcher


class HTTPDispatcherService(service.Service):

    """
    A Dispatcher for BitmaskCore exposing a REST API.
    """

    def __init__(self, core, port=7070, debug=False):
        self._core = core
        self.port = port
        self.debug = debug

    def startService(self):
        webdir = os.path.abspath(
            pkg_resources.resource_filename("leap.bitmask.core", "web"))
        root = File(webdir)

        api = Api(CommandDispatcher(self._core))
        root.putChild(u"API", api)

        site = Site(root)
        self.site = site
        self.listener = reactor.listenTCP(self.port, site,
                                          interface='127.0.0.1')

    def stopService(self):
        self.site.stopFactory()
        self.listener.stopListening()


class Api(Resource):
    isLeaf = True

    def __init__(self, dispatcher):
        Resource.__init__(self)
        self.dispatcher = dispatcher

    def render_POST(self, request):
        command = request.uri.split('/')[2:]
        params = request.content.getvalue()
        if params:
            # json.loads returns unicode strings and the rest of the code
            # expects strings. This 'str(param)' conversion can be removed
            # if we move to python3
            for param in json.loads(params):
                command.append(str(param))

        d = self.dispatcher.dispatch(command)
        d.addCallback(self._write_response, request)
        return NOT_DONE_YET

    def _write_response(self, response, request):
        request.setHeader('Content-Type', 'application/json')
        request.write(response)
        request.finish()
