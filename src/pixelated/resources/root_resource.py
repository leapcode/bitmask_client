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
import hashlib
import json
import os
from string import Template

from pixelated.resources import BaseResource, UnAuthorizedResource
from pixelated.resources.attachments_resource import AttachmentsResource
from pixelated.resources.sandbox_resource import SandboxResource
from pixelated.resources.contacts_resource import ContactsResource
from pixelated.resources.features_resource import FeaturesResource
from pixelated.resources.feedback_resource import FeedbackResource
from pixelated.resources.login_resource import LoginResource
from pixelated.resources.logout_resource import LogoutResource
from pixelated.resources.user_settings_resource import UserSettingsResource
from pixelated.resources.mail_resource import MailResource
from pixelated.resources.mails_resource import MailsResource
from pixelated.resources.tags_resource import TagsResource
from pixelated.resources.keys_resource import KeysResource
from twisted.web.static import File

CSRF_TOKEN_LENGTH = 32

MODE_STARTUP = 1
MODE_RUNNING = 2


class RootResource(BaseResource):

    def __init__(self, services_factory, static_folder=None):
        BaseResource.__init__(self, services_factory)
        self._startup_assets_folder = self._get_startup_folder()
        self._static_folder = static_folder or self._get_static_folder()
        self._html_template = open(os.path.join(
            self._static_folder, 'index.html')).read()
        self._services_factory = services_factory
        self._child_resources = ChildResourcesMap()
        self._startup_mode()

    def _startup_mode(self):
        self.putChild('startup-assets', File(self._startup_assets_folder))
        self._mode = MODE_STARTUP

    def getChild(self, path, request):
        if path == '':
            return self
        if self._is_xsrf_valid(request):
            return self._child_resources.get(path)
        return UnAuthorizedResource()

    def _is_xsrf_valid(self, request):
        xsrf_token = request.getCookie('XSRF-TOKEN')

        ajax_request = (request.getHeader(
            'x-requested-with') == 'XMLHttpRequest')
        if ajax_request:
            xsrf_header = request.getHeader('x-xsrf-token')
            return xsrf_header and xsrf_header == xsrf_token

        get_request = (request.method == 'GET')
        if get_request:
            return True

        csrf_input = request.args.get('csrftoken', [None])[0] or json.loads(
            request.content.read()).get('csrftoken', [None])[0]
        return csrf_input and csrf_input == xsrf_token

    def initialize(self, portal=None, disclaimer_banner=None):
        self._child_resources.add(
            'sandbox', SandboxResource(self._static_folder))
        self._child_resources.add('assets', File(self._static_folder))
        self._child_resources.add('keys', KeysResource(self._services_factory))
        self._child_resources.add(
            AttachmentsResource.BASE_URL, AttachmentsResource(self._services_factory))
        self._child_resources.add(
            'contacts', ContactsResource(self._services_factory))
        self._child_resources.add('features', FeaturesResource(portal))
        self._child_resources.add('tags', TagsResource(self._services_factory))
        self._child_resources.add(
            'mails', MailsResource(self._services_factory))
        self._child_resources.add('mail', MailResource(self._services_factory))
        self._child_resources.add(
            'feedback', FeedbackResource(self._services_factory))
        self._child_resources.add(
            'user-settings', UserSettingsResource(self._services_factory))
        self._child_resources.add(LoginResource.BASE_URL,
                                  LoginResource(self._services_factory, portal, disclaimer_banner=disclaimer_banner))
        self._child_resources.add(
            LogoutResource.BASE_URL, LogoutResource(self._services_factory))

        self._mode = MODE_RUNNING

    def _get_startup_folder(self):
        path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(path, '..', 'assets')

    def _get_static_folder(self):
        static_folder = os.path.abspath(os.path.join(
            os.path.abspath(__file__), "..", "..", "..", "web-ui", "app"))
        # this is a workaround for packaging
        if not os.path.exists(static_folder):
            static_folder = os.path.abspath(
                os.path.join(os.path.abspath(__file__), "..", "..", "..", "..", "web-ui", "app"))
        if not os.path.exists(static_folder):
            static_folder = os.path.join(
                '/', 'usr', 'share', 'pixelated-user-agent')
        return static_folder

    def _is_starting(self):
        return self._mode == MODE_STARTUP

    def _add_csrf_cookie(self, request):
        csrf_token = hashlib.sha256(os.urandom(CSRF_TOKEN_LENGTH)).hexdigest()
        request.addCookie('XSRF-TOKEN', csrf_token)

    def render_GET(self, request):
        self._add_csrf_cookie(request)
        if self._is_starting():
            return open(os.path.join(self._startup_assets_folder, 'Interstitial.html')).read()
        else:
            account_email = self.mail_service(request).account_email
            response = Template(self._html_template).safe_substitute(
                account_email=account_email)
            return str(response)


class ChildResourcesMap(object):

    def __init__(self):
        self._registry = {}

    def add(self, path, resource):
        self._registry[path] = resource

    def get(self, path):
        return self._registry.get(path)
