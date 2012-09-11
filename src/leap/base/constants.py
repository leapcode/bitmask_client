"""constants to be used in base module"""
APP_NAME = "leap"

# default provider placeholder
# using `example.org` we make sure that this
# is not going to be resolved during the tests phases
# (we expect testers to add it to their /etc/hosts

DEFAULT_TEST_PROVIDER = "testprovider.example.org"

DEFINITION_EXPECTED_PATH = "provider-definition.json"

DEFAULT_PROVIDER_DEFINITION = {
    u'api_uri': u'https://api.testprovider.example.org/',
    u'api_version': u'0.1.0',
    u'ca_cert': u'8aab80ae4326fd30721689db813733783fe0bd7e',
    u'ca_cert_uri': u'https://testprovider.example.org/cacert.pem',
    u'description': {u'en': u'This is a test provider'},
    u'display_name': {u'en': u'Test Provider'},
    u'domain': u'testprovider.example.org',
    u'enrollment_policy': u'open',
    u'public_key': u'cb7dbd679f911e85bc2e51bd44afd7308ee19c21',
    u'serial': 1,
    u'services': [u'eip'],
    u'version': u'0.1.0'}

MAX_ICMP_PACKET_LOSS = 10
