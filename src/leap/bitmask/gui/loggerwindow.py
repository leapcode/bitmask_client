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
import cgi

from PySide import QtCore, QtGui
from twisted.internet import threads

from ui_loggerwindow import Ui_LoggerWindow

from leap.bitmask.util.constants import PASTEBIN_API_DEV_KEY
from leap.bitmask.logs.leap_log_handler import LeapLogHandler
from leap.bitmask.util import pastebin
from leap.common.check import leap_assert, leap_assert_type

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
        from twisted.internet import reactor
        self.reactor = reactor

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
        self.ui.leFilterBy.textEdited.connect(self._filter_by)
        self.ui.cbCaseInsensitive.stateChanged.connect(self._load_history)
        self.ui.btnPastebin.clicked.connect(self._pastebin_this)

        self._current_filter = ""
        self._current_history = ""

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
        message = cgi.escape(log[LeapLogHandler.MESSAGE_KEY])

        if self._logs_to_display[level]:
            open_tag = "<tr style='" + html_style[level] + "'>"
            open_tag += "<td width='100%' style='padding: 5px;'>"
            close_tag = "</td></tr>"
            message = open_tag + message + close_tag

            filter_by = self._current_filter
            msg = message
            if self.ui.cbCaseInsensitive.isChecked():
                msg = msg.upper()
                filter_by = filter_by.upper()

            if msg.find(filter_by) != -1:
                self.ui.txtLogHistory.append(message)

    def _load_history(self):
        """
        Load the previous logged messages in the widget.
        They are stored in the custom handler.
        """
        self._set_logs_to_display()
        self.ui.txtLogHistory.clear()
        history = self._logging_handler.log_history
        current_history = []
        for line in history:
            self._add_log_line(line)
            message = line[LeapLogHandler.MESSAGE_KEY]
            current_history.append(message)

        self._current_history = "\n".join(current_history)

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

    def _filter_by(self, text):
        """
        Sets the text to use for filtering logs in the log window.

        :param text: the text to compare with the logs when filtering.
        :type text: str
        """
        self._current_filter = text
        self._load_history()

    def _save_log_to_file(self):
        """
        Lets the user save the current log to a file
        """
        fileName, filtr = QtGui.QFileDialog.getSaveFileName(
            self, self.tr("Save As"),
            options=QtGui.QFileDialog.DontUseNativeDialog)

        if fileName:
            try:
                with open(fileName, 'w') as output:
                    history = self.ui.txtLogHistory.toPlainText()
                    # Chop some \n.
                    # html->plain adds several \n because the html is made
                    # using table cells.
                    history = history.replace('\n\n\n', '\n')

                    output.write(history)
                logger.debug('Log saved in %s' % (fileName, ))
            except IOError, e:
                logger.error("Error saving log file: %r" % (e, ))
        else:
            logger.debug('Log not saved!')

    def _set_pastebin_sending(self, sending):
        """
        Define the status of the pastebin button.
        Change the text and enable/disable according to the current action.

        :param sending: if we are sending to pastebin or not.
        :type sending: bool
        """
        if sending:
            self.ui.btnPastebin.setText(self.tr("Sending to pastebin..."))
            self.ui.btnPastebin.setEnabled(False)
        else:
            self.ui.btnPastebin.setText(self.tr("Send to Pastebin.com"))
            self.ui.btnPastebin.setEnabled(True)

    def _pastebin_this(self):
        """
        Send the current log history to pastebin.com and gives the user a link
        to see it.
        """
        def do_pastebin():
            """
            Send content to pastebin and return the link.
            """
            content = self._current_history
            pb = pastebin.PastebinAPI()
            link = pb.paste(PASTEBIN_API_DEV_KEY, content,
                            paste_name="Bitmask log",
                            paste_expire_date='1M')

            # convert to 'raw' link
            link = "http://pastebin.com/raw.php?i=" + link.split('/')[-1]

            return link

        def pastebin_ok(link):
            """
            Callback handler for `do_pastebin`.

            :param link: the recently created pastebin link.
            :type link: str
            """
            self._set_pastebin_sending(False)
            msg = self.tr("Your pastebin link <a href='{0}'>{0}</a>")
            msg = msg.format(link)

            # We save the dialog in an instance member to avoid dialog being
            # deleted right after we exit this method
            self._msgBox = msgBox = QtGui.QMessageBox(
                QtGui.QMessageBox.Information, self.tr("Pastebin OK"), msg)
            msgBox.setWindowModality(QtCore.Qt.NonModal)
            msgBox.show()

        def pastebin_err(failure):
            """
            Errback handler for `do_pastebin`.

            :param failure: the failure that triggered the errback.
            :type failure: twisted.python.failure.Failure
            """
            self._set_pastebin_sending(False)
            logger.error(repr(failure))

            msg = self.tr("Sending logs to Pastebin failed!")
            if failure.check(pastebin.PostLimitError):
                msg = self.tr('Maximum posts per day reached')

            # We save the dialog in an instance member to avoid dialog being
            # deleted right after we exit this method
            self._msgBox = msgBox = QtGui.QMessageBox(
                QtGui.QMessageBox.Critical, self.tr("Pastebin Error"), msg)
            msgBox.setWindowModality(QtCore.Qt.NonModal)
            msgBox.show()

        self._set_pastebin_sending(True)
        d = threads.deferToThread(do_pastebin)
        d.addCallback(pastebin_ok)
        d.addErrback(pastebin_err)
