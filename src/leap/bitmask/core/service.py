# -*- coding: utf-8 -*-
# service.py
# Copyright (C) 2015 LEAP
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
Bitmask-core Service.
"""
import resource

from twisted.internet import reactor
from twisted.python import log

from leap.bitmask import __version__
from leap.bitmask.core import configurable
from leap.bitmask.core import mail_services
from leap.bitmask.core import _zmq
from leap.bitmask.core import websocket
from leap.bonafide.service import BonafideService
from leap.common.events import server as event_server
#from leap.vpn import EIPService


class BitmaskBackend(configurable.ConfigurableService):

    def __init__(self, basedir='~/.config/leap'):

        configurable.ConfigurableService.__init__(self, basedir)

        def enabled(service):
            return self.get_config('services', service, False, boolean=True)

        on_start = reactor.callWhenRunning

        on_start(self.init_events)
        on_start(self.init_bonafide)

        if enabled('mail'):
            on_start(self.init_soledad)
            on_start(self.init_keymanager)
            on_start(self.init_mail)

        if enabled('eip'):
            on_start(self.init_eip)

        if enabled('zmq'):
            on_start(self.init_zmq)

        if enabled('web'):
            on_start(self.init_web)

    def init_events(self):
        event_server.ensure_server()

    def init_bonafide(self):
        bf = BonafideService(self.basedir)
        bf.setName("bonafide")
        bf.setServiceParent(self)
        # TODO ---- these hooks should be activated only if
        # (1) we have enabled that service
        # (2) provider offers this service
        bf.register_hook('on_passphrase_entry', listener='soledad')
        bf.register_hook('on_bonafide_auth', listener='soledad')
        bf.register_hook('on_bonafide_auth', listener='keymanager')

    def init_soledad(self):
        service = mail_services.SoledadService
        sol = self._maybe_start_service(
            'soledad', service, self.basedir)
        if sol:
            sol.register_hook(
                'on_new_soledad_instance', listener='keymanager')

    def init_keymanager(self):
        service = mail_services.KeymanagerService
        km = self._maybe_start_service(
            'keymanager', service, self.basedir)
        if km:
            km.register_hook('on_new_keymanager_instance', listener='mail')

    def init_mail(self):
        service = mail_services.StandardMailService
        self._maybe_start_service('mail', service, self.basedir)

    def init_eip(self):
        # FIXME -- land EIP into leap.vpn
        pass
        #self._maybe_start_service('eip', EIPService)

    def init_zmq(self):
        zs = _zmq.ZMQServerService(self)
        zs.setServiceParent(self)

    def init_web(self):
        ws = websocket.WebSocketsDispatcherService(self)
        ws.setServiceParent(self)

    def _maybe_start_service(self, label, klass, *args, **kw):
        try:
            self.getServiceNamed(label)
        except KeyError:
            service = klass(*args, **kw)
            service.setName(label)
            service.setServiceParent(self)
            return service

    # General commands for the BitmaskBackend Core Service

    def do_stats(self):
        log.msg('BitmaskCore Service STATS')
        mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return 'BitmaskCore: [Mem usage: %s KB]' % (mem / 1024)

    def do_status(self):
        # we may want to make this tuple a class member
        services = ('soledad', 'keymanager', 'mail', 'eip')

        status_messages = []
        for name in services:
            status = 'stopped'
            try:
                if self.getServiceNamed(name).running:
                    status = "running"
            except KeyError:
                pass
            status_messages.append("[{}: {}]".format(name, status))

        return " ".join(status_messages)

    def do_version(self):
        version = __version__
        return 'BitmaskCore: %s' % version

    def do_shutdown(self):
        self.stopService()
        reactor.callLater(1, reactor.stop)
        return 'shutting down...'

    def do_enable_service(self, service):
        assert service in self.service_names
        self.set_config('services', service, 'True')

        if service == 'mail':
            self.init_soledad()
            self.init_keymanager()
            self.init_mail()

        elif service == 'eip':
            self.init_eip()

        elif service == 'zmq':
            self.init_zmq()

        elif service == 'web':
            self.init_web()

        return 'ok'

    def do_disable_service(self, service):
        assert service in self.service_names
        # TODO -- should stop also?
        self.set_config('services', service, 'False')
        return 'ok'
