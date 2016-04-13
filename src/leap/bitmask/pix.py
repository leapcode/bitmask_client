# -*- coding: utf-8 -*-
# pix.py
# Copyright (C) 2016 LEAP
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
"""
Pixelated plugin integration.
"""
import json
import os
import sys

from twisted.internet import defer
from twisted.python import log

from leap.bitmask.util import get_path_prefix
from leap.mail.mail import Account
from leap.keymanager import openpgp, KeyNotFound

try:
    from pixelated.adapter.mailstore import LeapMailStore
    from pixelated.adapter.welcome_mail import add_welcome_mail
    from pixelated.application import SingleUserServicesFactory
    from pixelated.application import UserAgentMode
    from pixelated.application import start_site
    from pixelated.bitmask_libraries.smtp import LeapSMTPConfig
    from pixelated.bitmask_libraries.session import SessionCache
    from pixelated.config import services
    from pixelated.resources.root_resource import RootResource
    import pixelated_www
    HAS_PIXELATED = True
except ImportError:
    HAS_PIXELATED = False


def start_pixelated_user_agent(userid, soledad, keymanager):

    leap_session = LeapSessionAdapter(
        userid, soledad, keymanager)

    config = Config()
    leap_home = os.path.join(get_path_prefix(), 'leap')
    config.leap_home = leap_home
    leap_session.config = config

    services_factory = SingleUserServicesFactory(
        UserAgentMode(is_single_user=True))

    if getattr(sys, 'frozen', False):
        # we are running in a |PyInstaller| bundle
        static_folder = os.path.join(sys._MEIPASS, 'pixelated_www')
    else:
        static_folder = os.path.abspath(pixelated_www.__path__[0])

    resource = RootResource(services_factory, static_folder=static_folder)

    config.host = 'localhost'
    config.port = 9090
    config.sslkey = None
    config.sslcert = None

    d = leap_session.account.callWhenReady(
        lambda _: _start_in_single_user_mode(
            leap_session, config,
            resource, services_factory))
    return d


def get_smtp_config(provider):
    config_path = os.path.join(
        get_path_prefix(), 'leap', 'providers', provider, 'smtp-service.json')
    json_config = json.loads(open(config_path).read())
    chosen_host = json_config['hosts'].keys()[0]
    hostname = json_config['hosts'][chosen_host]['hostname']
    port = json_config['hosts'][chosen_host]['port']

    config = Config()
    config.host = hostname
    config.port = port
    return config


class NickNym(object):

    def __init__(self, keymanager, userid):
        self._email = userid
        self.keymanager = keymanager

    @defer.inlineCallbacks
    def generate_openpgp_key(self):
        key_present = yield self._key_exists(self._email)
        if not key_present:
            yield self._gen_key()
        yield self._send_key_to_leap()

    @defer.inlineCallbacks
    def _key_exists(self, email):
        try:
            yield self.fetch_key(email, private=True, fetch_remote=False)
            defer.returnValue(True)
        except KeyNotFound:
            defer.returnValue(False)

    def fetch_key(self, email, private=False, fetch_remote=True):
        return self.keymanager.get_key(
            email, openpgp.OpenPGPKey,
            private=private, fetch_remote=fetch_remote)

    def _gen_key(self):
        return self.keymanager.gen_key(openpgp.OpenPGPKey)

    def _send_key_to_leap(self):
        return self.keymanager.send_key(openpgp.OpenPGPKey)


class LeapSessionAdapter(object):

    def __init__(self, userid, soledad, keymanager):
        self.userid = userid

        self.soledad = soledad

        # XXX this needs to be converged with our public apis.
        self.nicknym = NickNym(keymanager, userid)
        self.mail_store = LeapMailStore(soledad)

        self.user_auth = Config()
        self.user_auth.uuid = soledad.uuid

        self.fresh_account = False
        self.incoming_mail_fetcher = None
        self.account = Account(soledad)

        username, provider = userid.split('@')
        smtp_client_cert = os.path.join(
            get_path_prefix(),
            'leap', 'providers', provider, 'keys',
            'client',
            'smtp_{username}.pem'.format(
                username=username))

        assert(os.path.isfile(smtp_client_cert))

        smtp_config = get_smtp_config(provider)
        smtp_host = smtp_config.host
        smtp_port = smtp_config.port

        self.smtp_config = LeapSMTPConfig(
            userid,
            smtp_client_cert, smtp_host, smtp_port)

    def account_email(self):
        return self.userid

    def close(self):
        pass

    @property
    def is_closed(self):
        return self._is_closed

    def remove_from_cache(self):
        key = SessionCache.session_key(self.provider, self.userid)
        SessionCache.remove_session(key)

    def sync(self):
        return self.soledad.sync()


class Config(object):
    pass


def _start_in_single_user_mode(leap_session, config, resource,
                               services_factory):
    start_site(config, resource)
    return start_user_agent_in_single_user_mode(
        resource, services_factory,
        leap_session.config.leap_home, leap_session)


@defer.inlineCallbacks
def start_user_agent_in_single_user_mode(
        root_resource, services_factory, leap_home, leap_session):
    log.msg('Bootstrap done, loading services for user %s'
            % leap_session.userid)

    _services = services.Services(leap_session)
    yield _services.setup()

    if leap_session.fresh_account:
        yield add_welcome_mail(leap_session.mail_store)

    services_factory.add_session(leap_session.user_auth.uuid, _services)
    root_resource.initialize()
    log.msg('Done, the user agent is ready to be used')
