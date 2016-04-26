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
from requests.exceptions import SSLError


def error_handler(excp):
    if excp.type is SSLError:
        print """
            SSL Error: Please check your certificates or read our wiki for further info:
            https://github.com/pixelated-project/pixelated-user-agent/wiki/Configuring-and-using-SSL-Certificates-for-LEAP-provider
            Error reference: %s
            """ % excp.getErrorMessage()
    else:
        raise excp
