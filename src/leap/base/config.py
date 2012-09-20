"""
Configuration Base Class
"""
import grp
import json
import logging
import socket
import tempfile
import os

logger = logging.getLogger(name=__name__)
logger.setLevel('DEBUG')

import configuration
import requests

from leap.base import exceptions
from leap.base import constants
from leap.util.fileutil import (mkdir_p)

# move to base!
from leap.eip import exceptions as eipexceptions


class BaseLeapConfig(object):
    slug = None

    # XXX we have to enforce that every derived class
    # has a slug (via interface)
    # get property getter that raises NI..

    def save(self):
        raise NotImplementedError("abstract base class")

    def load(self):
        raise NotImplementedError("abstract base class")

    def get_config(self, *kwargs):
        raise NotImplementedError("abstract base class")

    @property
    def config(self):
        return self.get_config()

    def get_value(self, *kwargs):
        raise NotImplementedError("abstract base class")


class MetaConfigWithSpec(type):
    """
    metaclass for JSONLeapConfig classes.
    It creates a configuration spec out of
    the `spec` dictionary.
    """
    # XXX in the near future, this is the
    # place where we want to enforce
    # singletons, read-only and stuff.

    # TODO:
    # - add a error handler for missing options that
    #   we can act easily upon (sys.exit is ugly, for $deity's sake)

    def __new__(meta, classname, bases, classDict):
        spec_options = classDict.get('spec', None)
        # not quite happy with this workaround.
        # I want to raise if missing spec dict, but only
        # for grand-children of this metaclass.
        # maybe should use abc module for this.
        abcderived = ("JSONLeapConfig",)
        if spec_options is None and classname not in abcderived:
            raise exceptions.ImproperlyConfigured(
                "missing spec dict on your derived class")

        # we create a configuration spec attribute from the spec dict
        config_class = type(
            classname + "Spec",
            (configuration.Configuration, object),
            {'options': spec_options})
        classDict['spec'] = config_class

        return type.__new__(meta, classname, bases, classDict)

##########################################################
# hacking in progress:

# Configs have:
# - a slug (from where a filename/folder is derived)
# - a spec (for validation and defaults).
#   this spec is basically a dict that will be used
#   for type casting and validation, and defaults settings.

# all config objects, since they are derived from  BaseConfig, implement basic
# useful methods:
# - save
# - load
# - get_config (returns a optparse.OptionParser object)

# TODO:
# - have a good type cast repertory (uris, version, hashes...)
# - raise validation errors
# - multilingual objects

##########################################################


class JSONLeapConfig(BaseLeapConfig):

    __metaclass__ = MetaConfigWithSpec

    def __init__(self, *args, **kwargs):
        # sanity check
        try:
            assert self.slug is not None
        except AssertionError:
            raise exceptions.ImproperlyConfigured(
                "missing slug on JSONLeapConfig"
                " derived class")
        try:
            assert self.spec is not None
        except AssertionError:
            raise exceptions.ImproperlyConfigured(
                "missing spec on JSONLeapConfig"
                " derived class")
        assert issubclass(self.spec, configuration.Configuration)

        self._config = self.spec()
        self._config.parse_args(list(args))
        self.fetcher = kwargs.pop('fetcher', requests)

    # mandatory baseconfig interface

    def save(self, to=None):
        if to is None:
            to = self.filename
        folder, filename = os.path.split(to)
        if folder and not os.path.isdir(folder):
            mkdir_p(folder)
        # lazy evaluation until first level of nesting
        # to allow lambdas with context-dependant info
        # like os.path.expanduser
        config = self.get_config()
        for k, v in config.iteritems():
            if callable(v):
                config[k] = v()
        self._config.serialize(to)

    def load(self, fromfile=None, from_uri=None, fetcher=None, verify=False):
        if from_uri is not None:
            fetched = self.fetch(from_uri, fetcher=fetcher, verify=verify)
            if fetched:
                return
        if fromfile is None:
            fromfile = self.filename
        newconfig = self._config.deserialize(fromfile)
        # XXX check for no errors, etc
        self._config.config = newconfig

    def fetch(self, uri, fetcher=None, verify=True):
        if not fetcher:
            fetcher = self.fetcher
        logger.debug('verify: %s', verify)
        request = fetcher.get(uri, verify=verify)

        # XXX get 404, ...
        # and raise a UnableToFetch...
        request.raise_for_status()
        fd, fname = tempfile.mkstemp(suffix=".json")
        if not request.json:
            try:
                json.loads(request.content)
            except ValueError:
                raise eipexceptions.LeapBadConfigFetchedError
        with open(fname, 'w') as tmp:
            tmp.write(json.dumps(request.json))
        self._loadtemp(fname)
        return True

    def get_config(self):
        return self._config.config

    # public methods

    def get_filename(self):
        return self._slug_to_filename()

    @property
    def filename(self):
        return self.get_filename()

    # private

    def _loadtemp(self, filename):
        self.load(fromfile=filename)
        os.remove(filename)

    def _slug_to_filename(self):
        # is this going to work in winland if slug is "foo/bar" ?
        folder, filename = os.path.split(self.slug)
        # XXX fix import
        config_file = get_config_file(filename, folder)
        return config_file

    def exists(self):
        return os.path.isfile(self.filename)


#
# utility functions
#
# (might be moved to some class as we see fit, but
# let's remain functional for a while)
# maybe base.config.util ??
#


def get_config_dir():
    """
    get the base dir for all leap config
    @rparam: config path
    @rtype: string
    """
    # TODO
    # check for $XDG_CONFIG_HOME var?
    # get a more sensible path for win/mac
    # kclair: opinion? ^^
    return os.path.expanduser(
        os.path.join('~',
                     '.config',
                     'leap'))


def get_config_file(filename, folder=None):
    """
    concatenates the given filename
    with leap config dir.
    @param filename: name of the file
    @type filename: string
    @rparam: full path to config file
    """
    path = []
    path.append(get_config_dir())
    if folder is not None:
        path.append(folder)
    path.append(filename)
    return os.path.join(*path)


def get_default_provider_path():
    default_subpath = os.path.join("providers",
                                   constants.DEFAULT_PROVIDER)
    default_provider_path = get_config_file(
        '',
        folder=default_subpath)
    return default_provider_path


def validate_ip(ip_str):
    """
    raises exception if the ip_str is
    not a valid representation of an ip
    """
    socket.inet_aton(ip_str)


def get_username():
    return os.getlogin()


def get_groupname():
    gid = os.getgroups()[-1]
    return grp.getgrgid(gid).gr_name
