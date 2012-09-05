from PyQt4.QtGui import (QDialog, QFrame, QPushButton, QLabel, QMessageBox)


class ErrorDialog(QDialog):
    def __init__(self, parent=None):
        super(ErrorDialog, self).__init__(parent)
        frameStyle = QFrame.Sunken | QFrame.Panel
        self.warningLabel = QLabel()
        self.warningLabel.setFrameStyle(frameStyle)
        self.warningButton = QPushButton("QMessageBox.&warning()")

    def warningMessage(self, msg, label):
        msgBox = QMessageBox(QMessageBox.Warning,
                             "QMessageBox.warning()", msg,
                             QMessageBox.NoButton, self)
        msgBox.addButton("&Ok", QMessageBox.AcceptRole)
        if msgBox.exec_() == QMessageBox.AcceptRole:
            pass
            # do whatever we want to do after
            # closing the dialog. we can pass that
            # in the constructor

    def criticalMessage(self, msg, label):
        msgBox = QMessageBox(QMessageBox.Critical,
                             "QMessageBox.critical()", msg,
                             QMessageBox.NoButton, self)
        msgBox.addButton("&Ok", QMessageBox.AcceptRole)
        msgBox.exec_()
        import sys
        sys.exit()
