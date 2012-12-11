from __future__ import (unicode_literals)
import os

from leap import __branding
from leap.base import config as baseconfig

# XXX move provider stuff to base config

PROVIDER_CA_CERT = __branding.get(
    'provider_ca_file',
    'cacert.pem')

provider_ca_path = lambda domain: str(os.path.join(
    #baseconfig.get_default_provider_path(),
    baseconfig.get_provider_path(domain),
    'keys', 'ca',
    'cacert.pem'
)) if domain else None

default_provider_ca_path = lambda: str(os.path.join(
    baseconfig.get_default_provider_path(),
    'keys', 'ca',
    PROVIDER_CA_CERT
))

PROVIDER_DOMAIN = __branding.get('provider_domain', 'testprovider.example.org')


client_cert_path = lambda domain: unicode(os.path.join(
    baseconfig.get_provider_path(domain),
    'keys', 'client',
    'openvpn.pem'
)) if domain else None

default_client_cert_path = lambda: unicode(os.path.join(
    baseconfig.get_default_provider_path(),
    'keys', 'client',
    'openvpn.pem'
))

eipconfig_spec = {
    'description': 'sample eipconfig',
    'type': 'object',
    'properties': {
        'provider': {
            'type': unicode,
            'default': u"%s" % PROVIDER_DOMAIN,
            'required': True,
        },
        'transport': {
            'type': unicode,
            'default': u"openvpn",
        },
        'openvpn_protocol': {
            'type': unicode,
            'default': u"tcp"
        },
        'openvpn_port': {
            'type': int,
            'default': 80
        },
        'openvpn_ca_certificate': {
            'type': unicode,  # path
            'default': default_provider_ca_path
        },
        'openvpn_client_certificate': {
            'type': unicode,  # path
            'default': default_client_cert_path
        },
        'connect_on_login': {
            'type': bool,
            'default': True
        },
        'block_cleartext_traffic': {
            'type': bool,
            'default': True
        },
        'primary_gateway': {
            'type': unicode,
            'default': u"turkey",
            #'required': True
        },
        'secondary_gateway': {
            'type': unicode,
            'default': u"france"
        },
        'management_password': {
            'type': unicode
        }
    }
}

eipservice_config_spec = {
    'description': 'sample eip service config',
    'type': 'object',
    'properties': {
        'serial': {
            'type': int,
            'required': True,
            'default': 1
        },
        'version': {
            'type': unicode,
            'required': True,
            'default': "0.1.0"
        },
        'capabilities': {
            'type': dict,
            'default': {
                "transport": ["openvpn"],
                "ports": ["80", "53"],
                "protocols": ["udp", "tcp"],
                "static_ips": True,
                "adblock": True}
        },
        'gateways': {
            'type': list,
            'default': [{"country_code": "us",
                        "label": {"en":"west"},
                        "capabilities": {},
                        "hosts": ["1.2.3.4", "1.2.3.5"]}]
        },
        'openvpn_configuration': {
            'type': dict,
            'default': {
                "auth": None,
                "cipher": None,
                "tls-cipher": None}
        }
    }
}
