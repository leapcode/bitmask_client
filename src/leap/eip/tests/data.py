from __future__ import unicode_literals
import os

#from leap import __branding

# sample data used in tests

#PROVIDER = __branding.get('provider_domain')
PROVIDER = "testprovider.example.org"

EIP_SAMPLE_CONFIG = {
    "provider": "%s" % PROVIDER,
    "transport": "openvpn",
    "openvpn_protocol": "tcp",
    "openvpn_port": 80,
    "openvpn_ca_certificate": os.path.expanduser(
        "~/.config/leap/providers/"
        "%s/"
        "keys/ca/cacert.pem" % PROVIDER),
    "openvpn_client_certificate": os.path.expanduser(
        "~/.config/leap/providers/"
        "%s/"
        "keys/client/openvpn.pem" % PROVIDER),
    "connect_on_login": True,
    "block_cleartext_traffic": True,
    "primary_gateway": "location_unknown",
    "secondary_gateway": "location_unknown2",
    #"management_password": "oph7Que1othahwiech6J"
}

EIP_SAMPLE_SERVICE = {
    "serial": 1,
    "version": 1,
    "clusters": [
        {"label": {
            "en": "Location Unknown"},
            "name": "location_unknown"}
    ],
    "gateways": [
        {"capabilities": {
            "adblock": True,
            "filter_dns": True,
            "ports": ["80", "53", "443", "1194"],
            "protocols": ["udp", "tcp"],
            "transport": ["openvpn"],
            "user_ips": False},
         "cluster": "location_unknown",
         "host": "location.example.org",
         "ip_address": "192.0.43.10"}
    ]
}
