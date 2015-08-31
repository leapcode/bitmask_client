# -*- coding: utf-8 -*-
# log_silencer.py
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
Filter for leap logs.
"""
import os

from leap.bitmask.util import get_path_prefix


class SelectiveSilencerFilter(object):
    """
    Configurable log filter for a Logbook logger.

    To include certain logs add them to:
    ~/.config/leap/leap_log_inclusion.dev.conf

    To exclude certain logs add them to:
    ~/.config/leap/leap_log_exclusion.dev.conf

    The log filtering is based on how the module name starts.
    In case of no inclusion or exclusion files are detected the default rules
    will be used.
    """
    # TODO we can augment this by properly parsing the log-silencer file
    # and having different sections: ignore, levels, ...

    # TODO use ConfigParser to unify sections [log-ignore] [log-debug] etc

    INCLUSION_CONFIG_FILE = "leap_log_inclusion.dev.conf"
    EXCLUSION_CONFIG_FILE = "leap_log_exclusion.dev.conf"

    # Components to be completely silenced in the main bitmask logs.
    # You probably should think twice before adding a component to
    # the tuple below. Only very well tested components should go here, and
    # only in those cases in which we gain more from silencing them than from
    # having their logs into the main log file that the user will likely send
    # to us.
    EXCLUSION_RULES = (
        'leap.common.events',
        'leap.common.decorators',
    )

    # This tuple list the module names that we want to display, any different
    # namespace will be filtered out.
    INCLUSION_RULES = (
        '__main__',
        'leap.',  # right now we just want to include logs from leap modules
        'twisted.',
    )

    def __init__(self):
        """
        Tries to load silencer rules from the default path,
        or load from the SILENCER_RULES tuple if not found.
        """
        self._inclusion_path = os.path.join(get_path_prefix(), "leap",
                                            self.INCLUSION_CONFIG_FILE)

        self._exclusion_path = os.path.join(get_path_prefix(), "leap",
                                            self.EXCLUSION_CONFIG_FILE)

        self._load_rules()

    def _load_rules(self):
        """
        Load the inclusion and exclusion rules from the config files.
        """
        try:
            with open(self._inclusion_path) as f:
                self._inclusion_rules = f.read().splitlines()
        except IOError:
            self._inclusion_rules = self.INCLUSION_RULES

        try:
            with open(self._exclusion_path) as f:
                self._exclusion_rules = f.read().splitlines()
        except IOError:
            self._exclusion_rules = self.EXCLUSION_RULES

    def filter(self, record, handler):
        """
        Implements the filter functionality for this Filter

        :param record: the record to be examined
        :type record: logging.LogRecord
        :returns: a bool indicating whether the record should be logged or not.
        :rtype: bool
        """
        if not self._inclusion_rules and not self._exclusion_rules:
            return True  # do not filter if there are no rules

        logger_path = record.module
        if logger_path is None:
            return True  # we can't filter if there is no module info

        # exclude paths that ARE NOT listed in ANY of the inclusion rules
        match = False
        for path in self._inclusion_rules:
            if logger_path.startswith(path):
                match = True

        if not match:
            return False

        # exclude paths that ARE listed in the exclusion rules
        for path in self._exclusion_rules:
            if logger_path.startswith(path):
                return False

        return True
