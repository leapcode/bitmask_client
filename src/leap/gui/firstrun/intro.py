"""
Intro page used in first run wizard
"""

from PyQt4 import QtGui

from leap.gui.constants import APP_LOGO, APP_WATERMARK


class IntroPage(QtGui.QWizardPage):
    def __init__(self, parent=None):
        super(IntroPage, self).__init__(parent)

        self.setTitle(self.tr("First run wizard"))

        self.setPixmap(
            QtGui.QWizard.WatermarkPixmap,
            QtGui.QPixmap(APP_WATERMARK))

        self.setPixmap(
            QtGui.QWizard.LogoPixmap,
            QtGui.QPixmap(APP_LOGO))

        label = QtGui.QLabel(self.tr(
            "Now we will guide you through "
            "some configuration that is needed before you "
            "can connect for the first time.<br><br>"
            "If you ever need to modify these options again, "
            "you can find the wizard in the '<i>Settings</i>' menu from the "
            "main window.<br><br>"
            "Do you want to <b>sign up</b> for a new account, or <b>log "
            "in</b> with an already existing username?<br>"))
        label.setWordWrap(True)

        radiobuttonGroup = QtGui.QGroupBox()

        self.sign_up = QtGui.QRadioButton(
            self.tr("Sign up for a new account"))
        self.sign_up.setChecked(True)
        self.log_in = QtGui.QRadioButton(
            self.tr("Log In with my credentials"))

        radiobLayout = QtGui.QVBoxLayout()
        radiobLayout.addWidget(self.sign_up)
        radiobLayout.addWidget(self.log_in)
        radiobuttonGroup.setLayout(radiobLayout)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(radiobuttonGroup)
        self.setLayout(layout)

        #self.registerField('is_signup', self.sign_up)

    def validatePage(self):
        return True

    def nextId(self):
        """
        returns next id
        in a non-linear wizard
        """
        if self.sign_up.isChecked():
            next_ = 'providerselection'
        if self.log_in.isChecked():
            next_ = 'login'
        wizard = self.wizard()
        return wizard.get_page_index(next_)
