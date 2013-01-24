# -*- coding: utf-8 -*-
import logging
import platform
import re
import socket

import netifaces
import ping
import requests
import sh

from leap.base import constants
from leap.base import exceptions

logger = logging.getLogger(name=__name__)
_platform = platform.system()

#EVENTS OF NOTE
EVENT_CONNECT_REFUSED = "[ECONNREFUSED]: Connection refused (code=111)"

ICMP_TARGET = "8.8.8.8"


class LeapNetworkChecker(object):
    """
    all network related checks
    """
    def __init__(self, *args, **kwargs):
        provider_gw = kwargs.pop('provider_gw', None)
        self.provider_gateway = provider_gw

    def run_all(self, checker=None):
        if not checker:
            checker = self
        #self.error = None  # ?

        # for MVS
        checker.check_tunnel_default_interface()
        checker.check_internet_connection()
        checker.is_internet_up()

        if self.provider_gateway:
            checker.ping_gateway(self.provider_gateway)

        checker.parse_log_and_react([], ())

    def check_internet_connection(self):
        try:
            # XXX remove this hardcoded random ip
            # ping leap.se or eip provider instead...?
            # XXX could use icmp instead..
            requests.get('http://216.172.161.165')
        except requests.ConnectionError as e:
            error = "Unidentified Connection Error"
            if e.message == "[Errno 113] No route to host":
                if not self.is_internet_up():
                    error = "No valid internet connection found."
                else:
                    error = "Provider server appears to be down."
            logger.error(error)
            raise exceptions.NoInternetConnection(error)
        except (requests.HTTPError, requests.RequestException) as e:
            raise exceptions.NoInternetConnection(e.message)

        # XXX should redirect this to netcheck logger.
        # and don't clutter main log.
        logger.debug('Network appears to be up.')

    def is_internet_up(self):
        iface, gateway = self.get_default_interface_gateway()
        try:
            self.ping_gateway(self.provider_gateway)
        except exceptions.NoConnectionToGateway:
            return False
        return True

    def _get_route_table_linux(self):
        # do not use context manager, tests pass a StringIO
        f = open("/proc/net/route")
        route_table = f.readlines()
        f.close()
        #toss out header
        route_table.pop(0)
        if not route_table:
            raise exceptions.TunnelNotDefaultRouteError()
        return route_table

    def _get_def_iface_osx(self):
        default_iface = None
        #gateway = None
        routes = list(sh.route('-n', 'get', ICMP_TARGET, _iter=True))
        iface = filter(lambda l: "interface" in l, routes)
        if not iface:
            return None, None
        def_ifacel = re.findall('\w+\d', iface[0])
        default_iface = def_ifacel[0] if def_ifacel else None
        if not default_iface:
            return None, None
        _gw = filter(lambda l: "gateway" in l, routes)
        gw = re.findall('\d+\.\d+\.\d+\.\d+', _gw[0])[0]
        return default_iface, gw

    def _get_tunnel_iface_linux(self):
        # XXX review.
        # valid also when local router has a default entry?
        route_table = self._get_route_table_linux()
        line = route_table.pop(0)
        iface, destination = line.split('\t')[0:2]
        if not destination == '00000000' or not iface == 'tun0':
            raise exceptions.TunnelNotDefaultRouteError()
        return True

    def check_tunnel_default_interface(self):
        """
        Raises an TunnelNotDefaultRouteError
        if tun0 is not the chosen default route
        (including when no routes are present)
        """
        #logger.debug('checking tunnel default interface...')

        if _platform == "Linux":
            valid = self._get_tunnel_iface_linux()
            return valid
        elif _platform == "Darwin":
            default_iface, gw = self._get_def_iface_osx()
            #logger.debug('iface: %s', default_iface)
            if default_iface != "tun0":
                logger.debug('tunnel not default route! gw: %s', default_iface)
                # XXX should catch this and act accordingly...
                # but rather, this test should only be launched
                # when we have successfully completed a connection
                # ... TRIGGER: Connection stablished (or whatever it is)
                # in the logs
                raise exceptions.TunnelNotDefaultRouteError
        else:
            #logger.debug('PLATFORM !!! %s', _platform)
            raise NotImplementedError

    def _get_def_iface_linux(self):
        default_iface = None
        gateway = None

        route_table = self._get_route_table_linux()
        while route_table:
            line = route_table.pop(0)
            iface, destination, gateway = line.split('\t')[0:3]
            if destination == '00000000':
                default_iface = iface
                break
        return default_iface, gateway

    def get_default_interface_gateway(self):
        """
        gets the interface we are going thru.
        (this should be merged with check tunnel default interface,
        imo...)
        """
        if _platform == "Linux":
            default_iface, gw = self._get_def_iface_linux()
        elif _platform == "Darwin":
            default_iface, gw = self.get_def_iface_osx()
        else:
            raise NotImplementedError

        if not default_iface:
            raise exceptions.NoDefaultInterfaceFoundError

        if default_iface not in netifaces.interfaces():
            raise exceptions.InterfaceNotFoundError
        logger.debug('-- default iface', default_iface)
        return default_iface, gw

    def ping_gateway(self, gateway):
        # TODO: Discuss how much packet loss (%) is acceptable.

        # XXX -- validate gateway
        # -- is it a valid ip? (there's something in util)
        # -- is it a domain?
        # -- can we resolve? -- raise NoDNSError if not.

        # XXX -- needs review!
        # We cannout use this ping implementation; it needs root.
        # We need to look for another, poors-man implementation
        # or wrap around system traceroute (using sh module, fi)
        # -- kali
        packet_loss = ping.quiet_ping(gateway)[0]
        logger.debug('packet loss %s' % packet_loss)
        if packet_loss > constants.MAX_ICMP_PACKET_LOSS:
            raise exceptions.NoConnectionToGateway

    def check_name_resolution(self, domain_name):
        try:
            socket.gethostbyname(domain_name)
            return True
        except socket.gaierror:
            raise exceptions.CannotResolveDomainError

    def parse_log_and_react(self, log, error_matrix=None):
        """
        compares the recent openvpn status log to
        strings passed in and executes the callbacks passed in.
        @param log: openvpn log
        @type log: list of strings
        @param error_matrix: tuples of strings and tuples of callbacks
        @type error_matrix: tuples strings and call backs
        """
        for line in log:
            # we could compile a regex here to save some cycles up -- kali
            for each in error_matrix:
                error, callbacks = each
                if error in line:
                    for cb in callbacks:
                        if callable(cb):
                            cb()
