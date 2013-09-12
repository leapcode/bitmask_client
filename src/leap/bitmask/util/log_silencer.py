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
import logging
import os
import re

from leap.common.config import get_path_prefix


class SelectiveSilencerFilter(logging.Filter):
    """
    Configurable filter for root leap logger.

    If you want to ignore components from the logging, just add them,
    one by line, to ~/.config/leap/leap.dev.conf
    """
    # TODO we can augment this by properly parsing the log-silencer file
    # and having different sections: ignore, levels, ...

    # TODO use ConfigParser to unify sections [log-ignore] [log-debug] etc

    CONFIG_NAME = "leap.dev.conf"

    # Components to be completely silenced in the main bitmask logs.
    # You probably should think twice before adding a component to
    # the tuple below. Only very well tested components should go here, and
    # only in those cases in which we gain more from silencing them than from
    # having their logs into the main log file that the user will likely send
    # to us.
    SILENCER_RULES = (
        'leap.common.events',
    )

    def __init__(self, standalone=False):
        """
        Tries to load silencer rules from the default path,
        or load from the SILENCER_RULES tuple if not found.
        """
        self.standalone = standalone
        self.rules = None
        if os.path.isfile(self._rules_path):
            self.rules = self._load_rules()
        if not self.rules:
            self.rules = self.SILENCER_RULES

    @property
    def _rules_path(self):
        """
        The configuration file for custom ignore rules.
        """
        return os.path.join(
            get_path_prefix(standalone=self.standalone),
            "leap", self.CONFIG_NAME)

    def _load_rules(self):
        """
        Loads a list of paths to be ignored from the logging.
        """
        lines = open(self._rules_path).readlines()
        return map(lambda line: re.sub('\s', '', line),
                   lines)

    def filter(self, record):
        """
        Implements the filter functionality for this Filter

        :param record: the record to be examined
        :type record: logging.LogRecord
        :returns: a bool indicating whether the record should be logged or not.
        :rtype: bool
        """
        if not self.rules:
            return True
        logger_path = record.name
        for path in self.rules:
            if logger_path.startswith(path):
                return False
        return True
