"""all dealing with leap-providers: definition files, updating"""
import configuration

from leap.base.config import JSONLeapConfig

##########################################################
# hacking in progress:

# Specs are instances of configuration.Configuration class
# -yeah, that's an external app, not ours-
# and have to carry an options attr.
#
# Configs have:
# - a slug (from where a filename/folder is derived)
# - a spec (for validation and defaults).

# all config objects, as BaseConfig derived, implment basic
# useful methods:
# - save
# - load
# - get_config (returns a optparse.OptionParser object)

# TODO:
# - have a good type cast repertory (uris, version, hashes...)
# - raise validation errors
# - multilingual objects

##########################################################


class LeapProviderSpec(configuration.Configuration):
    options = {
        'serial': {
            'type': int,
            'default': 1,
            'required': True,
        },
        'version': {
            'type': unicode,
            'default': '0.1.0'
            #'required': True
        },
        'domain': {
            'type': unicode,  # XXX define uri type
            'default': 'testprovider.example.org'
            #'required': True,
        },
        'display_name': {
            'type': unicode,  # XXX multilingual object?
            'default': 'test provider'
            #'required': True
        },
        'description': {
            'default': 'test provider'
        },
        'enrollment_policy': {
            'type': unicode,  # oneof ??
            'default': 'open'
        },
        'services': {
            'type': list,  # oneof ??
            'default': ['eip']
        },
        'api_version': {
            'type': unicode,
            'default': '0.1.0'  # version regexp
        },
        'api_uri': {
            'type': unicode  # uri
        },
        'public_key': {
            'type': unicode  # fingerprint
        },
        'ca_cert': {
            'type': unicode
        },
        'ca_cert_uri': {
            'type': unicode
        },
    }


class LeapProviderDefinition(JSONLeapConfig):
    slug = 'definition.json'
    spec = LeapProviderSpec


class LeapProvider(object):
    # bring slug here (property)
    # constructor: pass name

    # constructor: init definition class
    # (__cls__.__name__ + Definition)
    # initializes a JSONLeapConfig with slug and
    # initializes also cls.name + Spec

    # and Abstract this thing out!

    # how can we hook here the network fetching stuff?
    # maybe (bstorming a little bit):

    # config = LeapProviderDefinition
    # fetcher = foo.FetcherClass
    pass


class LeapProviderSet(object):
    # we gather them from the filesystem
    def __init__(self):
        self.count = 0
