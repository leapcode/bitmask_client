"""all dealing with leap-providers: definition files, updating"""
from leap.base import config as baseconfig
from leap.base import specs


class LeapProviderDefinition(baseconfig.JSONLeapConfig):
    spec = specs.leap_provider_spec

    def get_slug(self):
        provider_path = baseconfig.get_default_provider_path()
        return baseconfig.get_config_file(
            'definition.json',
            folder=provider_path)

    def set_slug(self, *args, **kwargs):
        raise AttributeError("you cannot set slug")

    slug = property(get_slug, set_slug)

    # TODO (MVS+)
    # we will construct slug from providers/%s/definition.json
    # where %s is domain name. we can get that on __init__


class LeapProviderSet(object):
    # we gather them from the filesystem
    # TODO: (MVS+)
    def __init__(self):
        self.count = 0
