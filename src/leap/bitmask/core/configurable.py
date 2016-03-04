# -*- coding: utf-8 -*-
# configurable.py
# Copyright (C) 2015, 2016 LEAP
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
Configurable Backend for Bitmask Service.
"""
import ConfigParser
import locale
import os
import re
import sys

from twisted.application import service
from twisted.python import log

from leap.common import files


class MissingConfigEntry(Exception):
    """
    A required config entry was not found.
    """


class ConfigurableService(service.MultiService):

    config_file = u"bitmaskd.cfg"
    service_names = ('mail', 'eip', 'zmq', 'web')

    def __init__(self, basedir='~/.config/leap'):
        service.MultiService.__init__(self)

        path = os.path.abspath(os.path.expanduser(basedir))
        if not os.path.isdir(path):
            files.mkdir_p(path)
        self.basedir = path

        # creates self.config
        self.read_config()

    def get_config(self, section, option, default=None, boolean=False):
        try:
            if boolean:
                return self.config.getboolean(section, option)

            item = self.config.get(section, option)
            return item

        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            if default is None:
                fn = os.path.join(self.basedir, self.config_file)
                raise MissingConfigEntry("%s is missing the [%s]%s entry"
                                         % (_quote_output(fn),
                                            section, option))
            return default

    def set_config(self, section, option, value):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)
        self.save_config()
        self.read_config()
        assert self.config.get(section, option) == value

    def read_config(self):
        self.config = ConfigParser.SafeConfigParser()
        bitmaskd_cfg = self._get_config_path()

        if not os.path.isfile(bitmaskd_cfg):
            self._create_default_config(bitmaskd_cfg)

        try:
            with open(bitmaskd_cfg, "rb") as f:
                self.config.readfp(f)
        except EnvironmentError:
            if os.path.exists(bitmaskd_cfg):
                raise

    def save_config(self):
        bitmaskd_cfg = self._get_config_path()
        with open(bitmaskd_cfg, 'wb') as f:
            self.config.write(f)

    def _create_default_config(self, path):
        with open(path, 'w') as outf:
            outf.write(DEFAULT_CONFIG)

    def _get_config_path(self):
        return os.path.join(self.basedir, self.config_file)


DEFAULT_CONFIG = """
[services]
mail = True
eip = True
zmq = True
web = False
"""


def canonical_encoding(encoding):
    if encoding is None:
        log.msg("Warning: falling back to UTF-8 encoding.", level=log.WEIRD)
        encoding = 'utf-8'
    encoding = encoding.lower()
    if encoding == "cp65001":
        encoding = 'utf-8'
    elif (encoding == "us-ascii" or encoding == "646" or encoding ==
          "ansi_x3.4-1968"):
        encoding = 'ascii'

    return encoding


def check_encoding(encoding):
    # sometimes Python returns an encoding name that it doesn't support for
    # conversion fail early if this happens
    try:
        u"test".encode(encoding)
    except (LookupError, AttributeError):
        raise AssertionError(
            "The character encoding '%s' is not supported for conversion." % (
                encoding,))

filesystem_encoding = None
io_encoding = None
is_unicode_platform = False


def _reload():
    global filesystem_encoding, io_encoding, is_unicode_platform

    filesystem_encoding = canonical_encoding(sys.getfilesystemencoding())
    check_encoding(filesystem_encoding)

    if sys.platform == 'win32':
        # On Windows we install UTF-8 stream wrappers for sys.stdout and
        # sys.stderr, and reencode the arguments as UTF-8 (see
        # scripts/runner.py).
        io_encoding = 'utf-8'
    else:
        ioenc = None
        if hasattr(sys.stdout, 'encoding'):
            ioenc = sys.stdout.encoding
        if ioenc is None:
            try:
                ioenc = locale.getpreferredencoding()
            except Exception:
                pass  # work around <http://bugs.python.org/issue1443504>
        io_encoding = canonical_encoding(ioenc)

    check_encoding(io_encoding)

    is_unicode_platform = sys.platform in ["win32", "darwin"]

_reload()


def _quote_output(s, quotemarks=True, quote_newlines=None, encoding=None):
    """
    Encode either a Unicode string or a UTF-8-encoded bytestring for
    representation on stdout or stderr, tolerating errors. If 'quotemarks' is
    True, the string is always quoted; otherwise, it is quoted only if
    necessary to avoid ambiguity or control bytes in the output. (Newlines are
    counted as control bytes iff quote_newlines is True.)

    Quoting may use either single or double quotes. Within single quotes, all
    characters stand for themselves, and ' will not appear. Within double
    quotes, Python-compatible backslash escaping is used.

    If not explicitly given, quote_newlines is True when quotemarks is True.
    """
    assert isinstance(s, (str, unicode))
    if quote_newlines is None:
        quote_newlines = quotemarks

    if isinstance(s, str):
        try:
            s = s.decode('utf-8')
        except UnicodeDecodeError:
            return 'b"%s"' % (
                ESCAPABLE_8BIT.sub(
                    lambda m: _str_escape(m, quote_newlines), s),)

    must_double_quote = (quote_newlines and MUST_DOUBLE_QUOTE_NL or
                         MUST_DOUBLE_QUOTE)
    if must_double_quote.search(s) is None:
        try:
            out = s.encode(encoding or io_encoding)
            if quotemarks or out.startswith('"'):
                return "'%s'" % (out,)
            else:
                return out
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass

    escaped = ESCAPABLE_UNICODE.sub(
        lambda m: _unicode_escape(m, quote_newlines), s)
    return '"%s"' % (
        escaped.encode(encoding or io_encoding, 'backslashreplace'),)


def _unicode_escape(m, quote_newlines):
    u = m.group(0)
    if u == u'"' or u == u'$' or u == u'`' or u == u'\\':
        return u'\\' + u
    elif u == u'\n' and not quote_newlines:
        return u
    if len(u) == 2:
        codepoint = (
            ord(u[0]) - 0xD800) * 0x400 + ord(u[1]) - 0xDC00 + 0x10000
    else:
        codepoint = ord(u)
    if codepoint > 0xFFFF:
        return u'\\U%08x' % (codepoint,)
    elif codepoint > 0xFF:
        return u'\\u%04x' % (codepoint,)
    else:
        return u'\\x%02x' % (codepoint,)


def _str_escape(m, quote_newlines):
    c = m.group(0)
    if c == '"' or c == '$' or c == '`' or c == '\\':
        return '\\' + c
    elif c == '\n' and not quote_newlines:
        return c
    else:
        return '\\x%02x' % (ord(c),)

MUST_DOUBLE_QUOTE_NL = re.compile(
    ur'[^\x20-\x26\x28-\x7E\u00A0-\uD7FF\uE000-\uFDCF\uFDF0-\uFFFC]',
    re.DOTALL)
MUST_DOUBLE_QUOTE = re.compile(
    ur'[^\n\x20-\x26\x28-\x7E\u00A0-\uD7FF\uE000-\uFDCF\uFDF0-\uFFFC]',
    re.DOTALL)

ESCAPABLE_8BIT = re.compile(
    r'[^ !#\x25-\x5B\x5D-\x5F\x61-\x7E]',
    re.DOTALL)

# if we must double-quote, then we have to escape ", $ and `, but need not
# escape '

ESCAPABLE_UNICODE = re.compile(
    ur'([\uD800-\uDBFF][\uDC00-\uDFFF])|'  # valid surrogate pairs
    ur'[^ !#\x25-\x5B\x5D-\x5F\x61-\x7E\u00A0-\uD7FF'
    ur'\uE000-\uFDCF\uFDF0-\uFFFC]',
    re.DOTALL)
