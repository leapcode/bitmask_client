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

from twisted.internet import defer
from twisted.python import log

from leap.bitmask.util import get_path_prefix
from leap.mail.imap.account import IMAPAccount

from pixelated.adapter.mailstore import LeapMailStore
from pixelated.adapter.welcome_mail import add_welcome_mail
from pixelated.application import SingleUserServicesFactory
from pixelated.application import UserAgentMode
from pixelated.application import start_site
from pixelated.bitmask_libraries.smtp import LeapSMTPConfig
from pixelated.bitmask_libraries.session import SessionCache
from pixelated.config import services
from pixelated.resources.root_resource import RootResource


def start_pixelated_user_agent(userid, soledad, keymanager):

    leap_session = LeapSessionAdapter(
        userid, soledad, keymanager)

    config = Config()
    leap_home = os.path.join(get_path_prefix(), 'leap')
    config.leap_home = leap_home
    leap_session.config = config

    services_factory = SingleUserServicesFactory(
        UserAgentMode(is_single_user=True))
    resource = RootResource(services_factory)

    config.port = 9090
    config.sslkey = None
    config.sslcert = None
    config.host = 'localhost'

    deferred = _start_in_single_user_mode(
        leap_session, config,
        resource, services_factory)
    return deferred


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


class LeapSessionAdapter(object):

    def __init__(self, userid, soledad, keymanager):
        self.userid = userid

        self.soledad = soledad

        # FIXME this expects a keymanager-like instance
        self.nicknym = Config()
        self.nicknym.keymanager = keymanager

        self.mail_store = LeapMailStore(soledad)

        self.user_auth = Config()
        self.user_auth.uuid = soledad.uuid

        self.fresh_account = False
        self.incoming_mail_fetcher = None
        self.account = IMAPAccount(userid, soledad, defer.Deferred())

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
