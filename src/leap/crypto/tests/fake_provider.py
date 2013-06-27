#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fake_provider.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""A server faking some of the provider resources and apis,
used for testing Leap Client requests

It needs that you create a subfolder named 'certs',
and that you place the following files:

XXX check if in use

[ ] test-openvpn.pem
[ ] test-provider.json
[ ] test-eip-service.json
"""
import binascii
import json
import os
import sys
import time

import srp

from OpenSSL import SSL

from zope.interface import Interface, Attribute, implements

from twisted.web.server import Site, Request
from twisted.web.static import File, Data
from twisted.web.resource import Resource
from twisted.internet import reactor

from leap.common.testing.https_server import where

# See
# http://twistedmatrix.com/documents/current/web/howto/web-in-60/index.html
# for more examples

"""
Testing the FAKE_API:
#####################

 1) register an user
 >> curl -d "user[login]=me" -d "user[password_salt]=foo" \
         -d "user[password_verifier]=beef" http://localhost:8000/1/users
 << {"errors": null}

 2) check that if you try to register again, it will fail:
 >> curl -d "user[login]=me" -d "user[password_salt]=foo" \
         -d "user[password_verifier]=beef" http://localhost:8000/1/users
 << {"errors": {"login": "already taken!"}}

"""

# Globals to mock user/sessiondb

_USERDB = {}
_SESSIONDB = {}

_here = os.path.split(__file__)[0]


safe_unhexlify = lambda x: binascii.unhexlify(x) \
    if (len(x) % 2 == 0) else binascii.unhexlify('0' + x)


class IUser(Interface):
    """
    Defines the User Interface
    """
    login = Attribute("User login.")
    salt = Attribute("Password salt.")
    verifier = Attribute("Password verifier.")
    session = Attribute("Session.")
    svr = Attribute("Server verifier.")


class User(object):
    """
    User object.
    We store it in our simple session mocks
    """

    implements(IUser)

    def __init__(self, login, salt, verifier):
        self.login = login
        self.salt = salt
        self.verifier = verifier
        self.session = None
        self.svr = None

    def set_server_verifier(self, svr):
        """
        Adds a svr verifier object to this
        User instance
        """
        self.svr = svr

    def set_session(self, session):
        """
        Adds this instance of User to the
        global session dict
        """
        _SESSIONDB[session] = self
        self.session = session


class FakeUsers(Resource):
    """
    Resource that handles user registration.
    """

    def __init__(self, name):
        self.name = name

    def render_POST(self, request):
        """
        Handles POST to the users api resource
        Simulates a login.
        """
        args = request.args

        login = args['user[login]'][0]
        salt = args['user[password_salt]'][0]
        verifier = args['user[password_verifier]'][0]

        if login in _USERDB:
            request.setResponseCode(422)
            return "%s\n" % json.dumps(
                {'errors': {'login': 'already taken!'}})

        print '[server]', login, verifier, salt
        user = User(login, salt, verifier)
        _USERDB[login] = user
        return json.dumps({'errors': None})


def getSession(self, sessionInterface=None):
    """
    we overwrite twisted.web.server.Request.getSession method to
    put the right cookie name in place
    """
    if not self.session:
        #cookiename = b"_".join([b'TWISTED_SESSION'] + self.sitepath)
        cookiename = b"_".join([b'_session_id'] + self.sitepath)
        sessionCookie = self.getCookie(cookiename)
        if sessionCookie:
            try:
                self.session = self.site.getSession(sessionCookie)
            except KeyError:
                pass
        # if it still hasn't been set, fix it up.
        if not self.session:
            self.session = self.site.makeSession()
            self.addCookie(cookiename, self.session.uid, path=b'/')
    self.session.touch()
    if sessionInterface:
        return self.session.getComponent(sessionInterface)
    return self.session


def get_user(request):
    """
    Returns user from the session dict
    """
    login = request.args.get('login')
    if login:
        user = _USERDB.get(login[0], None)
        if user:
            return user

    request.getSession = getSession.__get__(request, Request)
    session = request.getSession()

    user = _SESSIONDB.get(session, None)
    return user


class FakeSession(Resource):
    def __init__(self, name):
        """
        Initializes session
        """
        self.name = name

    def render_GET(self, request):
        """
        Handles GET requests.
        """
        return "%s\n" % json.dumps({'errors': None})

    def render_POST(self, request):
        """
        Handles POST requests.
        """
        user = get_user(request)

        if not user:
            # XXX get real error from demo provider
            return json.dumps({'errors': 'no such user'})

        A = request.args['A'][0]

        _A = safe_unhexlify(A)
        _salt = safe_unhexlify(user.salt)
        _verifier = safe_unhexlify(user.verifier)

        svr = srp.Verifier(
            user.login,
            _salt,
            _verifier,
            _A,
            hash_alg=srp.SHA256,
            ng_type=srp.NG_1024)

        s, B = svr.get_challenge()

        _B = binascii.hexlify(B)

        print '[server] login = %s' % user.login
        print '[server] salt = %s' % user.salt
        print '[server] len(_salt) = %s' % len(_salt)
        print '[server] vkey = %s' % user.verifier
        print '[server] len(vkey) = %s' % len(_verifier)
        print '[server] s = %s' % binascii.hexlify(s)
        print '[server] B = %s' % _B
        print '[server] len(B) = %s' % len(_B)

        # override Request.getSession
        request.getSession = getSession.__get__(request, Request)
        session = request.getSession()

        user.set_session(session)
        user.set_server_verifier(svr)

        # yep, this is tricky.
        # some things are *already* unhexlified.
        data = {
            'salt': user.salt,
            'B': _B,
            'errors': None}

        return json.dumps(data)

    def render_PUT(self, request):
        """
        Handles PUT requests.
        """
        # XXX check session???
        user = get_user(request)

        if not user:
            print '[server] NO USER'
            return json.dumps({'errors': 'no such user'})

        data = request.content.read()
        auth = data.split("client_auth=")
        M = auth[1] if len(auth) > 1 else None
        # if not H, return
        if not M:
            return json.dumps({'errors': 'no M proof passed by client'})

        svr = user.svr
        HAMK = svr.verify_session(binascii.unhexlify(M))
        if HAMK is None:
            print '[server] verification failed!!!'
            raise Exception("Authentication failed!")
            #import ipdb;ipdb.set_trace()

        assert svr.authenticated()
        print "***"
        print '[server] User successfully authenticated using SRP!'
        print "***"

        return json.dumps(
            {'M2': binascii.hexlify(HAMK),
             'id': '9c943eb9d96a6ff1b7a7030bdeadbeef',
             'errors': None})


class API_Sessions(Resource):
    """
    Top resource for the API v1
    """
    def getChild(self, name, request):
        return FakeSession(name)


class FileModified(File):
    def render_GET(self, request):
        since = request.getHeader('if-modified-since')
        if since:
            tsince = time.strptime(since.replace(" GMT", ""))
            tfrom = time.strptime(time.ctime(os.path.getmtime(self.path)))
            if tfrom > tsince:
                return File.render_GET(self, request)
            else:
                request.setResponseCode(304)
                return ""
        return File.render_GET(self, request)


class OpenSSLServerContextFactory(object):

    def getContext(self):
        """
        Create an SSL context.
        """
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        #ctx = SSL.Context(SSL.TLSv1_METHOD)
        ctx.use_certificate_file(where('leaptestscert.pem'))
        ctx.use_privatekey_file(where('leaptestskey.pem'))

        return ctx


def get_provider_factory():
    """
    Instantiates a Site that serves the resources
    that we expect from a valid provider.
    Listens on:
    * port 8000 for http connections
    * port 8443 for https connections

    :rparam: factory for a site
    :rtype: Site instance
    """
    root = Data("", "")
    root.putChild("", root)
    root.putChild("provider.json", FileModified(
        os.path.join(_here,
                     "test_provider.json")))
    config = Resource()
    config.putChild(
        "eip-service.json",
        FileModified(
            os.path.join(_here, "eip-service.json")))
    apiv1 = Resource()
    apiv1.putChild("config", config)
    apiv1.putChild("sessions", API_Sessions())
    apiv1.putChild("users", FakeUsers(None))
    apiv1.putChild("cert", FileModified(
        os.path.join(_here,
                     'openvpn.pem')))
    root.putChild("1", apiv1)

    factory = Site(root)
    return factory


if __name__ == "__main__":

    from twisted.python import log
    log.startLogging(sys.stdout)

    factory = get_provider_factory()

    # regular http (for debugging with curl)
    reactor.listenTCP(8000, factory)
    reactor.listenSSL(8443, factory, OpenSSLServerContextFactory())
    reactor.run()
