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
import os

from twisted.internet import defer
from twisted.python import log

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

    print 'STARTING PIXELATED USER AGENT...'

    leap_session = LeapSessionAdapter(
        userid, soledad, keymanager)

    config = Config()
    leap_home = os.path.expanduser('~/.config/leap')
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


class LeapSessionAdapter(object):

    def __init__(self, userid, soledad, keymanager):
        self.userid = userid

        self.soledad = soledad

        self.nicknym = Config()
        self.nicknym.keymanager = keymanager

        self.mail_store = LeapMailStore(soledad)

        self.user_auth = Config()
        self.user_auth.uuid = soledad.uuid

        # XXX what is this?? path to smtp-service?
        # self.config = provider.config
        # self.provider = provider

        self.fresh_account = False
        self.incoming_mail_fetcher = None
        self.account = IMAPAccount(userid, soledad, defer.Deferred())

        username, provider = userid.split('@')
        smtp_client_cert = os.path.expanduser(
            '~/.config/leap/providers/{provider}/keys/'
            'client/smtp_{username}.pem'.format(
                provider=provider, username=username))
        # TODO --- get from config
        smtp_host = 'antelope.mail.bitmask.net'
        smtp_port = 2013

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
