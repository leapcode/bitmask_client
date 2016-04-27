#
# Copyright (c) 2016 ThoughtWorks, Inc.
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

from twisted.web.static import File


class SandboxResource(File):
    CSP_HEADER_VALUES = "sandbox allow-popups allow-scripts;" \
                        "default-src 'self';" \
                        "style-src *;" \
                        "script-src  *;" \
                        "font-src *;" \
                        "img-src *;" \
                        "object-src 'none';" \
                        "connect-src 'none';"

    def render_GET(self, request):
        request.setHeader('Content-Security-Policy', self.CSP_HEADER_VALUES)
        request.setHeader('X-Content-Security-Policy', self.CSP_HEADER_VALUES)
        request.setHeader('X-Webkit-CSP', self.CSP_HEADER_VALUES)
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Methods', 'GET')

        return super(SandboxResource, self).render_GET(request)
