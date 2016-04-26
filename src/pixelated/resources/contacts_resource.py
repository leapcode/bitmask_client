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

from pixelated.resources import respond_json_deferred, BaseResource
from twisted.internet.threads import deferToThread
from twisted.web import server
from twisted.web.resource import Resource


class ContactsResource(BaseResource):

    isLeaf = True

    def __init__(self, services_factory):
        BaseResource.__init__(self, services_factory)

    def render_GET(self, request):
        _search_engine = self.search_engine(request)
        query = request.args.get('q', [''])[-1]
        d = deferToThread(lambda: _search_engine.contacts(query))
        d.addCallback(lambda tags: respond_json_deferred(tags, request))

        def handle_error(error):
            print 'Something went wrong'
            import traceback
            traceback.print_exc()
            print error

        d.addErrback(handle_error)

        return server.NOT_DONE_YET
