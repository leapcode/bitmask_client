"""
Configuration Base Class
"""
import configuration  # python configuration module, not local!
import os

from leap.eip import config as eip_config


class BaseLeapConfig(object):
    slug = None

    # XXX we have to enforce that we have a slug (via interface)
    # get property getter that raises NI..

    def save(self):
        raise NotImplementedError("abstract base class")

    def load(self):
        raise NotImplementedError("abstract base class")

    def get_config(self, *kwargs):
        raise NotImplementedError("abstract base class")

    #XXX todo: enable this property after
    #fixing name clash with "config" in use at
    #vpnconnection

    #@property
    #def config(self):
        #return self.get_config()

    def get_value(self, *kwargs):
        raise NotImplementedError("abstract base class")


class JSONLeapConfig(BaseLeapConfig):

    def __init__(self, *args, **kwargs):
        # sanity check
        assert self.slug is not None
        assert self.spec is not None
        assert issubclass(self.spec, configuration.Configuration)

        self._config = self.spec()
        self._config.parse_args(list(args))

    # mandatory baseconfig interface

    def save(self, to=None):
        if to is None:
            to = self.filename
        self._config.serialize(to)

    def load(self, fromfile=None):
        # load should get a much more generic
        # argument. it could be, f.i., from_uri,
        # and call to Fetcher

        if fromfile is None:
            fromfile = self.filename
        self._config.deserialize(fromfile)

    def get_config(self):
        return self._config.config

    # public methods

    def get_filename(self):
        return self._slug_to_filename()

    @property
    def filename(self):
        return self.get_filename()

    def _slug_to_filename(self):
        # is this going to work in winland if slug is "foo/bar" ?
        folder, filename = os.path.split(self.slug)
        # XXX fix import
        config_file = eip_config.get_config_file(filename, folder)
        return config_file
