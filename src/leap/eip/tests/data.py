from __future__ import unicode_literals
import os

from leap import __branding

# sample data used in tests

PROVIDER = __branding.get('provider_domain')

EIP_SAMPLE_JSON = {
    "provider": "%s" % PROVIDER,
    "transport": "openvpn",
    "openvpn_protocol": "tcp",
    "openvpn_port": 80,
    "openvpn_ca_certificate": os.path.expanduser(
        "~/.config/leap/providers/"
        "%s/"
        "keys/ca/testprovider-ca-cert.pem" % PROVIDER),
    "openvpn_client_certificate": os.path.expanduser(
        "~/.config/leap/providers/"
        "%s/"
        "keys/client/openvpn.pem" % PROVIDER),
    "connect_on_login": True,
    "block_cleartext_traffic": True,
    "primary_gateway": "usa_west",
    "secondary_gateway": "france",
    #"management_password": "oph7Que1othahwiech6J"
}

EIP_SAMPLE_SERVICE = {
    "serial": 1,
    "version": "0.1.0",
    "capabilities": {
        "transport": ["openvpn"],
        "ports": ["80", "53"],
        "protocols": ["udp", "tcp"],
        "static_ips": True,
        "adblock": True
    },
    "gateways": [
    {"country_code": "us",
     "label": {"en":"west"},
     "capabilities": {},
     "hosts": ["1.2.3.4", "1.2.3.5"]},
    ]
}
