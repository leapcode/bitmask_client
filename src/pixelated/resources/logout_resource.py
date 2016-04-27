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

from twisted.internet import defer
from twisted.web import util
from twisted.web.server import NOT_DONE_YET

from pixelated.resources import BaseResource
from pixelated.resources.login_resource import LoginResource


class LogoutResource(BaseResource):
    BASE_URL = "logout"
    isLeaf = True

    @defer.inlineCallbacks
    def _execute_logout(self, request):
        session = self.get_session(request)
        yield self._services_factory.log_out_user(session.user_uuid)
        session.expire()

    def render_POST(self, request):
        def _redirect_to_login(_):
            content = util.redirectTo("/%s" % LoginResource.BASE_URL, request)
            request.write(content)
            request.finish()

        d = self._execute_logout(request)
        d.addCallback(_redirect_to_login)
        d.addErrback(self.generic_error_handling, request)

        return NOT_DONE_YET
