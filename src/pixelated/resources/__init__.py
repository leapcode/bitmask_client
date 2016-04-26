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

import json
import logging

from twisted.web.http import UNAUTHORIZED
from twisted.web.resource import Resource

# from pixelated.resources.login_resource import LoginResource
from pixelated.resources.session import IPixelatedSession

from twisted.web.http import INTERNAL_SERVER_ERROR
log = logging.getLogger(__name__)


class SetEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super(SetEncoder, self).default(obj)


def respond_json(entity, request, status_code=200):
    json_response = json.dumps(entity, cls=SetEncoder)
    request.responseHeaders.addRawHeader(b"content-type", b"application/json")
    request.code = status_code
    return json_response


def respond_json_deferred(entity, request, status_code=200):
    json_response = json.dumps(entity, cls=SetEncoder)
    request.responseHeaders.addRawHeader(b"content-type", b"application/json")
    request.code = status_code
    request.write(json_response)
    request.finish()


class GenericDeferredErrorHandler(object):

    @classmethod
    def generic_error_handling(cls, e, request):
        log.error(e)
        request.setResponseCode(INTERNAL_SERVER_ERROR)
        request.write('Something went wrong!')
        request.finish()


class BaseResource(Resource, GenericDeferredErrorHandler):

    def __init__(self, services_factory):
        Resource.__init__(self)
        self._services_factory = services_factory

    def _get_user_id_from_request(self, request):
        if self._services_factory.mode.is_single_user:
            return None  # it doesn't matter
        session = self.get_session(request)
        if session.is_logged_in():
            return session.user_uuid
        raise ValueError('Not logged in')

    def is_logged_in(self, request):
        session = self.get_session(request)
        return session.is_logged_in() and self._services_factory.is_logged_in(session.user_uuid)

    def get_session(self, request):
        return IPixelatedSession(request.getSession())

    def _services(self, request):
        user_id = self._get_user_id_from_request(request)
        return self._services_factory.services(user_id)

    def _service(self, request, attribute):
        return getattr(self._services(request), attribute)

    def keymanager(self, request):
        return self._service(request, 'keymanager')

    def mail_service(self, request):
        return self._service(request, 'mail_service')

    def search_engine(self, request):
        return self._service(request, 'search_engine')

    def draft_service(self, request):
        return self._service(request, 'draft_service')

    def feedback_service(self, request):
        return self._service(request, 'feedback_service')


class UnAuthorizedResource(Resource):

    def __init__(self):
        Resource.__init__(self)

    def render_GET(self, request):
        request.setResponseCode(UNAUTHORIZED)
        return "Unauthorized!"

    def render_POST(self, request):
        request.setResponseCode(UNAUTHORIZED)
        return "Unauthorized!"
