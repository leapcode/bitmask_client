# Copyright 2011 Canonical Ltd.
#
# This file is part of u1db.
#
# u1db is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# u1db is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with u1db.  If not, see <http://www.gnu.org/licenses/>.

"""Tests for test infrastructure bits"""

from wsgiref import simple_server

from u1db import (
    tests,
    )


class TestTestCaseWithServer(tests.TestCaseWithServer):

    def make_app(self):
        return "app"

    @staticmethod
    def server_def():
        def make_server(host_port, application):
            assert application == "app"
            return simple_server.WSGIServer(host_port, None)
        return (make_server, "shutdown", "http")

    def test_getURL(self):
        self.startServer()
        url = self.getURL()
        self.assertTrue(url.startswith('http://127.0.0.1:'))
