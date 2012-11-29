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

"""Build server for u1db-serve."""

from paste import httpserver

from u1db.remote import (
    http_app,
    server_state,
    )


def make_server(host, port, working_dir):
    """Make a server on host and port exposing dbs living in working_dir."""
    state = server_state.ServerState()
    state.set_workingdir(working_dir)
    application = http_app.HTTPApp(state)
    server = httpserver.WSGIServer(application, (host, port),
                                   httpserver.WSGIHandler)
    return server
