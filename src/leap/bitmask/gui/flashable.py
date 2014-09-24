# -*- coding: utf-8 -*-
# Copyright (C) 2014 LEAP
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


class Flashable(object):

    """
    An abstract super class to give a QWidget handy methods for diplaying
    alert messages inline. The widget inheriting from this class must have
    label named 'flash_label' available at self.ui.flash_label, or pass
    the QLabel object in the constructor.
    """

    def __init__(self, widget=None):
        self._setup(widget)

    def _setup(self, widget=None):
        if not hasattr(self, 'widget'):
            if widget:
                self.widget = widget
            else:
                self.widget = self.ui.flash_label
            self.widget.setVisible(False)

    def flash_error(self, message):
        """
        Sets string for the flash message.

        :param message: the text to be displayed
        :type message: str
        """
        self._setup()
        message = "<font color='red'><b>%s</b></font>" % (message,)
        self.widget.setVisible(True)
        self.widget.setText(message)

    def flash_success(self, message):
        """
        Sets string for the flash message.

        :param message: the text to be displayed
        :type message: str
        """
        self._setup()
        message = "<font color='green'><b>%s</b></font>" % (message,)
        self.widget.setVisible(True)
        self.widget.setText(message)

    def flash_message(self, message):
        """
        Sets string for the flash message.

        :param message: the text to be displayed
        :type message: str
        """
        self._setup()
        message = "<b>%s</b>" % (message,)
        self.widget.setVisible(True)
        self.widget.setText(message)

    def hide_flash(self):
        self._setup()
        self.widget.setVisible(False)
