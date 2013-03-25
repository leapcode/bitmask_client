# -*- coding: utf-8 -*-
# pluggableconfig.py
# Copyright (C) 2013 LEAP
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
generic configuration handlers
"""
import copy
import json
import logging
import os
import time
import urlparse

import jsonschema

#from leap.base.util.translations import LEAPTranslatable
from leap.common.check import leap_assert


logger = logging.getLogger(__name__)


__all__ = ['PluggableConfig',
           'adaptors',
           'types',
           'UnknownOptionException',
           'MissingValueException',
           'ConfigurationProviderException',
           'TypeCastException']

# exceptions


class UnknownOptionException(Exception):
    """exception raised when a non-configuration
    value is present in the configuration"""


class MissingValueException(Exception):
    """exception raised when a required value is missing"""


class ConfigurationProviderException(Exception):
    """exception raised when a configuration provider is missing, etc"""


class TypeCastException(Exception):
    """exception raised when a
    configuration item cannot be coerced to a type"""


class ConfigAdaptor(object):
    """
    abstract base class for config adaotors for
    serialization/deserialization and custom validation
    and type casting.
    """
    def read(self, filename):
        raise NotImplementedError("abstract base class")

    def write(self, config, filename):
        with open(filename, 'w') as f:
            self._write(f, config)

    def _write(self, fp, config):
        raise NotImplementedError("abstract base class")

    def validate(self, config, schema):
        raise NotImplementedError("abstract base class")


adaptors = {}


class JSONSchemaEncoder(json.JSONEncoder):
    """
    custom default encoder that
    casts python objects to json objects for
    the schema validation
    """
    def default(self, obj):
        if obj is str:
            return 'string'
        if obj is unicode:
            return 'string'
        if obj is int:
            return 'integer'
        if obj is list:
            return 'array'
        if obj is dict:
            return 'object'
        if obj is bool:
            return 'boolean'


class JSONAdaptor(ConfigAdaptor):
    indent = 2
    extensions = ['json']

    def read(self, _from):
        if isinstance(_from, file):
            _from_string = _from.read()
        if isinstance(_from, str):
            _from_string = _from
        return json.loads(_from_string)

    def _write(self, fp, config):
        fp.write(json.dumps(config,
                 indent=self.indent,
                 sort_keys=True))

    def validate(self, config, schema_obj):
        schema_json = JSONSchemaEncoder().encode(schema_obj)
        schema = json.loads(schema_json)
        jsonschema.validate(config, schema)


adaptors['json'] = JSONAdaptor()

#
# Adaptors
#
# Allow to apply a predefined set of types to the
# specs, so it checks the validity of formats and cast it
# to proper python types.

# TODO:
# - HTTPS uri


class DateType(object):
    fmt = '%Y-%m-%d'

    def to_python(self, data):
        return time.strptime(data, self.fmt)

    def get_prep_value(self, data):
        return time.strftime(self.fmt, data)


class TranslatableType(object):
    """
    a type that casts to LEAPTranslatable objects.
    Used for labels we get from providers and stuff.
    """

    def to_python(self, data):
        # TODO: add translatable
        return data  # LEAPTranslatable(data)

    # needed? we already have an extended dict...
    #def get_prep_value(self, data):
        #return dict(data)


class URIType(object):

    def to_python(self, data):
        parsed = urlparse.urlparse(data)
        if not parsed.scheme:
            raise TypeCastException("uri %s has no schema" % data)
        return parsed.geturl()

    def get_prep_value(self, data):
        return data


class HTTPSURIType(object):

    def to_python(self, data):
        parsed = urlparse.urlparse(data)
        if not parsed.scheme:
            raise TypeCastException("uri %s has no schema" % data)
        if parsed.scheme != "https":
            raise TypeCastException(
                "uri %s does not has "
                "https schema" % data)
        return parsed.geturl()

    def get_prep_value(self, data):
        return data


types = {
    'date': DateType(),
    'uri': URIType(),
    'https-uri': HTTPSURIType(),
    'translatable': TranslatableType(),
}


class PluggableConfig(object):

    options = {}

    def __init__(self,
                 adaptors=adaptors,
                 types=types,
                 format=None):

        self.config = {}
        self.adaptors = adaptors
        self.types = types
        self._format = format
        self.mtime = None
        self.dirty = False

    @property
    def option_dict(self):
        if hasattr(self, 'options') and isinstance(self.options, dict):
            return self.options.get('properties', None)

    def items(self):
        """
        act like an iterator
        """
        if isinstance(self.option_dict, dict):
            return self.option_dict.items()
        return self.options

    def validate(self, config, format=None):
        """
        validate config
        """
        schema = self.options
        if format is None:
            format = self._format

        if format:
            adaptor = self.get_adaptor(self._format)
            adaptor.validate(config, schema)
        else:
            # we really should make format mandatory...
            logger.error('no format passed to validate')

        # first round of validation is ok.
        # now we proceed to cast types if any specified.
        self.to_python(config)

    def to_python(self, config):
        """
        cast types following first type and then format indications.
        """
        unseen_options = [i for i in config if i not in self.option_dict]
        if unseen_options:
            raise UnknownOptionException(
                "Unknown options: %s" % ', '.join(unseen_options))

        for key, value in config.items():
            _type = self.option_dict[key].get('type')
            if _type is None and 'default' in self.option_dict[key]:
                _type = type(self.option_dict[key]['default'])
            if _type is not None:
                tocast = True
                if not callable(_type) and isinstance(value, _type):
                    tocast = False
                if tocast:
                    try:
                        config[key] = _type(value)
                    except BaseException, e:
                        raise TypeCastException(
                            "Could not coerce %s, %s, "
                            "to type %s: %s" % (key, value, _type.__name__, e))
            _format = self.option_dict[key].get('format', None)
            _ftype = self.types.get(_format, None)
            if _ftype:
                try:
                    config[key] = _ftype.to_python(value)
                except BaseException, e:
                    raise TypeCastException(
                        "Could not coerce %s, %s, "
                        "to format %s: %s" % (key, value,
                        _ftype.__class__.__name__,
                        e))

        return config

    def prep_value(self, config):
        """
        the inverse of to_python method,
        called just before serialization
        """
        for key, value in config.items():
            _format = self.option_dict[key].get('format', None)
            _ftype = self.types.get(_format, None)
            if _ftype and hasattr(_ftype, 'get_prep_value'):
                try:
                    config[key] = _ftype.get_prep_value(value)
                except BaseException, e:
                    raise TypeCastException(
                        "Could not serialize %s, %s, "
                        "by format %s: %s" % (key, value,
                        _ftype.__class__.__name__,
                        e))
            else:
                config[key] = value
        return config

    # methods for adding configuration

    def get_default_values(self):
        """
        return a config options from configuration defaults
        """
        defaults = {}
        for key, value in self.items():
            if 'default' in value:
                defaults[key] = value['default']
        return copy.deepcopy(defaults)

    def get_adaptor(self, format):
        """
        get specified format adaptor or
        guess for a given filename
        """
        adaptor = self.adaptors.get(format, None)
        if adaptor:
            return adaptor

        # not registered in adaptors dict, let's try all
        for adaptor in self.adaptors.values():
            if format in adaptor.extensions:
                return adaptor

    def filename2format(self, filename):
        extension = os.path.splitext(filename)[-1]
        return extension.lstrip('.') or None

    def serialize(self, filename, format=None, full=False):
        if not format:
            format = self._format
        if not format:
            format = self.filename2format(filename)
        if not format:
            raise Exception('Please specify a format')
            # TODO: more specific exception type

        adaptor = self.get_adaptor(format)
        if not adaptor:
            raise Exception("Adaptor not found for format: %s" % format)

        config = copy.deepcopy(self.config)
        serializable = self.prep_value(config)
        adaptor.write(serializable, filename)

        if self.mtime:
            self.touch_mtime(filename)

    def touch_mtime(self, filename):
        mtime = self.mtime
        os.utime(filename, (mtime, mtime))

    def deserialize(self, string=None, fromfile=None, format=None):
        """
        load configuration from a file or string
        """

        def _try_deserialize():
            if fromfile:
                with open(fromfile, 'r') as f:
                    content = adaptor.read(f)
            elif string:
                content = adaptor.read(string)
            return content

        # XXX cleanup this!

        if fromfile:
            leap_assert(os.path.exists(fromfile))
            if not format:
                format = self.filename2format(fromfile)

        if not format:
            format = self._format
        if format:
            adaptor = self.get_adaptor(format)
        else:
            adaptor = None

        if adaptor:
            content = _try_deserialize()
            return content

        # no adaptor, let's try rest of adaptors

        adaptors = self.adaptors[:]

        if format:
            adaptors.sort(
                key=lambda x: int(
                    format in x.extensions),
                reverse=True)

        for adaptor in adaptors:
            content = _try_deserialize()
        return content

    def set_dirty(self):
        self.dirty = True

    def is_dirty(self):
        return self.dirty

    def load(self, *args, **kwargs):
        """
        load from string or file
        if no string of fromfile option is given,
        it will attempt to load from defaults
        defined in the schema.
        """
        string = args[0] if args else None
        fromfile = kwargs.get("fromfile", None)
        mtime = kwargs.pop("mtime", None)
        self.mtime = mtime
        content = None

        # start with defaults, so we can
        # have partial values applied.
        content = self.get_default_values()
        if string and isinstance(string, str):
            content = self.deserialize(string)

        if not string and fromfile is not None:
            #import ipdb;ipdb.set_trace()
            content = self.deserialize(fromfile=fromfile)

        if not content:
            logger.error('no content could be loaded')
            # XXX raise!
            return

        # lazy evaluation until first level of nesting
        # to allow lambdas with context-dependant info
        # like os.path.expanduser
        for k, v in content.iteritems():
            if callable(v):
                content[k] = v()

        self.validate(content)
        self.config = content
        return True


def testmain():  # pragma: no cover

    from tests import test_validation as t
    import pprint

    config = PluggableConfig(_format="json")
    properties = copy.deepcopy(t.sample_spec)

    config.options = properties
    config.load(fromfile='data.json')

    print 'config'
    pprint.pprint(config.config)

    config.serialize('/tmp/testserial.json')

if __name__ == "__main__":
    testmain()
