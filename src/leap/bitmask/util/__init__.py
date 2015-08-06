# -*- coding: utf-8 -*-
# __init__.py
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
Some small and handy functions.
"""
import datetime
import itertools
import os
import sys

from leap.bitmask.config import flags
from leap.common.config import get_path_prefix as common_get_path_prefix

# functional goodies for a healthier life:
# We'll give your money back if it does not alleviate the eye strain, at least.


def first(things):
    """
    Return the head of a collection.

    :param things: a sequence to extract the head from.
    :type things: sequence
    :return: object, or None
    """
    try:
        return things[0]
    except (IndexError, TypeError):
        return None


def flatten(things):
    """
    Return a generator iterating through a flattened sequence.

    :param things: a nested sequence, eg, a list of lists.
    :type things: sequence
    :rtype: generator
    """
    return itertools.chain(*things)


# leap repetitive chores

def get_path_prefix():
    return common_get_path_prefix(flags.STANDALONE)


def get_modification_ts(path):
    """
    Gets modification time of a file.

    :param path: the path to get ts from
    :type path: str
    :returns: modification time
    :rtype: datetime object
    """
    ts = os.path.getmtime(path)
    return datetime.datetime.fromtimestamp(ts)


def update_modification_ts(path):
    """
    Sets modification time of a file to current time.

    :param path: the path to set ts to.
    :type path: str
    :returns: modification time
    :rtype: datetime object
    """
    os.utime(path, None)
    return get_modification_ts(path)


def is_file(path):
    """
    Returns True if the path exists and is a file.
    """
    return os.path.isfile(path)


def is_empty_file(path):
    """
    Returns True if the file at path is empty.
    """
    return os.stat(path).st_size is 0


def make_address(user, provider):
    """
    Return a full identifier for an user, as a email-like
    identifier.

    :param user: the username
    :type user: basestring
    :param provider: the provider domain
    :type provider: basestring
    """
    return "%s@%s" % (user, provider)


def force_eval(items):
    """
    Return a sequence that evaluates any callable in the sequence,
    instantiating it beforehand if the item is a class, and
    leaves the non-callable items without change.
    """
    def do_eval(thing):
        if isinstance(thing, type):
            return thing()()
        if callable(thing):
            return thing()
        return thing

    if isinstance(items, (list, tuple)):
        return map(do_eval, items)
    else:
        return do_eval(items)


def dict_to_flags(values):
    """
    Set the flags values given in the values dict.
    If a value isn't provided then use the already existing one.

    :param values: the values to set.
    :type values: dict.
    """
    for k, v in values.items():
        setattr(flags, k, v)


def flags_to_dict():
    """
    Get the flags values in a dict.

    :return: the values of flags into a dict.
    :rtype: dict.
    """
    items = [i for i in dir(flags) if i[0] != '_']
    values = dict((i, getattr(flags, i)) for i in items)

    return values

def here(module=None):
    if getattr(sys, 'frozen', False):
        # we are running in a |PyInstaller| bundle
        return sys._MEIPASS
    else:
        dirname = os.path.dirname
        if module:
	    return dirname(module.__file__)
        else:
            return dirname(__file__)
