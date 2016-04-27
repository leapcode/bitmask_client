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
from twisted.web.server import NOT_DONE_YET


class TagsResource(BaseResource):

    isLeaf = True

    def __init__(self, services_factory):
        BaseResource.__init__(self, services_factory)

    def render_GET(self, request):
        _search_engine = self.search_engine(request)
        query = request.args.get('q', [''])[0]
        skip_default_tags = request.args.get('skipDefaultTags', [False])[0]

        d = deferToThread(lambda: _search_engine.tags(
            query=query, skip_default_tags=skip_default_tags))
        d.addCallback(lambda tags: respond_json_deferred(tags, request))
        d.addErrback(self.generic_error_handling, request)

        return NOT_DONE_YET
