# -*- coding: utf-8 -*-
#
# Copyright (C) 2013,2014 LEAP
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
#

"""
An instance of class Providers, held by mainwindow, is responsible for
managing the current provider and the combobox provider list.
"""

from collections import deque
from PySide import QtCore


class Providers(QtCore.QObject):

    # Emitted when the user changes the provider combobox index. The object
    # parameter is actually a boolean value that is True if "Other..." was
    # selected, False otherwse
    _provider_changed = QtCore.Signal(object)

    def __init__(self, providers_combo):
        """
        :param providers_combo: combo widget that lists providers
        :type providers_combo: QWidget
        """
        QtCore.QObject.__init__(self)
        self._providers_indexes = deque(maxlen=2)  # previous and current
        self._providers_indexes.append(-1)
        self._combo = providers_combo
        self._combo.currentIndexChanged.connect(
            self._current_provider_changed)

    def set_providers(self, provider_list):
        """
        Set the provider list to provider_list plus an "Other..." item
        that triggers the wizard

        :param provider_list: list of providers
        :type provider_list: list of str
        """
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(provider_list + [self.tr("Other...")])
        self._combo.blockSignals(False)

    def select_provider_by_name(self, name):
        """
        Given a provider name/domain, it selects it in the combobox

        :param name: name or domain for the provider
        :type name: unicode str
        """
        provider_index = self._combo.findText(name)
        self._providers_indexes.append(provider_index)

        # block the signals during a combobox change since we don't want to
        # trigger the default signal that makes the UI ask the user for
        # confirmation
        self._combo.blockSignals(True)
        self._combo.setCurrentIndex(provider_index)
        self._combo.blockSignals(False)

    def get_selected_provider(self):
        """
        Returns the selected provider in the combobox

        :rtype: unicode str
        """
        return self._combo.currentText()

    def connect_provider_changed(self, callback):
        """
        Connects callback to provider_changed signal
        """
        self._provider_changed.connect(callback)

    def restore_previous_provider(self):
        """
        Set as selected provider the one that was selected previously.
        """
        prev_provider = self._providers_indexes.popleft()
        self._providers_indexes.append(prev_provider)
        self._combo.blockSignals(True)
        self._combo.setCurrentIndex(prev_provider)
        self._combo.blockSignals(False)

    @QtCore.Slot(int)
    def _current_provider_changed(self, idx):
        """
        TRIGGERS:
            self._combo.currentIndexChanged

        :param idx: the index of the new selected item
        :type idx: int
        """
        self._providers_indexes.append(idx)
        is_wizard = idx == (self._combo.count() - 1)
        self._provider_changed.emit(is_wizard)
        if is_wizard:
            self.restore_previous_provider()
