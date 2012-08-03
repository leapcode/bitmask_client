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
        msgBox.addButton("&Cancel", QMessageBox.RejectRole)
        if msgBox.exec_() == QMessageBox.AcceptRole:
            self.warningLabel.setText("Save Again")
        else:
            self.warningLabel.setText("Continue")
