# -*- coding: utf-8 -*-
# logwindow.py
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
import cgi

from PySide import QtCore, QtGui

import logbook

from ui_loggerwindow import Ui_LoggerWindow

from leap.bitmask.logs.utils import get_logger, LOG_CONTROLLER
from leap.bitmask.util.constants import PASTEBIN_API_DEV_KEY
from leap.bitmask.util import pastebin

logger = get_logger()


class LoggerWindow(QtGui.QDialog):
    """
    Window that displays a history of the logged messages in the app.
    """
    _paste_ok = QtCore.Signal(object)
    _paste_error = QtCore.Signal(object)

    def __init__(self, parent):
        """
        Initialize the widget.
        """
        QtGui.QDialog.__init__(self, parent)

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

        self._paste_ok.connect(self._pastebin_ok)
        self._paste_error.connect(self._pastebin_err)

        self._current_filter = ""
        self._current_history = ""

        self._set_logs_to_display()

        LOG_CONTROLLER.new_log.connect(self._add_log_line)
        self._load_history()

    def _add_log_line(self, log):
        """
        Adds a line to the history, only if it's in the desired levels to show.

        :param log: a log record to be inserted in the widget
        :type log: Logbook.LogRecord.
        """
        html_style = {
            logbook.DEBUG: "background: #CDFFFF;",
            logbook.INFO: "background: white;",
            logbook.WARNING: "background: #FFFF66;",
            logbook.ERROR: "background: red; color: white;",
            logbook.CRITICAL: "background: red; color: white; font: bold;"
        }
        level = log.level
        message = cgi.escape(log.msg)

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
        current_history = []
        for record in LOG_CONTROLLER.get_logs():
            self._add_log_line(record)
            current_history.append(record.msg)

        self._current_history = "\n".join(current_history)

    def _set_logs_to_display(self):
        """
        Sets the logs_to_display dict getting the toggled options from the ui
        """
        self._logs_to_display = {
            logbook.DEBUG: self.ui.btnDebug.isChecked(),
            logbook.INFO: self.ui.btnInfo.isChecked(),
            logbook.WARNING: self.ui.btnWarning.isChecked(),
            logbook.ERROR: self.ui.btnError.isChecked(),
            logbook.CRITICAL: self.ui.btnCritical.isChecked()
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
            self.ui.btnPastebin.setText(self.tr("Sending to Pastebin.com…"))
            self.ui.btnPastebin.setEnabled(False)
        else:
            self.ui.btnPastebin.setText(self.tr("Send to Pastebin.com"))
            self.ui.btnPastebin.setEnabled(True)

    def _pastebin_ok(self, link):
        """
        Handle a successful paste.

        :param link: the recently created pastebin link.
        :type link: str
        """
        self._set_pastebin_sending(False)
        msg = self.tr("Your pastebin link <a href='{0}'>{0}</a>")
        msg = msg.format(link)

        # We save the dialog in an instance member to avoid dialog being
        # deleted right after we exit this method
        self._msgBox = msgBox = QtGui.QMessageBox(
            QtGui.QMessageBox.Information, self.tr("Pastebin is OK"), msg)
        msgBox.setWindowModality(QtCore.Qt.NonModal)
        msgBox.show()

    def _pastebin_err(self, failure):
        """
        Handle a failure in paste.

        :param failure: the exception that made the paste fail.
        :type failure: Exception
        """
        self._set_pastebin_sending(False)
        logger.error(repr(failure))

        msg = self.tr("Sending logs to Pastebin failed!")
        if isinstance(failure, pastebin.PostLimitError):
            msg = self.tr('Maximum amount of submissions reached for today.')

        # We save the dialog in an instance member to avoid dialog being
        # deleted right after we exit this method
        self._msgBox = msgBox = QtGui.QMessageBox(
            QtGui.QMessageBox.Critical, self.tr("Pastebin Error"), msg)
        msgBox.setWindowModality(QtCore.Qt.NonModal)
        msgBox.show()

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
            try:
                link = pb.paste(PASTEBIN_API_DEV_KEY, content,
                                paste_name="Bitmask log",
                                paste_expire_date='1M')
                # convert to 'raw' link
                link = "http://pastebin.com/raw.php?i=" + link.split('/')[-1]

                self._paste_ok.emit(link)
            except Exception as e:
                self._paste_error.emit(e)

        self._set_pastebin_sending(True)

        self._paste_thread = QtCore.QThread()
        self._paste_thread.run = lambda: do_pastebin()
        self._paste_thread.start()
