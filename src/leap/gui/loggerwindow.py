# -*- coding: utf-8 -*-
# loggerwindow.py
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
History log window
"""
import logging

from PySide import QtGui
from ui_loggerwindow import Ui_LoggerWindow
from leap.common.check import leap_assert, leap_assert_type
from leap.util.leap_log_handler import LeapLogHandler

logger = logging.getLogger(__name__)


class LoggerWindow(QtGui.QDialog):
    """
    Window that displays a history of the logged messages in the app.
    """
    def __init__(self, handler):
        """
        Initialize the widget with the custom handler.

        :param handler: Custom handler that supports history and signal.
        :type handler: LeapLogHandler.
        """
        QtGui.QDialog.__init__(self)
        leap_assert(handler, "We need a handler for the logger window")
        leap_assert_type(handler, LeapLogHandler)

        # Load UI
        self.ui = Ui_LoggerWindow()
        self.ui.setupUi(self)

        # Make connections
        self.ui.btnSave.clicked.connect(self._save_log_to_file)
        self.ui.btnDebug.toggled.connect(self._load_history),
        self.ui.btnInfo.toggled.connect(self._load_history),
        self.ui.btnWarning.toggled.connect(self._load_history),
        self.ui.btnError.toggled.connect(self._load_history),
        self.ui.btnCritical.toggled.connect(self._load_history)

        # Load logging history and connect logger with the widget
        self._logging_handler = handler
        self._connect_to_handler()
        self._load_history()

    def _connect_to_handler(self):
        """
        This method connects the loggerwindow with the handler through a
        signal communicate the logger events.
        """
        self._logging_handler.new_log.connect(self._add_log_line)

    def _add_log_line(self, log):
        """
        Adds a line to the history, only if it's in the desired levels to show.

        :param log: a log record to be inserted in the widget
        :type log: a dict with RECORD_KEY and MESSAGE_KEY.
            the record contains the LogRecord of the logging module,
            the message contains the formatted message for the log.
        """
        html_style = {
            logging.DEBUG: "background: #CDFFFF;",
            logging.INFO: "background: white;",
            logging.WARNING: "background: #FFFF66;",
            logging.ERROR: "background: red; color: white;",
            logging.CRITICAL: "background: red; color: white; font: bold;"
        }
        level = log[LeapLogHandler.RECORD_KEY].levelno
        message = log[LeapLogHandler.MESSAGE_KEY]
        message = message.replace('\n', '<br>\n')

        if self._logs_to_display[level]:
            open_tag = "<tr style='" + html_style[level] + "'>"
            open_tag += "<td width='100%' style='padding: 5px;'>"
            close_tag = "</td></tr>"
            message = open_tag + message + close_tag

            self.ui.txtLogHistory.append(message)

    def _load_history(self):
        """
        Load the previous logged messages in the widget.
        They are stored in the custom handler.
        """
        self._set_logs_to_display()
        self.ui.txtLogHistory.clear()
        history = self._logging_handler.log_history
        for line in history:
            self._add_log_line(line)

    def _set_logs_to_display(self):
        """
        Sets the logs_to_display dict getting the toggled options from the ui
        """
        self._logs_to_display = {
            logging.DEBUG: self.ui.btnDebug.isChecked(),
            logging.INFO: self.ui.btnInfo.isChecked(),
            logging.WARNING: self.ui.btnWarning.isChecked(),
            logging.ERROR: self.ui.btnError.isChecked(),
            logging.CRITICAL: self.ui.btnCritical.isChecked()
        }

    def _save_log_to_file(self):
        """
        Lets the user save the current log to a file
        """
        fileName, filtr = QtGui.QFileDialog.getSaveFileName(
            self, self.tr("Save As"))

        if fileName:
            try:
                with open(fileName, 'w') as output:
                    output.write(self.ui.txtLogHistory.toPlainText())
                    output.write('\n')
                logger.debug('Log saved in %s' % (fileName, ))
            except IOError, e:
                logger.error("Error saving log file: %r" % (e, ))
        else:
            logger.debug('Log not saved!')
