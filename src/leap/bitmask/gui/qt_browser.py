from PySide import QtCore, QtWebKit, QtGui

PIXELATED_URI = 'http://localhost:9090'


class PixelatedWindow(QtGui.QDialog):

    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        self.web = QtWebKit.QWebView(self)
        self.web.load(QtCore.QUrl(PIXELATED_URI))
        self.setWindowTitle('Bitmask/Pixelated WebMail')
        self.web.show()
