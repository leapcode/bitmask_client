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

import logging

from leap.auth import SRPAuth
from leap.exceptions import SRPAuthenticationError
from twisted.cred.checkers import ANONYMOUS
from twisted.cred.credentials import ICredentials
from twisted.cred.error import UnauthorizedLogin
from twisted.internet import defer, threads
from twisted.web._auth.wrapper import UnauthorizedResource
from twisted.web.error import UnsupportedMethod
from zope.interface import implements, implementer, Attribute
from twisted.cred import portal, checkers, credentials
from twisted.web import util
from twisted.cred import error
from twisted.web.resource import IResource, ErrorPage

from pixelated.config.leap import authenticate_user
from pixelated.resources import IPixelatedSession


log = logging.getLogger(__name__)


@implementer(checkers.ICredentialsChecker)
class LeapPasswordChecker(object):
    credentialInterfaces = (
        credentials.IUsernamePassword,
    )

    def __init__(self, leap_provider):
        self._leap_provider = leap_provider

    def requestAvatarId(self, credentials):
        def _validate_credentials():
            try:
                srp_auth = SRPAuth(self._leap_provider.api_uri,
                                   self._leap_provider.local_ca_crt)
                return srp_auth.authenticate(credentials.username, credentials.password)
            except SRPAuthenticationError:
                raise UnauthorizedLogin()

        def _get_leap_session(srp_auth):
            return authenticate_user(self._leap_provider, credentials.username, credentials.password, auth=srp_auth)

        d = threads.deferToThread(_validate_credentials)
        d.addCallback(_get_leap_session)
        return d


class ISessionCredential(ICredentials):

    request = Attribute('the current request')


@implementer(ISessionCredential)
class SessionCredential(object):

    def __init__(self, request):
        self.request = request


@implementer(checkers.ICredentialsChecker)
class SessionChecker(object):
    credentialInterfaces = (ISessionCredential,)

    def __init__(self, services_factory):
        self._services_factory = services_factory

    def requestAvatarId(self, credentials):
        session = self.get_session(credentials.request)
        if session.is_logged_in() and self._services_factory.is_logged_in(session.user_uuid):
            return defer.succeed(session.user_uuid)
        return defer.succeed(ANONYMOUS)

    def get_session(self, request):
        return IPixelatedSession(request.getSession())


class PixelatedRealm(object):
    implements(portal.IRealm)

    def __init__(self, root_resource, anonymous_resource):
        self._root_resource = root_resource
        self._anonymous_resource = anonymous_resource

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IResource in interfaces:
            return IResource, avatarId, lambda: None
        raise NotImplementedError()


@implementer(IResource)
class PixelatedAuthSessionWrapper(object):

    isLeaf = False

    def __init__(self, portal, root_resource, anonymous_resource, credentialFactories):
        self._portal = portal
        self._credentialFactories = credentialFactories
        self._root_resource = root_resource
        self._anonymous_resource = anonymous_resource

    def render(self, request):
        raise UnsupportedMethod(())

    def getChildWithDefault(self, path, request):
        request.postpath.insert(0, request.prepath.pop())
        return self._authorizedResource(request)

    def _authorizedResource(self, request):
        creds = SessionCredential(request)
        return util.DeferredResource(self._login(creds))

    def _login(self, credentials):
        d = self._portal.login(credentials, None, IResource)
        d.addCallbacks(self._loginSucceeded, self._loginFailed)
        return d

    def _loginSucceeded(self, args):
        interface, avatar, logout = args
        if avatar == checkers.ANONYMOUS:
            return self._anonymous_resource
        else:
            return self._root_resource

    def _loginFailed(self, result):
        if result.check(error.Unauthorized, error.LoginFailed):
            return UnauthorizedResource(self._credentialFactories)
        else:
            log.err(
                result,
                "HTTPAuthSessionWrapper.getChildWithDefault encountered "
                "unexpected error")
            return ErrorPage(500, None, None)
