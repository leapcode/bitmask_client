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
    u'api_uri': u'https://api.%s/' % DEFAULT_PROVIDER,
    u'api_version': u'0.1.0',
    u'ca_cert_fingerprint': u'8aab80ae4326fd30721689db813733783fe0bd7e',
    u'ca_cert_uri': u'https://%s/cacert.pem' % DEFAULT_PROVIDER,
    u'description': {u'en': u'This is a test provider'},
    u'display_name': {u'en': u'Test Provider'},
    u'domain': u'%s' % DEFAULT_PROVIDER,
    u'enrollment_policy': u'open',
    u'public_key': u'cb7dbd679f911e85bc2e51bd44afd7308ee19c21',
    u'serial': 1,
    u'services': [u'eip'],
    u'version': u'0.1.0'}

MAX_ICMP_PACKET_LOSS = 10

ROUTE_CHECK_INTERVAL = 10
