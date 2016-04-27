#
# Copyright (c) 2014 ThoughtWorks, Inc.
#
# Pixelated is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pixelated is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Pixelated. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
from sys import platform as _platform

import protobuf.socketrpc.server

# protobuf throws a lot of 'Socket is not connected' exceptions on OSX but they are not an issue.
# refer too https://code.google.com/p/protobuf-socket-rpc/issues/detail?id=10 and
# or https://leap.se/code/issues/2187
if _platform == 'darwin':
    def try_except_decorator(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
                pass
            except:
                pass

        return wrapper

    protobuf.socketrpc.server.SocketHandler.handle = try_except_decorator(
        protobuf.socketrpc.server.SocketHandler.handle)
