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
