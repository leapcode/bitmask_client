EIP_CONFIG = "eip.json"

EIP_SAMPLE_JSON = {
    "provider": "testprovider.example.org",
    "transport": "openvpn",
    "openvpn_protocol": "tcp",
    "openvpn_port": "80",
    "openvpn_ca_certificate": "~/.config/leap/providers/"
                              "testprovider.example.org/"
                              "keys/ca/testprovider-ca-cert-"
                              "2013-01-01.pem",
    "openvpn_client_certificate": "~/.config/leap/providers/"
                                  "testprovider.example.org/"
                                  "keys/client/openvpn-2012-09-31.pem",
    "connect_on_login": True,
    "block_cleartext_traffic": True,
    "primary_gateway": "usa_west",
    "secondary_gateway": "france",
    "management_password": "oph7Que1othahwiech6J"
}

EIP_SERVICE_EXPECTED_PATH = "eip-service.json"

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
    {"country_code": "us",
     "label": {"en":"east"},
     "capabilities": {},
     "hosts": ["1.2.3.4", "1.2.3.5"]},
    {"country_code": "fr",
     "label": {},
     "capabilities": {},
     "hosts": ["1.2.3.4", "1.2.3.5"]}
    ]
}
