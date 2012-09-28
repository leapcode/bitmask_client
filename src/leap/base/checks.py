# -*- coding: utf-8 -*-

import logging
import platform

import ping
import requests

from leap.base import constants
from leap.base import exceptions

logger = logging.getLogger(name=__name__)

class LeapNetworkChecker(object):
    """
    all network related checks
    """
    # TODO eventually, use a more portable solution
    # like psutil

    def run_all(self, checker=None):
        if not checker:
            checker = self
        self.error = None  # ?

        # for MVS
        checker.check_tunnel_default_interface()
        checker.check_internet_connection()
        checker.is_internet_up()
        checker.ping_gateway()

    def check_internet_connection(self):
        try:
            # XXX remove this hardcoded random ip
            requests.get('http://216.172.161.165')
        except (requests.HTTPError, requests.RequestException) as e:
            raise exceptions.NoInternetConnection(e.message)
        except requests.ConnectionError as e:
            error = "Unidentified Connection Error"
            if e.message == "[Errno 113] No route to host":
                if not self.is_internet_up():
                    error = "No valid internet connection found."
                else:
                    error = "Provider server appears to be down."
            raise exceptions.NoInternetConnection(error)
        logger.debug('Network appears to be up.')

    def is_internet_up(self):
        iface, gateway = self.get_default_interface_gateway()
        self.ping_gateway(self)

    def check_tunnel_default_interface(self):
        """
        Raises an TunnelNotDefaultRouteError 
        (including when no routes are present)
        """
        if not platform.system() == "Linux":
            raise NotImplementedError

        f = open("/proc/net/route")
        route_table = f.readlines()
        f.close()
        #toss out header
        route_table.pop(0)

        if not route_table:
            raise exceptions.TunnelNotDefaultRouteError()

        line = route_table.pop(0)
        iface, destination = line.split('\t')[0:2]
        if not destination == '00000000' or not iface == 'tun0':
            raise exceptions.TunnelNotDefaultRouteError()


    def get_default_interface_gateway(self):
        """only impletemented for linux so far."""
        if not platform.system() == "Linux":
            raise NotImplementedError

        f = open("/proc/net/route")
        route_table = f.readlines()
        f.close()
        #toss out header
        route_table.pop(0)

        default_iface = None
        gateway = None
        while route_table:
            line = route_table.pop(0)
            iface, destination, gateway = line.split('\t')[0:3]
            if destination == '00000000':
                default_iface = iface
                break

        if not default_iface:
            raise exceptions.NoDefaultInterfaceFoundError

        if default_iface not in netifaces.interfaces():
            raise exceptions.InterfaceNotFoundError

        return default_iface, gateway

    def ping_gateway(self, gateway):
        #TODO: Discuss how much packet loss (%) is acceptable.
        packet_loss = ping.quiet_ping(gateway)[0]
        if packet_loss > constants.MAX_ICMP_PACKET_LOSS:
            raise exceptions.NoConnectionToGateway
