"""all dealing with leap-providers: definition files, updating"""
from leap.base.config import JSONLeapConfig
from leap.base import specs


class LeapProviderDefinition(JSONLeapConfig):
    slug = 'definition.json'
    spec = specs.leap_provider_spec


class LeapProviderSet(object):
    # we gather them from the filesystem
    # TODO: (MVS+)
    def __init__(self):
        self.count = 0
