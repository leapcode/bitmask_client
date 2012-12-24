"""constants to be used in base module"""
from leap import __branding
APP_NAME = __branding.get("short_name", "leap")

# default provider placeholder
# using `example.org` we make sure that this
# is not going to be resolved during the tests phases
# (we expect testers to add it to their /etc/hosts

DEFAULT_PROVIDER = __branding.get(
    "provider_domain",
    "testprovider.example.org")

DEFINITION_EXPECTED_PATH = "provider.json"

DEFAULT_PROVIDER_DEFINITION = {
    u"api_uri": "https://api.%s/" % DEFAULT_PROVIDER,
    u"api_version": u"1",
    u"ca_cert_fingerprint": "SHA256: fff",
    u"ca_cert_uri": u"https://%s/ca.crt" % DEFAULT_PROVIDER,
    u"default_language": u"en",
    u"description": {
        u"en": u"A demonstration service provider using the LEAP platform"
    },
    u"domain": "%s" % DEFAULT_PROVIDER,
    u"enrollment_policy": u"open",
    u"languages": [
        u"en"
    ],
    u"name": {
        u"en": u"Test Provider"
    },
    u"services": [
        "openvpn"
    ]
}


MAX_ICMP_PACKET_LOSS = 10

ROUTE_CHECK_INTERVAL = 10
